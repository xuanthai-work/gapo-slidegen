from dataclasses import replace
from typing import Protocol

from ..models import DeckPlan, SlidePlan
from ..provider import ProviderError
from .models import StoryOutlineItem
from .protocols import SlidePlanner


class SlidePlanningProvider(Protocol):
    def plan_slide(
        self,
        *,
        deck_plan: DeckPlan,
        current_slide: SlidePlan,
        source_item: StoryOutlineItem,
        previous_slide: SlidePlan | None,
        next_slide: SlidePlan | None,
    ) -> SlidePlan:
        ...


class ProviderSlidePlanner:
    """Uses provider slide planning with deterministic semantic fallback."""

    name = "provider-with-outline-fallback"

    def __init__(
        self,
        provider: SlidePlanningProvider,
        *,
        fallback: SlidePlanner,
    ) -> None:
        self.provider = provider
        self.fallback = fallback

    def plan(
        self,
        *,
        deck_plan: DeckPlan,
        current_slide: SlidePlan,
        source_item: StoryOutlineItem,
        previous_slide: SlidePlan | None,
        next_slide: SlidePlan | None,
    ) -> SlidePlan:
        try:
            return self.provider.plan_slide(
                deck_plan=deck_plan,
                current_slide=current_slide,
                source_item=source_item,
                previous_slide=previous_slide,
                next_slide=next_slide,
            )
        except ProviderError:
            return self.fallback.plan(
                deck_plan=deck_plan,
                current_slide=current_slide,
                source_item=source_item,
                previous_slide=previous_slide,
                next_slide=next_slide,
            )


class OutlineSlidePlanner:
    """Refines one deck-outline entry into a semantic slide plan."""

    name = "outline"

    def plan(
        self,
        *,
        deck_plan: DeckPlan,
        current_slide: SlidePlan,
        source_item: StoryOutlineItem,
        previous_slide: SlidePlan | None,
        next_slide: SlidePlan | None,
    ) -> SlidePlan:
        del deck_plan, previous_slide, next_slide
        structure, relationship = self._content_shape(
            source_item,
            current_slide.role,
        )
        visual_priority = self._visual_priority(source_item, structure)
        return replace(
            current_slide,
            content_structure=structure,
            item_count=len(source_item.blocks),
            relationship=relationship,
            visual_priority=visual_priority,
            image_requirement=(
                "optional"
                if source_item.layout == "split-image"
                or source_item.layout_id == "title_description_image"
                else "none"
            ),
            density=self._density(source_item),
        )

    @staticmethod
    def _content_shape(
        item: StoryOutlineItem,
        role: str,
    ) -> tuple[str, str]:
        if role == "comparison":
            return "comparison", "contrast"
        if role in {"process", "timeline"}:
            return role, "sequence"
        if role == "big-stat" or any(
            block.get("label") or block.get("value")
            for block in item.blocks
        ):
            return "metrics", "parallel"
        if role == "quote":
            return "statement", "none"
        if role == "cover":
            return "headline", "none"
        if item.blocks:
            return "list", "parallel"
        return "title-body", "none"

    @staticmethod
    def _visual_priority(item: StoryOutlineItem, structure: str) -> str:
        if item.layout == "split-image" or item.layout_id == "title_description_image":
            return "visual"
        if structure in {"comparison", "metrics", "list", "process", "timeline"}:
            return "balanced"
        return "content"

    @staticmethod
    def _density(item: StoryOutlineItem) -> str:
        character_count = len(item.title) + len(item.content) + sum(
            len(str(value))
            for block in item.blocks
            for value in block.values()
        )
        if character_count > 600 or len(item.blocks) > 4:
            return "high"
        if character_count > 220 or len(item.blocks) > 2:
            return "medium"
        return "low"
