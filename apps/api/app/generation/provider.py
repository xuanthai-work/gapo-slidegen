from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

if TYPE_CHECKING:
    from .events import GenerationEvent
    from .layouts import ContentConstraints
    from .models import DeckPlan
    from .stages.models import StoryOutline


STORY_LAYOUT_IDS = (
    "cover",
    "feature-grid",
    "feature-list",
    "split-image",
    "alternating-cards",
    "profile-cards",
    "highlight-metrics",
)


class ProviderError(RuntimeError):
    """Safe provider failure that may be surfaced to an API client or job."""


class ProviderConfigurationError(ProviderError):
    pass


class ProviderResponseError(ProviderError):
    pass


class GenerationCancelledError(ProviderError):
    """Generation stopped because its owning job was cancelled."""


@dataclass(frozen=True, slots=True)
class OutlineRequest:
    title: str
    text: str
    sections: list[dict[str, object]]
    language: str
    slide_count: int | None
    source_kind: str = "prompt"


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    presentation_id: UUID
    title: str
    text: str
    sections: list[dict[str, object]]
    language: str
    slide_count: int | None
    outline: list[dict[str, object]] = field(default_factory=list)
    source_kind: str = "prompt"
    theme_id: str = "modern-blue"


@dataclass(frozen=True, slots=True)
class RewriteRequest:
    text: str
    instruction: str
    language: str


@dataclass(frozen=True, slots=True)
class RewriteTextItem:
    id: str
    text: str


@dataclass(frozen=True, slots=True)
class SlideRewriteRequest:
    items: list[RewriteTextItem]
    instruction: str
    language: str


class PresentationProvider(Protocol):
    name: str

    def generate(self, request: GenerationRequest) -> dict[str, object]: ...


class OutlineProvider(Protocol):
    name: str

    def generate_outline(self, request: OutlineRequest) -> list[dict[str, object]]: ...


class RewriteProvider(Protocol):
    name: str

    def rewrite_text(self, request: RewriteRequest) -> str: ...

    def rewrite_slide(self, request: SlideRewriteRequest) -> list[RewriteTextItem]: ...


class DeckStreamingProvider(Protocol):
    """Streams normalized events for one tagged whole-deck generation call."""

    name: str

    def stream_deck_content(
        self,
        *,
        job_id: str,
        outline: StoryOutline,
        deck_plan: DeckPlan,
        selected_layouts: Mapping[str, str],
        layout_slots: Mapping[str, Sequence[str]],
        constraints: Mapping[str, ContentConstraints],
        language: str,
        attempt: int,
        is_cancelled: Callable[[], bool],
        source_text: str = "",
    ) -> Iterator[GenerationEvent]: ...
