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

    @staticmethod
    def _cover_layout_id(theme_id: str) -> str:
        if theme_id == "warm-studio":
            return "cover-warm"
        if theme_id == "midnight-signal":
            return "cover-midnight"
        return "cover-editorial"

    @staticmethod
    def _content_layout_id(
        *,
        index: int,
        theme_id: str,
        role: str | None,
        body: str,
    ) -> str:
        orders = {
            "editorial-cobalt": ("header", "split", "statement", "margin", "band", "frame"),
            "warm-studio": ("margin", "frame", "header", "statement", "split", "band"),
            "midnight-signal": ("split", "band", "margin", "frame", "statement", "header"),
        }
        if role in {"big-stat", "quote"}:
            variant = "statement"
        elif role in {"cover", "cta"}:
            variant = "band"
        elif len(body) > 720:
            variant = "header"
        else:
            order = orders.get(theme_id, orders["editorial-cobalt"])
            variant = order[(index - 1) % len(order)]
        return f"content-{variant}"

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
        theme_id = str(_theme["id"])
        items = outline.items
        if not items:
            item = StoryOutlineItem(id=str(uuid4()), title=request.title, content="")
            written = None
            index = 0
        else:
            item = items[index]
            written = contents.get(item.id) if contents else None
        if index == 0:
            return self.registry.compile(
                self._cover_layout_id(theme_id),
                NativeLayoutContext(
                    title=written.title if written else item.title,
                    body=str(written.slots.get("body") or "") if written else item.content,
                    theme_id=theme_id,
                    colors=palette,
                    fonts=typography,
                    total=max(len(items), 1),
                ),
            )
        slots = written.slots if written else {}
        slot_items = slots.get("items")
        return self.registry.compile(
            self._content_layout_id(
                index=index,
                theme_id=theme_id,
                role=item.role,
                body=item.content,
            ),
            NativeLayoutContext(
                title=written.title if written else item.title or f"Key point {index}",
                body=str(slots.get("body") or "") if written else item.content,
                theme_id=theme_id,
                colors=palette,
                fonts=typography,
                index=index,
                total=len(items),
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
