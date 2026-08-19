from typing import Mapping

from ..presenton_template import (
    PresentonTemplateAdapter,
)
from ..models import SlideContent
from ..provider import GenerationRequest
from ..themes import get_theme
from .layout_selector import PresentonLayoutSelector
from .models import StoryOutline, StoryOutlineItem


class PresentonContentGenerator:
    """Renders the Modern Blue theme by compiling the pinned Presenton template."""

    name = "presenton"

    def __init__(self, template_path: str | None = None) -> None:
        self.adapter = PresentonTemplateAdapter()
        self.layout_selector = PresentonLayoutSelector(self.adapter)
        del template_path  # reserved for future template selection

    def _build_slide(
        self,
        request: GenerationRequest,
        item: StoryOutlineItem,
        *,
        index: int,
        total: int,
        assets: Mapping[tuple[int, str], str],
        contents: Mapping[str, SlideContent] | None,
    ) -> dict[str, object]:
        layout_id = self.layout_selector.select(
            item,
            index=index,
            theme_id=request.theme_id,
            assets=assets,
        )
        written = contents.get(item.id) if contents else None
        slots = written.slots if written else {}
        slot_items = slots.get("items")
        blocks = (
            [dict(block) for block in slot_items if isinstance(block, dict)]
            if isinstance(slot_items, list)
            else item.blocks or None
        )
        return self.adapter.compile_slide(
            layout_id,
            title=written.title if written else item.title or (
                request.title if index == 0 else f"Key point {index}"
            ),
            content=str(slots.get("body") or "") if written else item.content,
            slide_index=index,
            slide_count=total,
            blocks=blocks,
            assets=self._slide_assets(assets, index),
            role=item.role,
            budgets=item.content_budget,
        )

    def render_slide(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        index: int,
        assets: Mapping[tuple[int, str], str],
        contents: Mapping[str, SlideContent] | None = None,
    ) -> dict[str, object]:
        return self._build_slide(
            request,
            outline.items[index],
            index=index,
            total=len(outline.items),
            assets=assets,
            contents=contents,
        )

    def render_slides(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: Mapping[tuple[int, str], str],
        contents: Mapping[str, SlideContent] | None = None,
    ) -> list[dict[str, object]]:
        return [
            self.render_slide(
                request,
                outline,
                index=index,
                assets=assets,
                contents=contents,
            )
            for index in range(len(outline.items))
        ]

    def render(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: Mapping[tuple[int, str], str],
        contents: Mapping[str, SlideContent] | None = None,
    ) -> dict[str, object]:
        theme = get_theme(request.theme_id)
        slides = self.render_slides(request, outline, assets=assets, contents=contents)
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
