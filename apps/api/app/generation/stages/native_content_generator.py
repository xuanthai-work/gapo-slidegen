from typing import Mapping
from uuid import uuid4

from ..layouts import (
    NativeLayoutContext,
    NativeLayoutRegistry,
    build_native_layout_registry,
)
from ..models import SlideContent
from ..provider import GenerationRequest
from ..themes import get_theme
from .layout_selector import NativeLayoutSelector
from .models import StoryOutline, StoryOutlineItem


def _chunks(text: str, count: int) -> list[str]:
    if count <= 0:
        return []
    words = text.split()
    if not words:
        return [""] * count
    size = max(1, (len(words) + count - 1) // count)
    chunks = [" ".join(words[index : index + size]) for index in range(0, len(words), size)]
    return (chunks + [""] * count)[:count]


def _automatic_slide_count(text: str) -> int:
    word_count = len(text.split())
    return max(5, min(15, 4 + (word_count + 119) // 120))


class NativeContentGenerator:
    """Compiles compatibility themes through product-owned native layouts."""

    name = "native"

    def __init__(self, registry: NativeLayoutRegistry | None = None) -> None:
        self.registry = registry or build_native_layout_registry()
        self._layout_selector = NativeLayoutSelector()

    def _render_theme(
        self,
        request: GenerationRequest,
    ) -> tuple[dict[str, object], dict[str, str], dict[str, str]]:
        theme = get_theme(request.theme_id)
        colors = theme["colors"]
        fonts = theme["fonts"]
        if not isinstance(colors, dict) or not isinstance(fonts, dict):
            raise ValueError("Theme configuration is invalid")
        palette = {key: str(value) for key, value in colors.items()}
        typography = {key: str(value) for key, value in fonts.items()}
        return theme, palette, typography

    def _resolve_layout_id(
        self,
        item: StoryOutlineItem,
        *,
        index: int,
        theme_id: str,
    ) -> str:
        if item.layout_id:
            return item.layout_id
        return self._layout_selector.select(item, index=index, theme_id=theme_id)

    def render_slide(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        index: int,
        assets: Mapping[tuple[int, str], str],
        contents: Mapping[str, SlideContent] | None = None,
    ) -> dict[str, object]:
        del assets
        _theme, palette, typography = self._render_theme(request)
        theme_id = request.theme_id
        items = outline.items
        if not items:
            item = StoryOutlineItem(id=str(uuid4()), title=request.title, content="")
            written = None
            index = 0
        else:
            item = items[index]
            written = contents.get(item.id) if contents else None
        slots = written.slots if written else {}
        slot_items = slots.get("items")
        return self.registry.compile(
            self._resolve_layout_id(item, index=index, theme_id=theme_id),
            NativeLayoutContext(
                title=written.title if written else item.title or (
                    request.title if index == 0 else f"Key point {index}"
                ),
                body=str(slots.get("body") or "") if written else item.content,
                theme_id=theme_id,
                colors=palette,
                fonts=typography,
                index=index,
                total=max(len(items), 1),
                blocks=(
                    [dict(block) for block in slot_items if isinstance(block, dict)]
                    if isinstance(slot_items, list)
                    else item.blocks
                ),
            ),
        )

    def render_slides(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: Mapping[tuple[int, str], str],
        contents: Mapping[str, SlideContent] | None = None,
    ) -> list[dict[str, object]]:
        if not outline.items:
            return [
                self.render_slide(
                    request,
                    outline,
                    index=0,
                    assets=assets,
                    contents=contents,
                )
            ]
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
        theme, _, _ = self._render_theme(request)
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
