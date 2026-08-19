from uuid import uuid4

from app.generation.event_transport import PublishResult
from app.generation.events import SLOT_SNAPSHOT, SLIDE_COMPLETED, GenerationEvent
from app.generation.layouts import ContentConstraints
from app.generation.models import DeckPlan, SlideContent, SlidePlan
from app.generation.provider import GenerationRequest, ProviderResponseError
from app.generation.stages.models import StoryOutline, StoryOutlineItem
from app.generation.stream_runtime import IncrementalSlideStreamer
from app.generation.worker import ClaimedGeneration, GenerationWorker


class FakePublisher:
    def __init__(self, *, fail: bool = False) -> None:
        self.events: list[GenerationEvent] = []
        self.fail = fail

    def publish(self, event: GenerationEvent) -> PublishResult:
        self.events.append(event)
        if self.fail:
            return PublishResult(published=False, error="redis down")
        return PublishResult(published=True, subscriber_count=1)


class FakeCheckpoints:
    def __init__(self) -> None:
        self.records: list[tuple[GenerationEvent, dict[str, object] | None]] = []

    def record_event(
        self,
        event: GenerationEvent,
        *,
        validated_canonical_slide: dict[str, object] | None = None,
    ):
        self.records.append((event, validated_canonical_slide))
        return object()


class FakeGenerator:
    name = "fake-renderer"

    def __init__(self) -> None:
        self.indexes: list[int] = []

    def render_slide(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        index: int,
        assets: dict[tuple[int, str], str],
        contents: dict[str, SlideContent] | None = None,
    ) -> dict[str, object]:
        del request, assets
        self.indexes.append(index)
        item = outline.items[index]
        written = (contents or {}).get(item.id)
        return {
            "id": item.id,
            "title": written.title if written else item.title,
            "elements": [
                {
                    "id": "title",
                    "type": "text",
                    "position": {"x": 10, "y": 10},
                    "size": {"width": 200, "height": 40},
                    "font": {"size": 18},
                }
            ],
        }


def _content(slide_id: str, title: str) -> SlideContent:
    return SlideContent(
        slide_id=slide_id,
        title=title,
        layout_id="title-body",
        slots={"body": "Body"},
    )


def _event(sequence: int, event_type: str, slide_id: str, **changes: object) -> GenerationEvent:
    values: dict[str, object] = {
        "version": 1,
        "type": event_type,
        "job_id": "11111111-1111-1111-1111-111111111111",
        "attempt": 1,
        "sequence": sequence,
        "slide_id": slide_id,
        "slot": None,
        "data": {},
    }
    values.update(changes)
    return GenerationEvent(**values)  # type: ignore[arg-type]


def test_incremental_streamer_publishes_coalesced_snapshots_and_compiled_slides() -> None:
    publisher = FakePublisher()
    checkpoints = FakeCheckpoints()
    generator = FakeGenerator()
    outline = StoryOutline(
        items=[
            StoryOutlineItem(id="cover", title="Cover", content="", layout_id="title_slide"),
            StoryOutlineItem(id="point-1", title="Point", content="Body", layout_id="title-body"),
        ]
    )
    request = GenerationRequest(
        presentation_id=uuid4(),
        title="Deck",
        text="Source",
        sections=[],
        language="en",
        slide_count=2,
        theme_id="modern-blue",
    )
    events = [
        _event(1, SLOT_SNAPSHOT, "cover", slot="title", data={"value": "C"}),
        _event(2, SLOT_SNAPSHOT, "cover", slot="title", data={"value": "Cover"}),
        _event(
            3,
            SLIDE_COMPLETED,
            "cover",
            data={"content": _content("cover", "Cover")},
        ),
        _event(
            4,
            SLIDE_COMPLETED,
            "point-1",
            data={"content": _content("point-1", "Point")},
        ),
    ]
    streamer = IncrementalSlideStreamer(
        publisher=publisher,
        checkpoints=checkpoints,
        compile_slide=lambda index, contents: generator.render_slide(
            request,
            outline,
            index=index,
            assets={},
            contents=contents,
        ),
        validate_slide=lambda slide: slide,
        delay_seconds=1,
        monotonic=lambda: 0.0,
    )

    compiled = streamer.consume(events, slide_ids=["cover", "point-1"])

    assert [slide["id"] for slide in compiled] == ["cover", "point-1"]
    assert generator.indexes == [0, 1]
    assert [event.type for event in publisher.events] == [
        SLOT_SNAPSHOT,
        SLIDE_COMPLETED,
        SLIDE_COMPLETED,
    ]
    assert publisher.events[0].data["value"] == "Cover"
    assert checkpoints.records[0][1]["id"] == "cover"
    assert checkpoints.records[1][1]["id"] == "point-1"


def test_incremental_streamer_continues_when_publish_fails() -> None:
    publisher = FakePublisher(fail=True)
    checkpoints = FakeCheckpoints()
    streamer = IncrementalSlideStreamer(
        publisher=publisher,
        checkpoints=checkpoints,
        compile_slide=lambda index, contents: {
            "id": list(contents)[index],
            "elements": [],
        },
        validate_slide=lambda slide: slide,
        delay_seconds=0,
        monotonic=lambda: 1.0,
    )

    compiled = streamer.consume(
        [
            _event(
                1,
                SLIDE_COMPLETED,
                "cover",
                data={"content": _content("cover", "Cover")},
            )
        ],
        slide_ids=["cover"],
    )

    assert compiled[0]["id"] == "cover"


def test_incremental_streamer_stamps_event_slide_id_onto_compiled_slides() -> None:
    publisher = FakePublisher()
    checkpoints = FakeCheckpoints()
    streamer = IncrementalSlideStreamer(
        publisher=publisher,
        checkpoints=checkpoints,
        compile_slide=lambda index, contents: {
            "id": str(uuid4()),
            "title": "Cover",
            "elements": [{"id": "title"}],
        },
        validate_slide=lambda slide: slide,
        delay_seconds=0,
        monotonic=lambda: 1.0,
    )

    compiled = streamer.consume(
        [
            _event(
                1,
                SLIDE_COMPLETED,
                "cover",
                data={"content": _content("cover", "Cover")},
            )
        ],
        slide_ids=["cover"],
    )

    assert compiled[0]["id"] == "cover"
    assert checkpoints.records[0][1]["id"] == "cover"
    assert checkpoints.records


def test_worker_builds_stream_layout_slots_from_selected_layouts() -> None:
    outline = StoryOutline(
        items=[
            StoryOutlineItem(id="cover", title="Cover", content="", layout_id="title_slide"),
            StoryOutlineItem(id="point-1", title="Point", content="Body", layout_id="cards"),
        ]
    )
    constraints = {
        "cover": ContentConstraints(72, 80, 40, 80, 0),
        "point-1": ContentConstraints(72, 180, 55, 120, 1),
    }

    selected, slots = GenerationWorker.stream_layout_maps(outline, constraints)

    assert selected == {"cover": "title_slide", "point-1": "cards"}
    assert slots["title_slide"] == ("title", "body")
    assert slots["cards"][-1] == "items.0.body"


def test_worker_streaming_requires_deck_plan_and_selected_layouts() -> None:
    deck = DeckPlan(
        title="Deck",
        audience="A",
        objective="O",
        narrative_arc="Arc",
        language="en",
        slides=[
            SlidePlan(
                id="cover",
                index=0,
                role="cover",
                communication_goal="Introduce",
                content_structure="headline",
            )
        ],
    )
    outline = StoryOutline(
        items=[StoryOutlineItem(id="cover", title="Cover", content="", layout_id="title_slide")]
    )

    selected, _slots = GenerationWorker.stream_layout_maps(
        outline,
        {"cover": ContentConstraints(72, 80, 40, 80, 0)},
    )

    assert selected["cover"] == "title_slide"
    assert deck.slides[0].id in selected


def test_incremental_streamer_keeps_compiled_slides_when_the_stream_fails() -> None:
    publisher = FakePublisher()
    checkpoints = FakeCheckpoints()
    streamer = IncrementalSlideStreamer(
        publisher=publisher,
        checkpoints=checkpoints,
        compile_slide=lambda index, contents: {
            "id": list(contents)[index],
            "elements": [],
        },
        validate_slide=lambda slide: slide,
        delay_seconds=0,
        monotonic=lambda: 1.0,
    )

    def events():
        yield _event(
            1,
            SLIDE_COMPLETED,
            "cover",
            data={"content": _content("cover", "Cover")},
        )
        raise ProviderResponseError("dropped")

    try:
        streamer.consume(events(), slide_ids=["cover", "point-1"])
    except ProviderResponseError:
        pass
    else:
        raise AssertionError("expected the stream to fail")

    assert streamer.compiled[0]["id"] == "cover"


class _FakeLayoutSelector:
    def content_constraints(self, layout_id: str) -> ContentConstraints:
        del layout_id
        return ContentConstraints(72, 80, 40, 80, 0)


class _FailAfterFirstSlideProvider:
    name = "fake-stream"

    def __init__(self) -> None:
        self.calls: list[tuple[int, list[str]]] = []

    def stream_deck_content(self, **kwargs):
        attempt = kwargs["attempt"]
        outline = kwargs["outline"]
        self.calls.append((attempt, [item.id for item in outline.items]))
        if attempt == 1:
            yield _event(
                1,
                SLIDE_COMPLETED,
                "cover",
                data={"content": _content("cover", "Cover")},
            )
            raise ProviderResponseError("dropped")
        yield _event(
            1,
            SLIDE_COMPLETED,
            "point-1",
            data={"content": _content("point-1", "Point")},
        )


class _StreamingPipeline:
    name = "fake"

    def __init__(self, provider: _FailAfterFirstSlideProvider) -> None:
        self.story_planner = provider
        self.layout_selector = _FakeLayoutSelector()
        self.content_generator = FakeGenerator()

    def validate_slide(self, slide: dict[str, object]) -> dict[str, object]:
        return slide


def test_worker_retries_incomplete_remainder_under_a_new_attempt() -> None:
    provider = _FailAfterFirstSlideProvider()
    worker = GenerationWorker(
        session_factory=object(),  # type: ignore[arg-type]
        pipeline=_StreamingPipeline(provider),  # type: ignore[arg-type]
        event_publisher=FakePublisher(),
        checkpoint_service=FakeCheckpoints(),
        streaming_enabled=True,
        snapshot_coalesce_seconds=0,
    )
    outline = StoryOutline(
        items=[
            StoryOutlineItem(id="cover", title="Cover", content="", layout_id="title_slide"),
            StoryOutlineItem(id="point-1", title="Point", content="Body", layout_id="title-body"),
        ]
    )
    deck = DeckPlan(
        title="Deck",
        audience="A",
        objective="O",
        narrative_arc="Arc",
        language="en",
        slides=[
            SlidePlan(id="cover", index=0, role="cover", communication_goal="Introduce", content_structure="headline"),
            SlidePlan(id="point-1", index=1, role="content", communication_goal="Explain", content_structure="list"),
        ],
    )
    claimed = ClaimedGeneration(
        job_id=uuid4(),
        owner_id=uuid4(),
        source_id=None,
        outline_id=None,
        title="Deck",
        text="Source",
        sections=[],
        outline=[],
        slide_count=2,
        language="en",
        source_kind="prompt",
        theme_id="modern-blue",
    )
    request = GenerationRequest(
        presentation_id=uuid4(),
        title="Deck",
        text="Source",
        sections=[],
        language="en",
        slide_count=2,
        theme_id="modern-blue",
    )

    contents, compiled = worker._write_or_stream_content(
        claimed,
        request,
        outline,
        deck,
        assets={},
    )

    assert [slide["id"] for slide in compiled or []] == ["cover", "point-1"]
    assert set(contents) == {"cover", "point-1"}
    assert provider.calls == [(1, ["cover", "point-1"]), (2, ["point-1"])]
