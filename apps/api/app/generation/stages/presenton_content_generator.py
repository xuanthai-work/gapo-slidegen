from typing import Mapping
from uuid import uuid4

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

    def _select_layout(self, item: StoryOutlineItem, index: int) -> str:
        # 1. Explicit layout id from the outline (e.g. chosen by planner/LLM)
        if item.layout_id and self._layout_exists(item.layout_id):
            return item.layout_id
        # 2. Legacy story-layout mapping from the LLM's 'layout' field
        requested_layout = MODERN_STORY_LAYOUTS.get(item.layout or "")
        if requested_layout:
            return requested_layout
        # 3. Semantic role mapping into preferred Presenton layouts
        if item.role:
            for candidate in ROLE_LAYOUT_CANDIDATES.get(item.role, ()):
                if self._layout_exists(candidate):
                    return candidate
        # 4. First slide is always the title/cover layout
        if index == 0:
            return "title_slide"
        # 5. Rotating fallback for variety
        return MODERN_CONTENT_LAYOUT_IDS[(index - 1) % len(MODERN_CONTENT_LAYOUT_IDS)]

    def render(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: Mapping[tuple[int, str], str],
    ) -> dict[str, object]:
        theme = get_theme(request.theme_id)
        items = outline.items
        title_item = items[0] if items else StoryOutlineItem(id=str(uuid4()), title=request.title, content="")
        total = len(items)
        slides = [
            self.adapter.compile_slide(
                self._select_layout(title_item, 0),
                title=title_item.title,
                content=title_item.content,
                slide_index=0,
                slide_count=total,
                assets=self._slide_assets(assets, 0),
            )
        ]
        for index, item in enumerate(items[1:], start=1):
            blocks = item.blocks or None
            slides.append(
                self.adapter.compile_slide(
                    self._select_layout(item, index),
                    title=item.title or f"Key point {index}",
                    content=item.content,
                    slide_index=index,
                    slide_count=total,
                    blocks=blocks if blocks else None,
                    assets=self._slide_assets(assets, index),
                )
            )
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
