from typing import Protocol

from ..layouts import ContentConstraints
from ..models import DeckPlan, SlideContent, SlidePlan
from ..provider import ProviderError, ProviderResponseError
from .models import StoryOutline, StoryOutlineItem


class BatchContentWritingProvider(Protocol):
    def write_content_batch(
        self,
        *,
        outline: StoryOutline,
        deck_plan: DeckPlan,
        constraints: dict[str, ContentConstraints],
        language: str,
    ) -> dict[str, SlideContent]:
        ...


def _truncate(text: str, limit: int) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    suffix = "..." if limit >= 3 else ""
    available = limit - len(suffix)
    truncated = cleaned[:available]
    last_space = truncated.rfind(" ")
    if last_space > available * 0.7:
        truncated = truncated[:last_space]
    return truncated.rstrip(" .,;:-") + suffix


class OutlineContentWriter:
    """Adapts reviewed outline copy into layout-addressable named slots."""

    name = "outline"

    def write_batch(
        self,
        *,
        outline: StoryOutline,
        deck_plan: DeckPlan,
        constraints: dict[str, ContentConstraints],
        language: str,
    ) -> dict[str, SlideContent]:
        del language
        plans = {plan.id: plan for plan in deck_plan.slides}
        return {
            item.id: self.write(
                item,
                layout_id=item.layout_id or "",
                constraints=constraints[item.id],
                plan=plans.get(item.id),
            )
            for item in outline.items
        }

    def write(
        self,
        item: StoryOutlineItem,
        *,
        layout_id: str,
        constraints: ContentConstraints,
        plan: SlidePlan | None = None,
    ) -> SlideContent:
        del plan
        limits = constraints.as_budget()
        for field, requested_limit in item.content_budget.items():
            if field in limits:
                limits[field] = min(limits[field], requested_limit)

        items = [
            {
                "heading": _truncate(
                    str(block.get("heading") or ""),
                    limits["block_heading_max_chars"],
                ),
                "body": _truncate(
                    str(block.get("body") or ""),
                    limits["block_body_max_chars"],
                ),
                "label": _truncate(
                    str(block.get("label") or ""),
                    limits["block_heading_max_chars"],
                ),
                "value": _truncate(
                    str(block.get("value") or ""),
                    limits["block_body_max_chars"],
                ),
            }
            for block in item.blocks[: constraints.max_items]
        ]
        return SlideContent(
            slide_id=item.id,
            layout_id=layout_id,
            title=_truncate(item.title, limits["title_max_chars"]),
            slots={
                "body": _truncate(item.content, limits["content_max_chars"]),
                "items": items,
            },
        )


class ProviderContentWriter:
    """Uses one provider call per deck and constrains its copy deterministically."""

    name = "provider-with-outline-fallback"

    def __init__(
        self,
        provider: BatchContentWritingProvider,
        *,
        fallback: OutlineContentWriter,
    ) -> None:
        self.provider = provider
        self.fallback = fallback

    def write_batch(
        self,
        *,
        outline: StoryOutline,
        deck_plan: DeckPlan,
        constraints: dict[str, ContentConstraints],
        language: str,
    ) -> dict[str, SlideContent]:
        try:
            generated = self.provider.write_content_batch(
                outline=outline,
                deck_plan=deck_plan,
                constraints=constraints,
                language=language,
            )
            expected_ids = [item.id for item in outline.items]
            if list(generated) != expected_ids:
                raise ProviderResponseError(
                    "Content writer changed slide identities or order."
                )
            return self._constrain_generated(
                generated=generated,
                outline=outline,
                deck_plan=deck_plan,
                constraints=constraints,
            )
        except ProviderError:
            return self.fallback.write_batch(
                outline=outline,
                deck_plan=deck_plan,
                constraints=constraints,
                language=language,
            )

    def _constrain_generated(
        self,
        *,
        generated: dict[str, SlideContent],
        outline: StoryOutline,
        deck_plan: DeckPlan,
        constraints: dict[str, ContentConstraints],
    ) -> dict[str, SlideContent]:
        source_by_id = {item.id: item for item in outline.items}
        plans = {plan.id: plan for plan in deck_plan.slides}
        constrained: dict[str, SlideContent] = {}
        for slide_id, content in generated.items():
            source = source_by_id[slide_id]
            raw_items = content.slots.get("items")
            blocks = (
                [dict(item) for item in raw_items if isinstance(item, dict)]
                if isinstance(raw_items, list)
                else []
            )
            generated_item = StoryOutlineItem(
                id=slide_id,
                title=content.title,
                content=str(content.slots.get("body") or ""),
                layout=source.layout,
                role=source.role,
                layout_id=source.layout_id,
                content_budget=source.content_budget,
                blocks=blocks,
            )
            constrained[slide_id] = self.fallback.write(
                generated_item,
                layout_id=source.layout_id or "",
                constraints=constraints[slide_id],
                plan=plans.get(slide_id),
            )
        return constrained
