from time import monotonic

from app.generation.events import SLOT_SNAPSHOT, GenerationEvent
from app.generation.layouts import ContentConstraints
from app.generation.stream_runtime import (
    SlotSnapshotCoalescer,
    remaining_slide_ids,
    stream_slots_for_constraints,
    subset_deck_plan,
    subset_story_outline,
)


def _snapshot(sequence: int, text: str, *, slot: str = "body") -> GenerationEvent:
    return GenerationEvent(
        version=1,
        type=SLOT_SNAPSHOT,
        job_id="job-1",
        attempt=1,
        sequence=sequence,
        slide_id="slide-1",
        slot=slot,
        data={"value": text},
    )


def test_stream_slots_start_with_title_then_body_then_item_fields() -> None:
    assert stream_slots_for_constraints(ContentConstraints(72, 180, 55, 120, 0)) == (
        "title",
        "body",
    )
    assert stream_slots_for_constraints(ContentConstraints(72, 180, 55, 120, 2)) == (
        "title",
        "body",
        "items.0.heading",
        "items.0.body",
        "items.1.heading",
        "items.1.body",
    )


def test_coalescer_holds_snapshots_until_delay_elapses() -> None:
    clock = {"now": 0.0}
    coalescer = SlotSnapshotCoalescer(delay_seconds=0.1, monotonic=lambda: clock["now"])

    assert coalescer.ingest(_snapshot(1, "A")) == []
    clock["now"] = 0.05
    assert coalescer.ingest(_snapshot(2, "AB")) == []
    clock["now"] = 0.1
    flushed = coalescer.ingest(_snapshot(3, "ABC"))

    assert [event.data["value"] for event in flushed] == ["ABC"]


def test_coalescer_flushes_pending_snapshots_before_non_snapshot_events() -> None:
    coalescer = SlotSnapshotCoalescer(delay_seconds=1, monotonic=monotonic)
    completed = GenerationEvent(
        version=1,
        type="slide.completed",
        job_id="job-1",
        attempt=1,
        sequence=3,
        slide_id="slide-1",
        slot=None,
        data={"content": "done"},
    )

    coalescer.ingest(_snapshot(1, "A"))
    coalescer.ingest(_snapshot(2, "AB", slot="title"))
    flushed = coalescer.ingest(completed)

    assert [event.type for event in flushed] == [SLOT_SNAPSHOT, SLOT_SNAPSHOT, "slide.completed"]
    assert {event.slot: event.data["value"] for event in flushed[:2]} == {
        "body": "A",
        "title": "AB",
    }


def test_remainder_helpers_keep_unfinished_slides_in_order() -> None:
    from app.generation.models import DeckPlan, SlidePlan
    from app.generation.stages.models import StoryOutline, StoryOutlineItem

    outline = StoryOutline(
        items=[
            StoryOutlineItem(id="cover", title="Cover", content=""),
            StoryOutlineItem(id="point-1", title="Point", content=""),
        ]
    )
    deck = DeckPlan(
        title="Deck",
        audience="A",
        objective="O",
        narrative_arc="Arc",
        language="en",
        slides=[
            SlidePlan(id="cover", index=0, role="cover", communication_goal="G", content_structure="headline"),
            SlidePlan(id="point-1", index=1, role="content", communication_goal="G", content_structure="list"),
        ],
    )

    remaining = remaining_slide_ids(["cover", "point-1"], ["cover"])
    filtered_outline = subset_story_outline(outline, remaining)
    filtered_deck = subset_deck_plan(deck, remaining)

    assert remaining == ["point-1"]
    assert [item.id for item in filtered_outline.items] == ["point-1"]
    assert [slide.id for slide in filtered_deck.slides] == ["point-1"]
