from typing import Protocol

from ..models import DeckPlan, SlidePlan
from ..provider import GenerationRequest, ProviderError
from .models import StoryOutline
from .protocols import DeckPlanner


class DeckPlanningProvider(Protocol):
    def plan_deck(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
    ) -> DeckPlan:
        ...


class ProviderDeckPlanner:
    """Uses provider planning and falls back when the provider response is unusable."""

    name = "provider-with-outline-fallback"

    def __init__(
        self,
        provider: DeckPlanningProvider,
        *,
        fallback: DeckPlanner,
    ) -> None:
        self.provider = provider
        self.fallback = fallback

    def plan(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
    ) -> DeckPlan:
        try:
            return self.provider.plan_deck(request, outline)
        except ProviderError:
            return self.fallback.plan(request, outline)


class OutlineDeckPlanner:
    """Builds a deck-level narrative contract from a reviewed legacy outline."""

    name = "outline"

    def plan(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
    ) -> DeckPlan:
        slides = [
            SlidePlan(
                id=item.id,
                index=index,
                role=item.role or ("cover" if index == 0 else "content"),
                communication_goal=item.title,
                content_structure="unspecified",
                preferred_archetype=item.layout_id or item.layout,
            )
            for index, item in enumerate(outline.items)
        ]
        narrative_arc = " → ".join(
            slide.role
            for slide in slides
            if slide.role
        )
        return DeckPlan(
            title=request.title,
            audience="",
            objective=f"Present {request.title}",
            narrative_arc=narrative_arc,
            language=request.language,
            slides=slides,
        )
