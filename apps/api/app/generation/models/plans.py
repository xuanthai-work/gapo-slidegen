from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ContentDensity = Literal["low", "medium", "high"]
ImageRequirement = Literal["none", "optional", "required"]
VisualPriority = Literal["content", "balanced", "visual"]


@dataclass(frozen=True, slots=True)
class SlidePlan:
    """Semantic instructions for one slide, without rendered copy or geometry."""

    id: str
    index: int
    role: str
    communication_goal: str
    content_structure: str
    item_count: int = 0
    relationship: str = "none"
    visual_priority: VisualPriority = "content"
    image_requirement: ImageRequirement = "none"
    density: ContentDensity = "medium"
    preferred_archetype: str | None = None


@dataclass(frozen=True, slots=True)
class DeckPlan:
    """Presentation-level narrative and its ordered semantic slide plans."""

    title: str
    audience: str
    objective: str
    narrative_arc: str
    language: str
    slides: list[SlidePlan] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SlideContent:
    """Audience-facing copy addressed to named slots in a selected layout."""

    slide_id: str
    title: str
    layout_id: str = ""
    slots: dict[str, object] = field(default_factory=dict)
