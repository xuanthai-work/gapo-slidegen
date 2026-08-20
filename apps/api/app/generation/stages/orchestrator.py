from __future__ import annotations

import subprocess
from dataclasses import replace
from typing import Mapping, Protocol

from ..layouts import ContentConstraints
from ..models import DeckPlan, SlideContent, SlidePlan
from ..provider import GenerationRequest, OutlineRequest
from .models import AssetPlan, GeneratedAsset, StoryOutline
from .content_understanding import StubContentUnderstanding
from .protocols import (
    AssetGenerator,
    AssetPlanner,
    ContentGenerator,
    ContentUnderstanding,
    ContentWriter,
    DeckPlanner,
    LayoutSelector,
    SlidePlanner,
    SlideRepairer,
    SlideValidator,
    StoryPlanner,
)
from .visual_gate import VisualGate


class SlideValidationFailed(ValueError):
    pass


class SlideRasterizer(Protocol):
    name: str

    def rasterize(self, slide: dict[str, object]) -> bytes:
        """Return a PNG of the slide at editor stage size (1280×720)."""
        ...


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
        deck_planner: DeckPlanner | None = None,
        slide_planner: SlidePlanner | None = None,
        layout_selector: LayoutSelector | None = None,
        content_writer: ContentWriter | None = None,
        slide_validator: SlideValidator | None = None,
        slide_repairer: SlideRepairer | None = None,
        asset_planner: AssetPlanner | None = None,
        asset_generator: AssetGenerator | None = None,
        slide_rasterizer: SlideRasterizer | None = None,
        visual_gate: VisualGate | None = None,
        visual_gate_max_repairs: int | None = None,
    ) -> None:
        self.story_planner = story_planner
        self.content_generator = content_generator
        self.content_understanding = content_understanding or StubContentUnderstanding()
        self.deck_planner = deck_planner
        self.slide_planner = slide_planner
        self.layout_selector = layout_selector
        self.content_writer = content_writer
        self.slide_validator = slide_validator
        self.slide_repairer = slide_repairer
        self.asset_planner = asset_planner or NullAssetPlanner()
        self.asset_generator = asset_generator or NullAssetGenerator()
        self.slide_rasterizer = slide_rasterizer
        self.visual_gate = visual_gate
        if visual_gate_max_repairs is None:
            from .repair_dispatcher import VISUAL_GATE_MAX_REPAIRS

            visual_gate_max_repairs = VISUAL_GATE_MAX_REPAIRS
        self.visual_gate_max_repairs = visual_gate_max_repairs
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

    def plan_deck(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
    ) -> DeckPlan | None:
        if self.deck_planner is None:
            return None
        deck_plan = self.deck_planner.plan(request, outline)
        if self.slide_planner is None:
            return deck_plan

        refined_slides = []
        for index, current in enumerate(deck_plan.slides):
            refined_slides.append(
                self.slide_planner.plan(
                    deck_plan=deck_plan,
                    current_slide=current,
                    source_item=outline.items[index],
                    previous_slide=deck_plan.slides[index - 1] if index > 0 else None,
                    next_slide=(
                        deck_plan.slides[index + 1]
                        if index + 1 < len(deck_plan.slides)
                        else None
                    ),
                )
            )
        return replace(deck_plan, slides=refined_slides)

    def select_layouts(
        self,
        outline: StoryOutline,
        *,
        theme_id: str,
        deck_plan: DeckPlan | None = None,
    ) -> StoryOutline:
        if self.layout_selector is None:
            return outline
        plans = {plan.id: plan for plan in deck_plan.slides} if deck_plan else {}
        return StoryOutline(
            items=[
                replace(
                    item,
                    layout_id=self.layout_selector.select(
                        item,
                        index=index,
                        theme_id=theme_id,
                        plan=plans.get(item.id),
                    ),
                )
                for index, item in enumerate(outline.items)
            ]
        )

    def write_content(
        self,
        outline: StoryOutline,
        deck_plan: DeckPlan | None = None,
        *,
        language: str = "en",
        source_text: str = "",
    ) -> dict[str, SlideContent]:
        if self.content_writer is None:
            return {}
        if self.layout_selector is None:
            raise ValueError("ContentWriter requires a LayoutSelector")

        constraints = {}
        for item in outline.items:
            if not item.layout_id:
                raise ValueError(f"Slide {item.id!r} has no selected layout")
            constraints[item.id] = self.layout_selector.content_constraints(
                item.layout_id
            )
        if deck_plan is None:
            raise ValueError("ContentWriter requires a DeckPlan")
        return self.content_writer.write_batch(
            outline=outline,
            deck_plan=deck_plan,
            constraints=constraints,
            language=language,
            source_text=source_text,
        )

    def render(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: Mapping[tuple[int, str], str] | None = None,
        contents: Mapping[str, SlideContent] | None = None,
        deck_plan: DeckPlan | None = None,
    ) -> dict[str, object]:
        if contents:
            document = self.content_generator.render(
                request,
                outline,
                assets=assets or {},
                contents=contents,
            )
            mutable_contents = dict(contents)
        else:
            document = self.content_generator.render(
                request,
                outline,
                assets=assets or {},
            )
            mutable_contents = {}
        plans = (
            {plan.id: plan for plan in deck_plan.slides}
            if deck_plan is not None
            else None
        )
        self.accept_document(
            document,
            request=request,
            outline=outline,
            assets=assets or {},
            contents=mutable_contents,
            plans=plans,
        )
        return document

    def accept_slide(
        self,
        slide: dict[str, object],
        *,
        request: GenerationRequest,
        outline: StoryOutline,
        index: int,
        assets: Mapping[tuple[int, str], str],
        contents: dict[str, SlideContent],
        plan: SlidePlan | None = None,
    ) -> dict[str, object]:
        slide = self.validate_slide(slide)
        rasterizer = self.slide_rasterizer
        gate = self.visual_gate
        if gate is None or rasterizer is None:
            return slide
        if index < 0 or index >= len(outline.items):
            return slide
        item = outline.items[index]
        content = contents.get(item.id)
        if content is None:
            return slide

        tried = {item.layout_id or ""}
        last_constraints: ContentConstraints | None = None
        from .repair_dispatcher import apply_repair_action, choose_repair_action

        def layout_constraints(layout_id: str) -> ContentConstraints:
            if self.layout_selector is None:
                return ContentConstraints(72, 240, 60, 180, 4)
            return self.layout_selector.content_constraints(layout_id)

        for attempt in range(self.visual_gate_max_repairs + 1):
            content = contents[item.id]
            try:
                png = rasterizer.rasterize(slide)
            except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as error:
                slide_id = str(slide.get("id") or item.id or "unknown")
                raise SlideValidationFailed(
                    f"Slide {slide_id!r} failed visual validation: VISUAL_RASTERIZE_FAILED"
                ) from error
            result = gate.inspect(png=png, slide=slide, content=content)
            if result.readable:
                return slide
            if attempt == self.visual_gate_max_repairs:
                codes = ", ".join(issue.code for issue in result.issues) or "fail"
                raise SlideValidationFailed(
                    f"Slide {item.id!r} failed visual validation: {codes}"
                )
            action = choose_repair_action(result.issues)
            if self.layout_selector is None:
                ranking = []
                catalog_constraints = ContentConstraints(72, 240, 60, 180, 4)
            else:
                ranking = self.layout_selector.rank(
                    item,
                    index=index,
                    theme_id=request.theme_id,
                    assets=assets,
                    plan=plan,
                )
                catalog_constraints = self.layout_selector.content_constraints(
                    item.layout_id or content.layout_id
                )
            content, last_constraints = apply_repair_action(
                action,
                item=item,
                content=content,
                constraints=last_constraints or catalog_constraints,
                ranking=ranking,
                tried=tried,
                issues=result.issues,
                layout_constraints=layout_constraints,
            )
            contents[item.id] = content
            tried.add(item.layout_id or "")
            slide = self.content_generator.render_slide(
                request,
                outline,
                index=index,
                assets=assets,
                contents=contents,
            )
            slide = self.validate_slide(slide)
        codes = ", ".join(issue.code for issue in result.issues) or "fail"
        raise SlideValidationFailed(
            f"Slide {item.id!r} failed visual validation: {codes}"
        )

    def accept_document(
        self,
        document: dict[str, object],
        *,
        request: GenerationRequest,
        outline: StoryOutline,
        assets: Mapping[tuple[int, str], str],
        contents: dict[str, SlideContent],
        plans: Mapping[str, SlidePlan] | None = None,
    ) -> None:
        slides = document.get("slides")
        if not isinstance(slides, list):
            return
        plan_map = dict(plans) if plans else {}
        for index, slide in enumerate(slides):
            if not isinstance(slide, dict):
                continue
            item_plan = None
            if index < len(outline.items):
                item_plan = plan_map.get(outline.items[index].id)
            slides[index] = self.accept_slide(
                slide,
                request=request,
                outline=outline,
                index=index,
                assets=assets,
                contents=contents,
                plan=item_plan,
            )

    def validate_slide(self, slide: dict[str, object]) -> dict[str, object]:
        if self.slide_validator is None:
            return slide
        result = self.slide_validator.validate(slide)
        if result.valid:
            return slide
        if self.slide_repairer is not None:
            slide = self.slide_repairer.repair(slide, result)
            result = self.slide_validator.validate(slide)
            if result.valid:
                return slide
        codes = ", ".join(issue.code for issue in result.issues)
        slide_id = str(slide.get("id") or "unknown")
        raise SlideValidationFailed(
            f"Slide {slide_id!r} failed visual validation: {codes}"
        )

    def validate_document(self, document: dict[str, object]) -> None:
        slides = document.get("slides")
        if not isinstance(slides, list):
            return
        for index, slide in enumerate(slides):
            if isinstance(slide, dict):
                slides[index] = self.validate_slide(slide)

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
        deck_plan = self.plan_deck(request, outline)
        outline = self.select_layouts(
            outline,
            theme_id=request.theme_id,
            deck_plan=deck_plan,
        )
        contents = self.write_content(
            outline,
            deck_plan,
            language=request.language,
            source_text=request.text,
        )
        asset_plan = self.plan_assets(outline, request)
        generated = self.asset_generator.generate(asset_plan)
        asset_map = _build_asset_map(generated)
        return self.render(
            request,
            outline,
            assets=asset_map,
            contents=contents,
            deck_plan=deck_plan,
        )


def _build_asset_map(generated: list[GeneratedAsset]) -> dict[tuple[int, str], str]:
    mapping: dict[tuple[int, str], str] = {}
    for asset in generated:
        if asset.asset_id is not None:
            mapping[(asset.slot.slide_index, asset.slot.name)] = asset.asset_id
    return mapping
