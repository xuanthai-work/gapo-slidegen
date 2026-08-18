from typing import Mapping

from ..presenton_template import (
    MODERN_CONTENT_LAYOUT_IDS,
    MODERN_STORY_LAYOUTS,
    ROLE_LAYOUT_CANDIDATES,
    PresentonTemplateAdapter,
)
from ..provider import GenerationRequest
from ..themes import get_theme
from .models import StoryOutline, StoryOutlineItem


class PresentonContentGenerator:
    """Renders the Modern Blue theme by compiling the pinned Presenton template."""

    name = "presenton"

    def __init__(self, template_path: str | None = None) -> None:
        self.adapter = PresentonTemplateAdapter()
        del template_path  # reserved for future template selection

    def _layout_exists(self, layout_id: str) -> bool:
        return layout_id in self.adapter.layout_ids

    @staticmethod
    def _is_visual_role(role: str | None) -> bool:
        return role in {"hook", "problem", "solution", "case-study", "cta", "quote"}

    @staticmethod
    def _has_visual_fallback(item: StoryOutlineItem) -> bool:
        return (item.role in {
            "hook",
            "problem",
            "solution",
            "case-study",
            "cta",
            "quote",
            "features",
            "team",
            "process",
            "timeline",
            "comparison",
            "big-stat",
            "summary",
        }) or PresentonContentGenerator._has_metric_data(item)

    @staticmethod
    def _has_metric_data(item: StoryOutlineItem) -> bool:
        return any(
            (block.get("label") or block.get("value"))
            for block in (item.blocks or [])
            if isinstance(block, dict)
        )

    def _select_layout(
        self,
        item: StoryOutlineItem,
        index: int,
        *,
        assets: Mapping[tuple[int, str], str],
        slide_index: int,
    ) -> str:
        from ..presenton_template import (
            _has_media_slot,
            _has_metric_slots,
            _is_card_grid,
        )

        block_count = len(item.blocks) if item.blocks else 0
        has_metric_blocks = self._has_metric_data(item)
        has_assets = bool(self._slide_assets(assets, slide_index)) or self._has_visual_fallback(item)

        # 1. Explicit layout id from the outline (e.g. chosen by planner/LLM)
        if item.layout_id and self._layout_exists(item.layout_id):
            return item.layout_id
        # 2. Legacy story-layout mapping from the LLM's 'layout' field
        requested_layout = MODERN_STORY_LAYOUTS.get(item.layout or "")
        if requested_layout:
            return requested_layout
        # 3. Semantic role mapping into preferred Presenton layouts, filtered by
        #    content shape so we do not pick a 4-card grid for a single block or
        #    a media layout for roles that are not inherently visual.
        candidates: tuple[str, ...] = ()
        if item.role:
            candidates = ROLE_LAYOUT_CANDIDATES.get(item.role, ())
        for candidate in candidates:
            if not self._layout_exists(candidate):
                continue
            if block_count == 0 and _is_card_grid(candidate):
                continue
            if has_metric_blocks and not _has_metric_slots(candidate) and _is_card_grid(candidate):
                # Prefer metric layouts when blocks carry label/value data.
                continue
            if _has_media_slot(candidate) and not has_assets and not self._is_visual_role(item.role):
                # Non-visual roles should not leave an empty media panel when no
                # assets are resolved.
                continue
            return candidate
        # 4. First slide is always the title/cover layout
        if index == 0:
            return "title_slide"
        # 5. Content-shape fallback for non-cover slides.
        if block_count == 1 and not has_assets:
            return "title_description_bullet_points_list_with_icon"
        if has_metric_blocks and self._layout_exists(
            "title_image_description_list_with_highlighted_text_heading_description"
        ):
            return "title_image_description_list_with_highlighted_text_heading_description"
        # 6. Rotating fallback for variety
        return MODERN_CONTENT_LAYOUT_IDS[(index - 1) % len(MODERN_CONTENT_LAYOUT_IDS)]

    def _build_slide(
        self,
        request: GenerationRequest,
        item: StoryOutlineItem,
        *,
        index: int,
        total: int,
        assets: Mapping[tuple[int, str], str],
    ) -> dict[str, object]:
        return self.adapter.compile_slide(
            self._select_layout(item, index, assets=assets, slide_index=index),
            title=item.title or (request.title if index == 0 else f"Key point {index}"),
            content=item.content,
            slide_index=index,
            slide_count=total,
            blocks=item.blocks or None,
            assets=self._slide_assets(assets, index),
            role=item.role,
            budgets=item.content_budget,
        )

    def render_slides(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: Mapping[tuple[int, str], str],
    ) -> list[dict[str, object]]:
        items = outline.items
        total = len(items)
        slides: list[dict[str, object]] = []
        for index, item in enumerate(items, start=0):
            slides.append(self._build_slide(request, item, index=index, total=total, assets=assets))
        return slides

    def render(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: Mapping[tuple[int, str], str],
    ) -> dict[str, object]:
        theme = get_theme(request.theme_id)
        slides = self.render_slides(request, outline, assets=assets)
        return {
            "id": str(request.presentation_id),
            "schemaVersion": 1,
            "title": request.title,
            "language": request.language,
            "revision": 0,
            "theme": theme,
            "slides": slides,
        }

    def _slide_assets(
        self,
        assets: Mapping[tuple[int, str], str],
        slide_index: int,
    ) -> dict[str, str]:
        return {
            slot_name: asset_id
            for (slide, slot_name), asset_id in assets.items()
            if slide == slide_index
        }
