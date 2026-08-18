from uuid import uuid4

from app.generation.provider import GenerationRequest, OutlineRequest
from app.generation.stages import (
    AssetPlan,
    AssetRequest,
    AssetSlot,
    GenerationPipeline,
    GeneratedAsset,
    StoryOutline,
    StoryOutlineItem,
)
from app.generation.stages.orchestrator import NullAssetPlanner


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

    def plan(self, outline: StoryOutline, request: GenerationRequest) -> AssetPlan:
        del request
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
