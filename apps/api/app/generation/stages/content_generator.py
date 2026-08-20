"""Content generators turn a story plan and resolved asset map into canonical
slide schema JSON.
"""

from typing import Mapping

from ..models import SlideContent
from ..provider import GenerationRequest
from .models import StoryOutline
from .native_content_generator import NativeContentGenerator
from .presenton_content_generator import PresentonContentGenerator
from .protocols import ContentGenerator

__all__ = [
    "ContentGenerator",
    "NativeContentGenerator",
    "PresentonContentGenerator",
    "ThemeDispatchContentGenerator",
    "build_content_generator",
]


def build_content_generator(theme_id: str) -> ContentGenerator:
    """Return the Presenton renderer for the requested template."""
    from ..themes import parse_theme_ref

    template_id, _scheme = parse_theme_ref(theme_id)
    return PresentonContentGenerator(template_id=template_id)


class ThemeDispatchContentGenerator:
    """Content generator that selects the concrete renderer per-request by theme."""

    name = "dispatch"

    def _delegate(
        self,
        request: GenerationRequest,
    ) -> NativeContentGenerator | PresentonContentGenerator:
        return build_content_generator(request.theme_id)

    def render_slide(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        index: int,
        assets: Mapping[tuple[int, str], str],
        contents: Mapping[str, SlideContent] | None = None,
    ) -> dict[str, object]:
        return self._delegate(request).render_slide(
            request,
            outline,
            index=index,
            assets=assets,
            contents=contents,
        )

    def render_slides(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: dict[tuple[int, str], str],
        contents: Mapping[str, SlideContent] | None = None,
    ) -> list[dict[str, object]]:
        return self._delegate(request).render_slides(
            request,
            outline,
            assets=assets,
            contents=contents,
        )

    def render(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: dict[tuple[int, str], str],
        contents: Mapping[str, SlideContent] | None = None,
    ) -> dict[str, object]:
        return self._delegate(request).render(
            request,
            outline,
            assets=assets,
            contents=contents,
        )
