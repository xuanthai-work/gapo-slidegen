from typing import Mapping, Protocol

from ..layouts import ContentConstraints
from ..models import DeckPlan, SlideContent, SlidePlan
from ..provider import GenerationRequest, OutlineRequest
from .models import (
    AssetPlan,
    ContentUnderstandingResult,
    GeneratedAsset,
    StoryOutline,
    StoryOutlineItem,
)
from .slide_validator import SlideValidationResult


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


class DeckPlanner(Protocol):
    """Produces the presentation-level narrative without rendered copy."""

    name: str

    def plan(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
    ) -> DeckPlan:
        ...


class SlidePlanner(Protocol):
    """Refines one deck entry using its source item and neighboring slides."""

    name: str

    def plan(
        self,
        *,
        deck_plan: DeckPlan,
        current_slide: SlidePlan,
        source_item: StoryOutlineItem,
        previous_slide: SlidePlan | None,
        next_slide: SlidePlan | None,
    ) -> SlidePlan:
        ...


class LayoutSelector(Protocol):
    """Maps a story item and theme to the concrete layout implementation."""

    name: str

    def select(
        self,
        item: StoryOutlineItem,
        *,
        index: int,
        theme_id: str,
        plan: SlidePlan | None = None,
    ) -> str:
        ...

    def content_constraints(self, layout_id: str) -> ContentConstraints:
        ...


class ContentWriter(Protocol):
    """Writes audience-facing copy into the selected layout's named slots."""

    name: str

    def write_batch(
        self,
        *,
        outline: StoryOutline,
        deck_plan: DeckPlan,
        constraints: dict[str, ContentConstraints],
        language: str,
    ) -> dict[str, SlideContent]:
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
        contents: Mapping[str, SlideContent] | None = None,
    ) -> dict[str, object]:
        ...

    def render_slide(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        index: int,
        assets: Mapping[tuple[int, str], str],
        contents: Mapping[str, SlideContent] | None = None,
    ) -> dict[str, object]:
        """Compile one canonical slide from already-written named-slot content."""
        ...

    def render_slides(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: Mapping[tuple[int, str], str],
        contents: Mapping[str, SlideContent] | None = None,
    ) -> list[dict[str, object]]:
        """Render each slide individually for streaming previews.

        Implementations should return a list of slide documents in order. The
        orchestrator/worker can emit a Server-Sent Event after each slide.
        """
        ...


class SlideValidator(Protocol):
    """Runs deterministic checks against compiled canonical slide JSON."""

    name: str

    def validate(self, slide: dict[str, object]) -> SlideValidationResult:
        ...


class SlideRepairer(Protocol):
    """Applies deterministic fixes using exact validator findings."""

    name: str

    def repair(
        self,
        slide: dict[str, object],
        validation: SlideValidationResult,
    ) -> dict[str, object]:
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
