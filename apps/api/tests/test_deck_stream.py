from dataclasses import replace

import pytest

from app.generation.deck_stream import (
    DeckStreamError,
    StreamLimits,
    TaggedDeckStreamParser,
)
from app.generation.events import (
    SLOT_SNAPSHOT,
    GenerationEvent,
    coalesce_slot_snapshots,
)
from app.generation.models import DeckPlan, SlideContent, SlidePlan


def _deck(*slide_ids: str) -> DeckPlan:
    return DeckPlan(
        title="Deck",
        audience="Engineers",
        objective="Explain the system",
        narrative_arc="Context to action",
        language="en",
        slides=[
            SlidePlan(
                id=slide_id,
                index=index,
                role="content",
                communication_goal=f"Explain {slide_id}",
                content_structure="body",
                preferred_archetype="content-basic",
            )
            for index, slide_id in enumerate(slide_ids, start=1)
        ],
    )


def _parser(
    *slide_ids: str,
    attempt: int = 1,
    limits: StreamLimits | None = None,
) -> TaggedDeckStreamParser:
    return TaggedDeckStreamParser(
        _deck(*slide_ids),
        job_id="job-123",
        selected_layouts={slide_id: "content-basic" for slide_id in slide_ids},
        layout_slots={"content-basic": ("title", "body")},
        attempt=attempt,
        limits=limits,
    )


def _payload(slide_id: str, title: str, body: str) -> str:
    return (
        f"[[SLIDE {slide_id}]]"
        f"[[SLOT title]]{title}[[/SLOT]]"
        f"[[SLOT body]]{body}[[/SLOT]]"
        "[[/SLIDE]]"
    )


def test_parser_handles_markers_fragmented_across_http_chunks() -> None:
    parser = _parser("slide-1")
    payload = _payload("slide-1", "A title", "A body")

    events = []
    for character in payload:
        events.extend(parser.feed(character))
    parser.finish()

    completed = events[-1]
    assert completed.type == "slide.completed"
    assert completed.data["content"] == SlideContent(
        slide_id="slide-1",
        title="A title",
        layout_id="content-basic",
        slots={"body": "A body"},
    )
    body_snapshots = [
        event.data["value"]
        for event in events
        if event.type == SLOT_SNAPSHOT and event.slot == "body"
    ]
    assert body_snapshots[-1] == "A body"


def test_parser_streams_multiple_slides_in_plan_order() -> None:
    parser = _parser("slide-1", "slide-2", attempt=3)

    events = parser.feed(
        _payload("slide-1", "First", "One")
        + _payload("slide-2", "Second", "Two")
    )
    parser.finish()

    completed = [event for event in events if event.type == "slide.completed"]
    assert [event.slide_id for event in completed] == ["slide-1", "slide-2"]
    assert [event.data["content"].title for event in completed] == ["First", "Second"]
    assert all(
        event.version == 1
        and event.job_id == "job-123"
        and event.attempt == 3
        for event in events
    )
    assert [event.sequence for event in events] == list(range(1, len(events) + 1))


def test_parser_events_include_generation_job_identity() -> None:
    parser = _parser("slide-1")

    events = parser.feed(_payload("slide-1", "Title", "Body"))
    parser.finish()

    assert events
    assert {event.job_id for event in events} == {"job-123"}


def test_parser_uses_concrete_selected_layout_instead_of_planned_archetype() -> None:
    deck = _deck("slide-1")
    parser = TaggedDeckStreamParser(
        deck,
        job_id="job-layout",
        selected_layouts={"slide-1": "selected-layout"},
        layout_slots={"selected-layout": ("title", "body")},
    )

    events = parser.feed(_payload("slide-1", "Title", "Body"))
    parser.finish()

    completed = events[-1]
    assert completed.data["content"].layout_id == "selected-layout"


def test_parser_assembles_dotted_item_slots_as_structured_content() -> None:
    parser = TaggedDeckStreamParser(
        _deck("slide-1"),
        job_id="job-items",
        selected_layouts={"slide-1": "cards"},
        layout_slots={
            "cards": (
                "title",
                "body",
                "items.0.heading",
                "items.0.body",
                "items.1.heading",
                "items.1.body",
            )
        },
    )
    payload = (
        "[[SLIDE slide-1]]"
        "[[SLOT title]]Benefits[[/SLOT]]"
        "[[SLOT body]]Why it matters[[/SLOT]]"
        "[[SLOT items.0.heading]]Fast[[/SLOT]]"
        "[[SLOT items.0.body]]Minutes, not days[[/SLOT]]"
        "[[SLOT items.1.heading]]Safe[[/SLOT]]"
        "[[SLOT items.1.body]]Validated output[[/SLOT]]"
        "[[/SLIDE]]"
    )

    events = parser.feed(payload)
    parser.finish()

    completed = events[-1].data["content"]
    assert completed.slots == {
        "body": "Why it matters",
        "items": [
            {"heading": "Fast", "body": "Minutes, not days"},
            {"heading": "Safe", "body": "Validated output"},
        ],
    }
    item_snapshots = [
        event
        for event in events
        if event.type == SLOT_SNAPSHOT and event.slot == "items.1.body"
    ]
    assert item_snapshots[-1].data == {"value": "Validated output"}


def test_parser_rejects_malformed_dotted_item_slot_constraints() -> None:
    with pytest.raises(ValueError, match="Malformed item slot"):
        TaggedDeckStreamParser(
            _deck("slide-1"),
            job_id="job-items",
            selected_layouts={"slide-1": "cards"},
            layout_slots={"cards": ("title", "items.one.heading")},
        )


def test_parser_rejects_malformed_dotted_item_slot_marker() -> None:
    parser = _parser("slide-1")

    with pytest.raises(DeckStreamError, match="Malformed item slot"):
        parser.feed("[[SLIDE slide-1]][[SLOT items.one.heading]]")


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (_payload("slide-2", "Wrong", "Order"), "Expected slide 'slide-1'"),
        (_payload("missing", "Unknown", "Slide"), "Unknown slide 'missing'"),
        (
            "[[SLIDE slide-1]][[SLOT mystery]]",
            "Unknown slot 'mystery'",
        ),
        (
            "[[SLIDE slide-1]][[SLOT body]]",
            "Expected slot 'title'",
        ),
    ],
)
def test_parser_rejects_unknown_or_out_of_order_identifiers(
    payload: str,
    message: str,
) -> None:
    parser = _parser("slide-1", "slide-2")

    with pytest.raises(DeckStreamError, match=message):
        parser.feed(payload)


def test_parser_enforces_stream_and_slot_output_limits() -> None:
    stream_limited = _parser(
        "slide-1",
        limits=StreamLimits(max_stream_chars=20, max_slot_chars=100),
    )
    with pytest.raises(DeckStreamError, match="Stream output limit"):
        stream_limited.feed(_payload("slide-1", "Title", "Body"))

    slot_limited = _parser(
        "slide-1",
        limits=StreamLimits(max_stream_chars=1_000, max_slot_chars=4),
    )
    with pytest.raises(DeckStreamError, match="Slot output limit"):
        slot_limited.feed("[[SLIDE slide-1]][[SLOT title]]12345")


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ("[[SLIDE slide-1]][[SLOT title]]unfinished", "incomplete"),
        ("[[SLIDE slide-1]][[BOGUS]]", "Unknown marker"),
        (
            "[[SLIDE slide-1]][[SLOT title]]Title[[/SLOT]][[/SLIDE]]",
            "missing slot 'body'",
        ),
    ],
)
def test_parser_rejects_incomplete_or_malformed_completion(
    payload: str,
    message: str,
) -> None:
    parser = _parser("slide-1")

    if "BOGUS" in payload or "/SLIDE" in payload:
        with pytest.raises(DeckStreamError, match=message):
            parser.feed(payload)
    else:
        parser.feed(payload)
        with pytest.raises(DeckStreamError, match=message):
            parser.finish()


def test_event_sequences_increment_across_multiple_feed_calls() -> None:
    parser = _parser("slide-1")

    first = parser.feed("[[SLIDE slide-1]][[SLOT title]]Hello")
    second = parser.feed(" world[[/SLOT]][[SLOT body]]Body[[/SLOT]][[/SLIDE]]")
    parser.finish()

    events = first + second
    assert [event.sequence for event in events] == list(range(1, len(events) + 1))
    assert events[0].data["value"] == "Hello"
    assert events[1].data["value"] == "Hello world"


def test_coalescing_keeps_latest_snapshot_per_slide_slot_attempt() -> None:
    snapshot = GenerationEvent(
        version=1,
        type=SLOT_SNAPSHOT,
        job_id="job-1",
        attempt=1,
        sequence=5,
        slide_id="slide-1",
        slot="body",
        data={"value": "highest"},
    )
    lifecycle = GenerationEvent(
        version=1,
        type="slide.completed",
        job_id="job-1",
        attempt=1,
        sequence=6,
        slide_id="slide-1",
        slot=None,
        data={"content": "complete"},
    )
    events = [
        snapshot,
        lifecycle,
        replace(snapshot, sequence=3, data={"value": "later position"}),
        replace(snapshot, job_id="job-2", sequence=2, data={"value": "other job"}),
        replace(snapshot, attempt=2, sequence=4, data={"value": "retry"}),
    ]

    assert coalesce_slot_snapshots(events) == [
        snapshot,
        lifecycle,
        replace(snapshot, job_id="job-2", sequence=2, data={"value": "other job"}),
        replace(snapshot, attempt=2, sequence=4, data={"value": "retry"}),
    ]
