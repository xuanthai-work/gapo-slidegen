from typing import Mapping

from ..provider import GenerationRequest, OutlineRequest
from .models import AssetPlan, GeneratedAsset, StoryOutline
from .content_understanding import StubContentUnderstanding
from .protocols import (
    AssetGenerator,
    AssetPlanner,
    ContentGenerator,
    ContentUnderstanding,
    LayoutSelector,
    StoryPlanner,
)


class NullAssetPlanner:
    """Default no-op asset planner when the product does not auto-generate assets."""

    name = "null"

    def plan(self, outline: StoryOutline, request: GenerationRequest) -> AssetPlan:
        del outline, request
        return AssetPlan()


class NullAssetGenerator:
    """Default no-op asset generator; placeholders remain in the rendered schema."""

    name = "null"

    def generate(self, plan: AssetPlan) -> list[GeneratedAsset]:
        del plan
        return []


class GenerationPipeline:
    """Orchestrates generation stages in the order defined by the ADR.

    The pipeline is provider-agnostic: each stage is injected at construction
    time so tests and different environments can mix stubs, LLM providers, and
    real asset generation freely.
    """

    def __init__(
        self,
        *,
        story_planner: StoryPlanner,
        content_generator: ContentGenerator,
        content_understanding: ContentUnderstanding | None = None,
        layout_selector: LayoutSelector | None = None,
        asset_planner: AssetPlanner | None = None,
        asset_generator: AssetGenerator | None = None,
    ) -> None:
        self.story_planner = story_planner
        self.content_generator = content_generator
        self.content_understanding = content_understanding or StubContentUnderstanding()
        self.layout_selector = layout_selector
        self.asset_planner = asset_planner or NullAssetPlanner()
        self.asset_generator = asset_generator or NullAssetGenerator()
        self.name = story_planner.name

    def generate_outline(self, request: OutlineRequest) -> list[dict[str, object]]:
        understanding: dict[str, object] | None = None
        if self.content_understanding is not None:
            try:
                result = self.content_understanding.understand(
                    title=request.title,
                    text=request.text,
                    sections=request.sections,
                    language=request.language,
                    source_kind=request.source_kind,
                )
                if result is not None:
                    understanding = {
                        "intent": result.intent,
                        "audience": result.audience,
                        "tone": result.tone,
                        "key_takeaways": result.key_takeaways,
                    }
            except Exception:
                # Content understanding is optional; falling back keeps generation
                # robust even if the chat provider is slow or unavailable.
                pass
        return self.story_planner.generate_outline(request, understanding=understanding)

    def plan_assets(
        self,
        outline: StoryOutline,
        request: GenerationRequest,
    ) -> AssetPlan:
        return self.asset_planner.plan(outline, request)

    def render(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: Mapping[tuple[int, str], str] | None = None,
    ) -> dict[str, object]:
        return self.content_generator.render(
            request,
            outline,
            assets=assets or {},
        )

    def generate(self, request: GenerationRequest) -> dict[str, object]:
        """Backward-compatible convenience method that runs the full pipeline.

        Asset generation is disabled so this path stays safe for unit tests and
        for environments without a configured image provider.
        """
        outline = StoryOutline.from_dicts(
            request.outline or self.generate_outline(
                OutlineRequest(
                    title=request.title,
                    text=request.text,
                    sections=request.sections,
                    language=request.language,
                    slide_count=request.slide_count,
                    source_kind=request.source_kind,
                )
            )
        )
        asset_plan = self.plan_assets(outline, request)
        generated = self.asset_generator.generate(asset_plan)
        asset_map = _build_asset_map(generated)
        return self.render(request, outline, assets=asset_map)


def _build_asset_map(generated: list[GeneratedAsset]) -> dict[tuple[int, str], str]:
    mapping: dict[tuple[int, str], str] = {}
    for asset in generated:
        if asset.asset_id is not None:
            mapping[(asset.slot.slide_index, asset.slot.name)] = asset.asset_id
    return mapping
