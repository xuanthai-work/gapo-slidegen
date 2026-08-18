"""Content generators turn a story plan and resolved asset map into canonical
slide schema JSON.
"""

from ..provider import GenerationRequest
from ..themes import THEMES
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
    """Return the renderer appropriate for the requested theme."""
    if theme_id in THEMES:
        return PresentonContentGenerator()
    return NativeContentGenerator()


class ThemeDispatchContentGenerator:
    """Content generator that selects the concrete renderer per-request by theme."""

    name = "dispatch"

    def _delegate(
        self,
        request: GenerationRequest,
    ) -> NativeContentGenerator | PresentonContentGenerator:
        return build_content_generator(request.theme_id)

    def render_slides(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: dict[tuple[int, str], str],
    ) -> list[dict[str, object]]:
        return self._delegate(request).render_slides(request, outline, assets=assets)

    def render(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: dict[tuple[int, str], str],
    ) -> dict[str, object]:
        return self._delegate(request).render(request, outline, assets=assets)
