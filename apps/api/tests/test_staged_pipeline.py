from uuid import uuid4

import pytest

from app.generation.layouts import ContentConstraints
from app.generation.models import SlideContent, SlidePlan
from app.generation.provider import GenerationRequest, OutlineRequest
from app.generation.stages.deck_planner import OutlineDeckPlanner
from app.generation.stages import (
    AssetPlan,
    AssetRequest,
    AssetSlot,
    GenerationPipeline,
    GeneratedAsset,
    StoryOutline,
    StoryOutlineItem,
)
from app.generation.stages.orchestrator import NullAssetPlanner, SlideValidationFailed
from app.generation.stages.slide_validator import (
    SlideValidationIssue,
    SlideValidationResult,
)
from app.generation.stages.slide_planner import OutlineSlidePlanner


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


class FakeContentGenerator:
    name = "fake-renderer"

    def __init__(self) -> None:
        self.calls: list[tuple[GenerationRequest, StoryOutline, dict[tuple[int, str], str]]] = []

    def render(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: dict[tuple[int, str], str],
    ) -> dict[str, object]:
        self.calls.append((request, outline, assets))
        return {
            "id": str(request.presentation_id),
            "schemaVersion": 1,
            "title": request.title,
            "language": request.language,
            "theme": {"id": request.theme_id},
            "slides": [{"id": "slide-1", "title": outline.items[0].title, "elements": []}],
            "revision": 0,
        }


class FakeAssetPlanner:
    name = "fake-asset-planner"

    def __init__(self) -> None:
        self.outlines: list[StoryOutline] = []

    def plan(self, outline: StoryOutline, request: GenerationRequest) -> AssetPlan:
        del request
        self.outlines.append(outline)
        return AssetPlan(
            requests=[
                AssetRequest(
                    slot=AssetSlot(slide_index=1, name="hero", kind="image"),
                    prompt=f"Image for: {outline.items[1].title}",
                )
            ]
        )


class FakeAssetGenerator:
    name = "fake-asset-gen"

    def generate(self, plan: AssetPlan) -> list[GeneratedAsset]:
        return [
            GeneratedAsset(
                slot=request.slot,
                asset_id=f"asset-{request.slot.slide_index}-{request.slot.name}",
            )
            for request in plan.requests
        ]


class FakeLayoutSelector:
    name = "fake-layout-selector"

    def __init__(self) -> None:
        self.calls: list[tuple[str, int, str]] = []
        self.plans: list[SlidePlan | None] = []

    def select(
        self,
        item: StoryOutlineItem,
        *,
        index: int,
        theme_id: str,
        plan: SlidePlan | None = None,
    ) -> str:
        self.calls.append((item.id, index, theme_id))
        self.plans.append(plan)
        return "title_slide" if index == 0 else "comparison-2col"

    def content_constraints(self, layout_id: str) -> ContentConstraints:
        max_items = 0 if layout_id == "title_slide" else 2
        return ContentConstraints(72, 180, 55, 120, max_items)


class FakeContentWriter:
    name = "fake-content-writer"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, ContentConstraints]] = []
        self.batch_calls = 0

    def write_batch(
        self,
        *,
        outline: StoryOutline,
        deck_plan,
        constraints: dict[str, ContentConstraints],
        language: str,
    ) -> dict[str, SlideContent]:
        del language
        self.batch_calls += 1
        plans = {plan.id: plan for plan in deck_plan.slides}
        return {
            item.id: self.write(
                item,
                layout_id=item.layout_id or "",
                constraints=constraints[item.id],
                plan=plans.get(item.id),
            )
            for item in outline.items
        }

    def write(
        self,
        item: StoryOutlineItem,
        *,
        layout_id: str,
        constraints: ContentConstraints,
        plan: SlidePlan | None = None,
    ) -> SlideContent:
        del plan
        self.calls.append((item.id, layout_id, constraints))
        return SlideContent(
            slide_id=item.id,
            layout_id=layout_id,
            title=item.title,
            slots={"body": item.content, "items": item.blocks},
        )


class NamedSlotContentGenerator(FakeContentGenerator):
    def __init__(self) -> None:
        super().__init__()
        self.contents: dict[str, SlideContent] = {}

    def render(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: dict[tuple[int, str], str],
        contents: dict[str, SlideContent] | None = None,
    ) -> dict[str, object]:
        self.contents = contents or {}
        return super().render(request, outline, assets=assets)


class FakeSlideValidator:
    name = "fake-slide-validator"

    def __init__(self) -> None:
        self.slide_ids: list[str] = []

    def validate(self, slide: dict[str, object]) -> SlideValidationResult:
        self.slide_ids.append(str(slide["id"]))
        return SlideValidationResult()


class FailingSlideValidator(FakeSlideValidator):
    def validate(self, slide: dict[str, object]) -> SlideValidationResult:
        super().validate(slide)
        return SlideValidationResult(
            issues=[
                SlideValidationIssue(
                    code="ELEMENT_OUT_OF_BOUNDS",
                    message="outside",
                    element_ids=("title",),
                )
            ]
        )


class RepairAwareValidator(FakeSlideValidator):
    def validate(self, slide: dict[str, object]) -> SlideValidationResult:
        super().validate(slide)
        if slide.get("repaired"):
            return SlideValidationResult()
        return SlideValidationResult(
            issues=[
                SlideValidationIssue(
                    code="ELEMENT_OUT_OF_BOUNDS",
                    message="outside",
                    element_ids=("title",),
                )
            ]
        )


class FakeSlideRepairer:
    name = "fake-slide-repairer"

    def repair(
        self,
        slide: dict[str, object],
        validation: SlideValidationResult,
    ) -> dict[str, object]:
        assert not validation.valid
        return {**slide, "repaired": True}


def test_pipeline_validates_compiled_slides() -> None:
    validator = FakeSlideValidator()
    pipeline = GenerationPipeline(
        story_planner=FakeStoryPlanner(),
        content_generator=FakeContentGenerator(),
        slide_validator=validator,
    )

    pipeline.generate(
        GenerationRequest(
            presentation_id=uuid4(),
            title="Validated",
            text="Source text",
            sections=[],
            language="en",
            slide_count=2,
        )
    )

    assert validator.slide_ids == ["slide-1"]


def test_pipeline_repairs_then_revalidates_compiled_slides() -> None:
    validator = RepairAwareValidator()
    pipeline = GenerationPipeline(
        story_planner=FakeStoryPlanner(),
        content_generator=FakeContentGenerator(),
        slide_validator=validator,
        slide_repairer=FakeSlideRepairer(),
    )

    document = pipeline.generate(
        GenerationRequest(
            presentation_id=uuid4(),
            title="Repaired",
            text="Source text",
            sections=[],
            language="en",
            slide_count=2,
        )
    )

    assert document["slides"][0]["repaired"] is True
    assert validator.slide_ids == ["slide-1", "slide-1"]


def test_pipeline_rejects_slides_that_fail_exact_validation() -> None:
    pipeline = GenerationPipeline(
        story_planner=FakeStoryPlanner(),
        content_generator=FakeContentGenerator(),
        slide_validator=FailingSlideValidator(),
    )

    with pytest.raises(SlideValidationFailed, match="ELEMENT_OUT_OF_BOUNDS"):
        pipeline.generate(
            GenerationRequest(
                presentation_id=uuid4(),
                title="Invalid",
                text="Source text",
                sections=[],
                language="en",
                slide_count=2,
            )
        )


def test_pipeline_writes_named_slot_content_after_layout_selection() -> None:
    selector = FakeLayoutSelector()
    writer = FakeContentWriter()
    renderer = NamedSlotContentGenerator()
    pipeline = GenerationPipeline(
        story_planner=FakeStoryPlanner(),
        content_generator=renderer,
        deck_planner=OutlineDeckPlanner(),
        slide_planner=OutlineSlidePlanner(),
        layout_selector=selector,
        content_writer=writer,
    )

    pipeline.generate(
        GenerationRequest(
            presentation_id=uuid4(),
            title="Named slots",
            text="Source text",
            sections=[],
            language="en",
            slide_count=2,
            theme_id="modern-blue",
        )
    )

    assert [(item_id, layout_id) for item_id, layout_id, _ in writer.calls] == [
        ("cover", "title_slide"),
        ("point-1", "comparison-2col"),
    ]
    assert renderer.contents["point-1"].slots["body"] == "First takeaway."
    assert writer.batch_calls == 1


def test_pipeline_refines_slide_plans_before_layout_selection() -> None:
    selector = FakeLayoutSelector()
    pipeline = GenerationPipeline(
        story_planner=FakeStoryPlanner(),
        content_generator=FakeContentGenerator(),
        deck_planner=OutlineDeckPlanner(),
        slide_planner=OutlineSlidePlanner(),
        layout_selector=selector,
    )

    pipeline.generate(
        GenerationRequest(
            presentation_id=uuid4(),
            title="Semantic planning",
            text="Source text",
            sections=[],
            language="en",
            slide_count=2,
        )
    )

    assert [plan.content_structure for plan in selector.plans if plan] == [
        "headline",
        "title-body",
    ]
    assert [plan.id for plan in selector.plans if plan] == ["cover", "point-1"]


def test_pipeline_selects_layouts_before_asset_planning_and_rendering() -> None:
    selector = FakeLayoutSelector()
    asset_planner = FakeAssetPlanner()
    renderer = FakeContentGenerator()
    pipeline = GenerationPipeline(
        story_planner=FakeStoryPlanner(),
        content_generator=renderer,
        layout_selector=selector,
        asset_planner=asset_planner,
        asset_generator=FakeAssetGenerator(),
    )

    pipeline.generate(
        GenerationRequest(
            presentation_id=uuid4(),
            title="Layout stage",
            text="Source text",
            sections=[],
            language="en",
            slide_count=2,
            theme_id="modern-blue",
        )
    )

    assert selector.calls == [
        ("cover", 0, "modern-blue"),
        ("point-1", 1, "modern-blue"),
    ]
    assert [item.layout_id for item in asset_planner.outlines[0].items] == [
        "title_slide",
        "comparison-2col",
    ]
    assert [item.layout_id for item in renderer.calls[0][1].items] == [
        "title_slide",
        "comparison-2col",
    ]


def test_pipeline_runs_stages_in_order_with_asset_injection() -> None:
    story = FakeStoryPlanner()
    renderer = FakeContentGenerator()
    pipeline = GenerationPipeline(
        story_planner=story,
        content_generator=renderer,
        asset_planner=FakeAssetPlanner(),
        asset_generator=FakeAssetGenerator(),
    )
    presentation_id = uuid4()
    document = pipeline.generate(
        GenerationRequest(
            presentation_id=presentation_id,
            title="Staged test",
            text="Source text",
            sections=[],
            language="en",
            slide_count=2,
            theme_id="modern-blue",
        )
    )

    assert document["id"] == str(presentation_id)
    assert document["slides"][0]["title"] == "Staged test"
    assert renderer.calls
    _, _, assets = renderer.calls[0]
    assert assets == {(1, "hero"): "asset-1-hero"}


def test_null_asset_planner_yields_empty_plan() -> None:
    planner = NullAssetPlanner()
    outline = StoryOutline(items=[StoryOutlineItem(id="x", title="T", content="C")])
    plan = planner.plan(
        outline,
        GenerationRequest(
            presentation_id=uuid4(),
            title="T",
            text="t",
            sections=[],
            language="en",
            slide_count=1,
        ),
    )
    assert plan.requests == []
