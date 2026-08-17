"""Content generators turn a story plan and resolved asset map into canonical
slide schema JSON.
"""

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
    """Return the renderer appropriate for the requested theme."""
    if theme_id == "modern-blue":
        return PresentonContentGenerator()
    return NativeContentGenerator()


class ThemeDispatchContentGenerator:
    """Content generator that selects the concrete renderer per-request by theme."""

    name = "dispatch"

    def render(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: dict[tuple[int, str], str],
    ) -> dict[str, object]:
        return build_content_generator(request.theme_id).render(
            request, outline, assets=assets
        )
