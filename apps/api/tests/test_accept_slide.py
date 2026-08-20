from uuid import uuid4

import pytest

from app.generation.layouts import ContentConstraints
from app.generation.models import SlideContent
from app.generation.provider import GenerationRequest, OutlineRequest
from app.generation.stages import GenerationPipeline, StoryOutline, StoryOutlineItem
from app.generation.stages.content_writer import OutlineContentWriter
from app.generation.stages.deck_planner import OutlineDeckPlanner
from app.generation.stages.layout_selector import LayoutCandidateScore
from app.generation.stages.orchestrator import SlideValidationFailed
from app.generation.stages.repair_dispatcher import VISUAL_GATE_MAX_REPAIRS
from app.generation.stages.slide_planner import OutlineSlidePlanner
from app.generation.stages.visual_gate import VisualGateResult, VisualIssue

LONG_BODY = (
    "Sentence one is long enough to wrap across the layout bound. "
    "Sentence two continues the argument with more detail. "
    "Sentence three adds supporting context so truncation has room to cut. "
    "Sentence four keeps going until the copy exceeds the scaled content limit."
)


class FakeStoryPlanner:
    name = "fake-story"

    def generate_outline(
        self,
        request: OutlineRequest,
        understanding: dict[str, object] | None = None,
    ) -> list[dict[str, object]]:
        del understanding
        return [
            {"id": "cover", "title": request.title, "content": ""},
            {"id": "point-1", "title": "Point one", "content": "First takeaway."},
        ]


class FakeRasterizer:
    name = "fake-rasterizer"

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def rasterize(self, slide: dict[str, object]) -> bytes:
        self.calls.append(slide)
        return b"\x89PNG\r\n\x1a\n" + b"x"


class ExplodingRasterizer:
    name = "exploding-rasterizer"

    def rasterize(self, slide: dict[str, object]) -> bytes:
        del slide
        raise OSError("chromium missing")


class RecordingGenerator:
    name = "recording"

    def __init__(self) -> None:
        self.layout_ids: list[str | None] = []

    def render(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: dict[tuple[int, str], str],
        contents: dict[str, SlideContent] | None = None,
    ) -> dict[str, object]:
        del assets, contents
        return {
            "id": str(request.presentation_id),
            "schemaVersion": 1,
            "title": request.title,
            "language": request.language,
            "theme": {"id": request.theme_id},
            "slides": [
                {"id": item.id, "title": item.title, "layout_id": item.layout_id, "elements": []}
                for item in outline.items
            ],
            "revision": 0,
        }

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
        item = outline.items[index]
        self.layout_ids.append(item.layout_id)
        content = (contents or {}).get(item.id)
        body = ""
        if content is not None:
            raw_body = content.slots.get("body")
            if isinstance(raw_body, str):
                body = raw_body
        return {
            "id": item.id,
            "title": content.title if content is not None else item.title,
            "layout_id": item.layout_id,
            "body": body,
            "elements": [],
        }

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


class RankingSelector:
    name = "ranking"

    def __init__(self, layout_ids: list[str]) -> None:
        self.layout_ids = layout_ids
        self.select_plans: list = []
        self.rank_plans: list = []

    def select(self, item, *, index, theme_id, plan=None) -> str:
        del item, index, theme_id
        self.select_plans.append(plan)
        return self.layout_ids[0]

    def rank(self, item, *, index, theme_id, assets=None, plan=None):
        del item, index, theme_id, assets
        self.rank_plans.append(plan)
        return [
            LayoutCandidateScore(layout_id, float(len(self.layout_ids) - offset), (layout_id,))
            for offset, layout_id in enumerate(self.layout_ids)
        ]

    def content_constraints(self, layout_id: str) -> ContentConstraints:
        del layout_id
        return ContentConstraints(72, 240, 60, 180, 4)


class CountingGate:
    name = "counting"

    def __init__(
        self,
        code: str = "TEXT_TRUNCATED",
        slot: str = "body",
        fail_times: int = 1,
    ) -> None:
        self.calls = 0
        self.code = code
        self.slot = slot
        self.fail_times = fail_times

    def inspect(self, *, png: bytes, slide: dict[str, object], content: SlideContent) -> VisualGateResult:
        del png, slide, content
        self.calls += 1
        if self.calls <= self.fail_times:
            return VisualGateResult(
                extracted_text="",
                issues=[
                    VisualIssue(
                        code=self.code,  # type: ignore[arg-type]
                        message=self.code,
                        slot=self.slot,
                        expected="expected",
                        observed="",
                    )
                ],
            )
        return VisualGateResult(extracted_text="ok", issues=[])


class AlwaysUnreadableGate:
    name = "always-unreadable"

    def __init__(self) -> None:
        self.calls = 0

    def inspect(self, *, png: bytes, slide: dict[str, object], content: SlideContent) -> VisualGateResult:
        del png, slide, content
        self.calls += 1
        return VisualGateResult(
            extracted_text="",
            issues=[
                VisualIssue(
                    code="TEXT_UNREADABLE",
                    message="unreadable",
                    slot="title",
                    expected="T",
                    observed="",
                )
            ],
        )


class ReadableGate:
    name = "readable"

    def inspect(self, *, png: bytes, slide: dict[str, object], content: SlideContent) -> VisualGateResult:
        del png, slide, content
        return VisualGateResult(extracted_text="ok", issues=[])


def _request() -> GenerationRequest:
    return GenerationRequest(
        presentation_id=uuid4(),
        title="T",
        text="B",
        sections=[],
        language="en",
        slide_count=1,
    )


def _outline(*, layout_id: str = "grid") -> StoryOutline:
    return StoryOutline(
        items=[StoryOutlineItem(id="s1", title="T", content="B", layout_id=layout_id)]
    )


def _pipeline(
    *,
    rasterizer=None,
    visual_gate=None,
    generator=None,
    selector=None,
) -> GenerationPipeline:
    return GenerationPipeline(
        story_planner=FakeStoryPlanner(),
        content_generator=generator or RecordingGenerator(),
        slide_validator=None,
        slide_rasterizer=rasterizer,
        visual_gate=visual_gate,
        layout_selector=selector if selector is not None else RankingSelector(["grid", "list"]),
    )


def test_accept_slide_skips_gate_when_unwired() -> None:
    rasterizer = FakeRasterizer()
    pipeline = GenerationPipeline(
        story_planner=FakeStoryPlanner(),
        content_generator=RecordingGenerator(),
        slide_validator=None,
        slide_rasterizer=rasterizer,
        visual_gate=None,
        layout_selector=RankingSelector(["grid", "list"]),
    )
    slide = {"id": "s1", "elements": []}
    outline = StoryOutline(items=[StoryOutlineItem(id="s1", title="T", content="B", layout_id="grid")])
    request = GenerationRequest(
        presentation_id=uuid4(),
        title="T",
        text="B",
        sections=[],
        language="en",
        slide_count=1,
    )
    contents = {
        "s1": SlideContent(slide_id="s1", title="T", layout_id="grid", slots={"body": "B"}),
    }
    out = pipeline.accept_slide(
        slide,
        request=request,
        outline=outline,
        index=0,
        assets={},
        contents=contents,
        plan=None,
    )
    assert out is slide
    assert rasterizer.calls == []


def test_accept_slide_truncates_then_accepts_without_changing_layout() -> None:
    rasterizer = FakeRasterizer()
    generator = RecordingGenerator()
    pipeline = _pipeline(
        rasterizer=rasterizer,
        visual_gate=CountingGate(),
        generator=generator,
        selector=RankingSelector(["grid", "list"]),
    )
    outline = _outline(layout_id="grid")
    contents = {
        "s1": SlideContent(
            slide_id="s1",
            title="T",
            layout_id="grid",
            slots={"body": LONG_BODY},
        )
    }
    original_body = LONG_BODY
    out = pipeline.accept_slide(
        {"id": "s1", "elements": []},
        request=_request(),
        outline=outline,
        index=0,
        assets={},
        contents=contents,
        plan=None,
    )
    repaired_body = str(contents["s1"].slots["body"])
    assert len(rasterizer.calls) == 2
    assert outline.items[0].layout_id == "grid"
    assert contents["s1"].layout_id == "grid"
    assert len(repaired_body) < len(original_body)
    assert out["layout_id"] == "grid"
    assert generator.layout_ids == ["grid"]


def test_accept_slide_second_truncate_shrinks_further_than_one() -> None:
    rasterizer = FakeRasterizer()
    generator = RecordingGenerator()
    pipeline = _pipeline(
        rasterizer=rasterizer,
        visual_gate=CountingGate(fail_times=2, slot="items.2.body"),
        generator=generator,
        selector=RankingSelector(["grid", "list"]),
    )
    outline = _outline(layout_id="grid")
    contents = {
        "s1": SlideContent(
            slide_id="s1",
            title="T",
            layout_id="grid",
            slots={
                "body": LONG_BODY,
                "items": [
                    {"heading": "A", "body": "Alpha point with a full sentence."},
                    {"heading": "B", "body": "Bravo point with a full sentence."},
                    {"heading": "C", "body": "Charlie point with a full sentence."},
                ],
            },
        )
    }
    once_limit = max(48, int(240 * 0.7))
    twice_limit = max(48, int(once_limit * 0.7))
    pipeline.accept_slide(
        {"id": "s1", "elements": []},
        request=_request(),
        outline=outline,
        index=0,
        assets={},
        contents=contents,
        plan=None,
    )
    repaired_items = contents["s1"].slots["items"]
    repaired_body = str(contents["s1"].slots["body"])
    assert isinstance(repaired_items, list)
    assert len(rasterizer.calls) == 3
    assert outline.items[0].layout_id == "grid"
    assert len(repaired_items) == 2
    assert len(repaired_body) <= twice_limit


def test_accept_slide_switches_to_next_ranked_layout_when_unreadable() -> None:
    rasterizer = FakeRasterizer()
    generator = RecordingGenerator()
    pipeline = _pipeline(
        rasterizer=rasterizer,
        visual_gate=CountingGate(code="TEXT_UNREADABLE", slot="title"),
        generator=generator,
        selector=RankingSelector(["grid", "list"]),
    )
    outline = _outline(layout_id="grid")
    contents = {
        "s1": SlideContent(slide_id="s1", title="T", layout_id="grid", slots={"body": "Hello world."}),
    }
    pipeline.accept_slide(
        {"id": "s1", "elements": []},
        request=_request(),
        outline=outline,
        index=0,
        assets={},
        contents=contents,
        plan=None,
    )
    assert outline.items[0].layout_id == "list"
    assert contents["s1"].layout_id == "list"
    assert generator.layout_ids == ["list"]
    assert len(rasterizer.calls) == 2


def test_accept_slide_fails_when_unreadable_and_ranking_exhausted() -> None:
    rasterizer = FakeRasterizer()
    gate = AlwaysUnreadableGate()
    pipeline = _pipeline(
        rasterizer=rasterizer,
        visual_gate=gate,
        selector=RankingSelector(["grid"]),
    )
    outline = _outline(layout_id="grid")
    contents = {
        "s1": SlideContent(slide_id="s1", title="T", layout_id="grid", slots={"body": "Hi"}),
    }
    with pytest.raises(SlideValidationFailed, match="TEXT_UNREADABLE"):
        pipeline.accept_slide(
            {"id": "s1", "elements": []},
            request=_request(),
            outline=outline,
            index=0,
            assets={},
            contents=contents,
            plan=None,
        )
    assert gate.calls <= VISUAL_GATE_MAX_REPAIRS + 1
    assert len(rasterizer.calls) <= VISUAL_GATE_MAX_REPAIRS + 1


def test_accept_slide_skips_gate_when_slide_content_missing() -> None:
    rasterizer = FakeRasterizer()
    pipeline = _pipeline(
        rasterizer=rasterizer,
        visual_gate=CountingGate(),
    )
    slide = {"id": "s1", "elements": []}
    out = pipeline.accept_slide(
        slide,
        request=_request(),
        outline=_outline(),
        index=0,
        assets={},
        contents={},
        plan=None,
    )
    assert out is slide
    assert rasterizer.calls == []


def test_accept_slide_wraps_rasterize_oserror() -> None:
    pipeline = _pipeline(
        rasterizer=ExplodingRasterizer(),
        visual_gate=ReadableGate(),
    )
    contents = {
        "s1": SlideContent(slide_id="s1", title="T", layout_id="grid", slots={"body": "B"}),
    }
    with pytest.raises(SlideValidationFailed, match="VISUAL_RASTERIZE_FAILED"):
        pipeline.accept_slide(
            {"id": "s1", "elements": []},
            request=_request(),
            outline=_outline(),
            index=0,
            assets={},
            contents=contents,
            plan=None,
        )


def test_render_runs_accept_document_when_gate_is_wired() -> None:
    rasterizer = FakeRasterizer()
    pipeline = _pipeline(
        rasterizer=rasterizer,
        visual_gate=ReadableGate(),
    )
    outline = _outline()
    contents = {
        "s1": SlideContent(slide_id="s1", title="T", layout_id="grid", slots={"body": "B"}),
    }
    pipeline.render(_request(), outline, assets={}, contents=contents)
    assert len(rasterizer.calls) == 1


def test_generate_passes_slide_plan_into_visual_repair_rank() -> None:
    selector = RankingSelector(["grid", "list"])
    pipeline = GenerationPipeline(
        story_planner=FakeStoryPlanner(),
        content_generator=RecordingGenerator(),
        deck_planner=OutlineDeckPlanner(),
        slide_planner=OutlineSlidePlanner(),
        layout_selector=selector,
        content_writer=OutlineContentWriter(),
        slide_validator=None,
        slide_rasterizer=FakeRasterizer(),
        visual_gate=CountingGate(code="TEXT_UNREADABLE", slot="title"),
    )
    pipeline.generate(_request())
    assert selector.select_plans
    assert all(plan is not None for plan in selector.select_plans)
    assert selector.rank_plans
    assert selector.rank_plans[0] == selector.select_plans[0]
    assert selector.rank_plans[0] is not None
