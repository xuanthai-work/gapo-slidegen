from uuid import uuid4

from app.generation.event_transport import PublishResult
from app.generation.events import SLIDE_COMPLETED, GenerationEvent
from app.generation.layouts import ContentConstraints
from app.generation.models import DeckPlan, SlideContent, SlidePlan
from app.generation.provider import GenerationRequest
from app.generation.stages.models import StoryOutline, StoryOutlineItem
from app.generation.worker import ClaimedGeneration, GenerationWorker


class FakePublisher:
    def publish(self, event: GenerationEvent) -> PublishResult:
        return PublishResult(published=True, subscriber_count=1)


class FakeCheckpoints:
    def record_event(
        self,
        event: GenerationEvent,
        *,
        validated_canonical_slide: dict[str, object] | None = None,
    ):
        del event, validated_canonical_slide
        return object()


class FakeTracker:
    def slide(self, progress: int, slide_index: int, slide: dict[str, object]) -> None:
        del progress, slide_index, slide


class FakeGenerator:
    name = "fake-renderer"

    def render_slide(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        index: int,
        assets: dict[tuple[int, str], str],
        contents: dict[str, SlideContent] | None = None,
    ) -> dict[str, object]:
        del request, assets, contents
        item = outline.items[index]
        return {"id": item.id, "title": item.title, "elements": []}

    def render_slides(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: dict[tuple[int, str], str],
        contents: dict[str, SlideContent] | None = None,
    ) -> list[dict[str, object]]:
        return [
            self.render_slide(request, outline, index=index, assets=assets, contents=contents)
            for index in range(len(outline.items))
        ]


class _FakeLayoutSelector:
    def content_constraints(self, layout_id: str) -> ContentConstraints:
        del layout_id
        return ContentConstraints(72, 80, 40, 80, 0)


class _BatchPipeline:
    name = "fake"

    def __init__(self) -> None:
        self.content_generator = FakeGenerator()

    def validate_slide(self, slide: dict[str, object]) -> dict[str, object]:
        return slide

    def accept_slide(self, slide: dict[str, object], **kwargs) -> dict[str, object]:
        del kwargs
        return slide


class _StreamProvider:
    name = "fake-stream"

    def stream_deck_content(self, **kwargs):
        del kwargs
        yield GenerationEvent(
            version=1,
            type=SLIDE_COMPLETED,
            job_id="11111111-1111-1111-1111-111111111111",
            attempt=1,
            sequence=1,
            slide_id="cover",
            slot=None,
            data={
                "content": SlideContent(
                    slide_id="cover",
                    title="Cover",
                    layout_id="title-body",
                    slots={"body": "Body"},
                )
            },
        )


class _StreamingPipeline:
    name = "fake"

    def __init__(self) -> None:
        self.story_planner = _StreamProvider()
        self.layout_selector = _FakeLayoutSelector()
        self.content_generator = FakeGenerator()

    def validate_slide(self, slide: dict[str, object]) -> dict[str, object]:
        return slide

    def accept_slide(self, slide: dict[str, object], **kwargs) -> dict[str, object]:
        del kwargs
        return slide


def _outline() -> StoryOutline:
    return StoryOutline(
        items=[
            StoryOutlineItem(id="cover", title="Cover", content="", layout_id="title_slide"),
        ]
    )


def _deck() -> DeckPlan:
    return DeckPlan(
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


def _request() -> GenerationRequest:
    return GenerationRequest(
        presentation_id=uuid4(),
        title="Deck",
        text="Source",
        sections=[],
        language="en",
        slide_count=1,
        theme_id="modern-blue",
    )


def _claimed() -> ClaimedGeneration:
    return ClaimedGeneration(
        job_id=uuid4(),
        owner_id=uuid4(),
        source_id=None,
        outline_id=None,
        title="Deck",
        text="Source",
        sections=[],
        outline=[],
        slide_count=1,
        language="en",
        source_kind="prompt",
        theme_id="modern-blue",
        template_id="modern",
        color_scheme_id="professional-blue",
    )


def test_render_slide_by_slide_calls_accept_slide() -> None:
    pipeline = _BatchPipeline()
    worker = GenerationWorker(
        session_factory=object(),  # type: ignore[arg-type]
        pipeline=pipeline,  # type: ignore[arg-type]
        event_publisher=FakePublisher(),
        checkpoint_service=FakeCheckpoints(),
    )
    calls: list[dict[str, object]] = []

    def accept_slide(slide: dict[str, object], **kwargs) -> dict[str, object]:
        calls.append(slide)
        return slide

    worker.pipeline.accept_slide = accept_slide  # type: ignore[method-assign]
    contents = {
        "cover": SlideContent(
            slide_id="cover",
            title="Cover",
            layout_id="title_slide",
            slots={},
        )
    }

    worker._render_slide_by_slide(
        _request(),
        _outline(),
        assets={},
        contents=contents,
        tracker=FakeTracker(),  # type: ignore[arg-type]
        deck_plan=_deck(),
    )

    assert len(calls) == 1
    assert calls[0]["id"] == "cover"


def test_stream_compile_slide_calls_accept_slide() -> None:
    pipeline = _StreamingPipeline()
    worker = GenerationWorker(
        session_factory=object(),  # type: ignore[arg-type]
        pipeline=pipeline,  # type: ignore[arg-type]
        event_publisher=FakePublisher(),
        checkpoint_service=FakeCheckpoints(),
        streaming_enabled=True,
        snapshot_coalesce_seconds=0,
    )
    calls: list[dict[str, object]] = []

    def accept_slide(slide: dict[str, object], **kwargs) -> dict[str, object]:
        calls.append(slide)
        return slide

    worker.pipeline.accept_slide = accept_slide  # type: ignore[method-assign]

    contents, compiled = worker._write_or_stream_content(
        _claimed(),
        _request(),
        _outline(),
        _deck(),
        assets={},
    )

    assert [slide["id"] for slide in compiled or []] == ["cover"]
    assert "cover" in contents
    assert len(calls) == 1
    assert calls[0]["id"] == "cover"
