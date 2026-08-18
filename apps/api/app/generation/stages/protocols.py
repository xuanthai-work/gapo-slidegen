from typing import Mapping, Protocol

from ..provider import GenerationRequest, OutlineRequest
from .models import (
    AssetPlan,
    ContentUnderstandingResult,
    GeneratedAsset,
    StoryOutline,
    StoryOutlineItem,
)


class ContentUnderstanding(Protocol):
    """Optional stage that builds a semantic summary from a normalized source."""

    name: str

    def understand(
        self,
        *,
        title: str,
        text: str,
        sections: list[dict[str, object]],
        language: str,
        source_kind: str,
    ) -> ContentUnderstandingResult | None:
        ...


class StoryPlanner(Protocol):
    """Produces the ordered story plan (outline) for a source."""

    name: str

    def generate_outline(
        self,
        request: OutlineRequest,
        understanding: dict[str, object] | None = None,
    ) -> list[dict[str, object]]:
        ...


class LayoutSelector(Protocol):
    """Maps a story item and theme to the concrete layout implementation."""

    name: str

    def select(self, item: StoryOutlineItem, *, theme_id: str) -> str:
        ...


class ContentGenerator(Protocol):
    """Renders the final canonical slide schema from a story plan and assets."""

    name: str

    def render(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: Mapping[tuple[int, str], str],
    ) -> dict[str, object]:
        ...

    def render_slides(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: Mapping[tuple[int, str], str],
    ) -> list[dict[str, object]]:
        """Render each slide individually for streaming previews.

        Implementations should return a list of slide documents in order. The
        orchestrator/worker can emit a Server-Sent Event after each slide.
        """
        ...


class AssetPlanner(Protocol):
    """Decides which slides need generated or imported assets."""

    name: str

    def plan(self, outline: StoryOutline, request: GenerationRequest) -> AssetPlan:
        ...


class AssetGenerator(Protocol):
    """Executes an asset plan and returns resolved asset ids."""

    name: str

    def generate(self, plan: AssetPlan) -> list[GeneratedAsset]:
        ...
