from dataclasses import dataclass
from typing import Mapping

from ..layouts import ContentConstraints, NativeLayoutRegistry, build_native_layout_registry
from ..models import SlidePlan
from ..presenton_template import (
    MODERN_STORY_LAYOUTS,
    ROLE_LAYOUT_CANDIDATES,
    PresentonTemplateAdapter,
    _has_media_slot,
    _has_metric_slots,
    _is_card_grid,
    _layout_shape,
    is_auto_excluded_layout,
    is_cover_layout,
)
from .models import StoryOutlineItem

_NATIVE_CONTENT_ORDER = {
    "editorial-cobalt": ("header", "split", "statement", "margin", "band", "frame"),
    "warm-studio": ("margin", "frame", "header", "statement", "split", "band"),
    "midnight-signal": ("split", "band", "margin", "frame", "statement", "header"),
}


@dataclass(frozen=True, slots=True)
class LayoutCandidateScore:
    layout_id: str
    score: float
    reasons: tuple[str, ...]


class PresentonLayoutSelector:
    """Selects a concrete Presenton layout from semantic story metadata."""

    name = "presenton"

    def __init__(self, adapter: PresentonTemplateAdapter | None = None) -> None:
        self.adapter = adapter or PresentonTemplateAdapter()

    def select(
        self,
        item: StoryOutlineItem,
        *,
        index: int,
        theme_id: str,
        assets: Mapping[tuple[int, str], str] | None = None,
        plan: SlidePlan | None = None,
    ) -> str:
        return self.rank(
            item,
            index=index,
            theme_id=theme_id,
            assets=assets,
            plan=plan,
        )[0].layout_id

    def rank(
        self,
        item: StoryOutlineItem,
        *,
        index: int,
        theme_id: str,
        assets: Mapping[tuple[int, str], str] | None = None,
        plan: SlidePlan | None = None,
    ) -> list[LayoutCandidateScore]:
        del theme_id
        resolved_assets = assets or {}
        block_count = plan.item_count if plan else len(item.blocks)
        role = plan.role if plan else item.role
        has_metric_blocks = (
            plan.content_structure == "metrics"
            if plan
            else self._has_metric_data(item)
        )
        has_assets = self._has_slide_assets(resolved_assets, index)
        has_visual_intent = (
            plan.visual_priority == "visual" or plan.image_requirement != "none"
            if plan
            else self._has_visual_fallback(item)
        )
        preferred_archetype = plan.preferred_archetype if plan else None
        requested_layout = MODERN_STORY_LAYOUTS.get(
            preferred_archetype or item.layout or ""
        )
        role_candidates = ROLE_LAYOUT_CANDIDATES.get(role, ()) if role else ()
        has_semantic_guidance = bool(
            plan or item.layout_id or item.layout or item.role or block_count
        )
        cover_layout = self._cover_layout_id()
        content_layouts = self._content_layout_ids(cover_layout)
        fallback_layout = (
            content_layouts[(index - 1) % len(content_layouts)]
            if index > 0 and content_layouts
            else cover_layout
        )
        ranking: list[LayoutCandidateScore] = []

        for layout_id in self.adapter.layout_ids:
            if is_auto_excluded_layout(layout_id) and layout_id != item.layout_id:
                continue
            score = 0.0
            reasons: list[str] = []
            constraints = self.content_constraints(layout_id)

            if item.layout_id == layout_id:
                score += 1_000
                reasons.append("explicit-preference")
            if preferred_archetype == layout_id:
                score += 900
                reasons.append("planned-preference")
            if requested_layout == layout_id:
                score += 800
                reasons.append("legacy-preference")
            if layout_id in role_candidates:
                score += 300 - role_candidates.index(layout_id) * 20
                reasons.append("role-match")

            if layout_id == cover_layout or is_cover_layout(layout_id):
                if index == 0:
                    score += 500
                    reasons.append("first-slide")
                else:
                    score -= 300
                    reasons.append("cover-after-first-slide")
            elif index == 0 and role == "cover":
                score -= 200
                reasons.append("non-cover-first-slide")

            if constraints.max_items > 0:
                if block_count > constraints.max_items:
                    score -= 250 * (block_count - constraints.max_items)
                    reasons.append("item-capacity-exceeded")
                elif block_count > 0:
                    score += 30
                    reasons.append("item-capacity-fit")
            elif block_count > 0:
                score -= 40
                reasons.append("layout-has-no-item-slots")

            if len(item.content) > constraints.content_max_chars:
                overflow = len(item.content) - constraints.content_max_chars
                score -= min(120, overflow / 4)
                reasons.append("content-capacity-exceeded")

            shape = _layout_shape(layout_id)
            if _is_card_grid(layout_id):
                if block_count == 0:
                    score -= 200
                    reasons.append("empty-card-grid")
                else:
                    score += 40
                    reasons.append("parallel-items-fit")
            if shape == "two_column_text" and 0 < block_count <= constraints.max_items:
                score += 30
                reasons.append("list-fit")
            if _has_metric_slots(layout_id):
                if has_metric_blocks:
                    score += 250
                    reasons.append("metric-data-fit")
                else:
                    score -= 100
                    reasons.append("missing-metric-data")
            elif has_metric_blocks and _is_card_grid(layout_id):
                score -= 120
                reasons.append("metric-shape-mismatch")

            if _has_media_slot(layout_id):
                if has_assets:
                    score += 100
                    reasons.append("resolved-asset-fit")
                elif has_visual_intent:
                    score += 80
                    reasons.append("visual-intent-fit")
                else:
                    score -= 120
                    reasons.append("unfilled-media-slot")

            if shape == "index_grid" and role == "agenda":
                score += 200
                reasons.append("agenda-fit")
            if shape == "text_only" and role == "section":
                score += 120
                reasons.append("section-fit")
            if layout_id == fallback_layout:
                score += 20 if has_semantic_guidance else 1_000
                reasons.append(
                    "variety-fallback"
                    if has_semantic_guidance
                    else "unguided-variety-fallback"
                )

            ranking.append(
                LayoutCandidateScore(
                    layout_id=layout_id,
                    score=score,
                    reasons=tuple(reasons),
                )
            )

        if not ranking:
            return [LayoutCandidateScore(cover_layout, 0.0, ("empty-fallback",))]
        return sorted(ranking, key=lambda candidate: candidate.score, reverse=True)

    def content_constraints(self, layout_id: str) -> ContentConstraints:
        return self.adapter.content_constraints(layout_id)

    def _layout_exists(self, layout_id: str) -> bool:
        return layout_id in self.adapter.layout_ids

    def _cover_layout_id(self) -> str:
        for layout_id in self.adapter.layout_ids:
            if is_cover_layout(layout_id):
                return layout_id
        return self.adapter.layout_ids[0]

    def _content_layout_ids(self, cover_layout: str) -> tuple[str, ...]:
        return tuple(
            layout_id
            for layout_id in self.adapter.layout_ids
            if layout_id != cover_layout and not is_auto_excluded_layout(layout_id)
        )

    @classmethod
    def _has_visual_fallback(cls, item: StoryOutlineItem) -> bool:
        return (item.role in {
            "hook",
            "problem",
            "solution",
            "case-study",
            "cta",
            "quote",
            "features",
            "team",
            "process",
            "timeline",
            "comparison",
            "big-stat",
            "summary",
        }) or cls._has_metric_data(item)

    @staticmethod
    def _has_metric_data(item: StoryOutlineItem) -> bool:
        return any(
            (block.get("label") or block.get("value"))
            for block in (item.blocks or [])
            if isinstance(block, dict)
        )

    @staticmethod
    def _has_slide_assets(
        assets: Mapping[tuple[int, str], str],
        slide_index: int,
    ) -> bool:
        return any(index == slide_index for index, _ in assets)


class NativeLayoutSelector:
    """Selects product-owned native layouts and exposes their content budgets."""

    name = "native"

    def __init__(self, registry: NativeLayoutRegistry | None = None) -> None:
        self.registry = registry or build_native_layout_registry()

    def select(
        self,
        item: StoryOutlineItem,
        *,
        index: int,
        theme_id: str,
        assets: Mapping[tuple[int, str], str] | None = None,
        plan: SlidePlan | None = None,
    ) -> str:
        del assets
        role = plan.role if plan else item.role
        block_count = max(
            len(item.blocks),
            plan.item_count if plan is not None else 0,
        )
        if index == 0 or role == "cover":
            return self._cover_layout_id(theme_id)
        if role in {"big-stat", "quote"}:
            return "content-statement"
        if role in {"cta"}:
            return "content-band"
        if block_count >= 2:
            return "content-header"
        body = item.content
        if len(body) > 720:
            return "content-header"
        order = _NATIVE_CONTENT_ORDER.get(theme_id, _NATIVE_CONTENT_ORDER["editorial-cobalt"])
        return f"content-{order[(index - 1) % len(order)]}"

    def rank(
        self,
        item: StoryOutlineItem,
        *,
        index: int,
        theme_id: str,
        assets: Mapping[tuple[int, str], str] | None = None,
        plan: SlidePlan | None = None,
    ) -> list[LayoutCandidateScore]:
        layout_id = self.select(item, index=index, theme_id=theme_id, assets=assets, plan=plan)
        return [LayoutCandidateScore(layout_id, 1.0, ("native-select",))]

    def content_constraints(self, layout_id: str) -> ContentConstraints:
        return self.registry.content_constraints(layout_id)

    @staticmethod
    def _cover_layout_id(theme_id: str) -> str:
        if theme_id == "warm-studio":
            return "cover-warm"
        if theme_id == "midnight-signal":
            return "cover-midnight"
        return "cover-editorial"


class ThemeDispatchLayoutSelector:
    """Chooses Presenton layouts from the template named in theme_id."""

    name = "dispatch"

    def __init__(
        self,
        *,
        presenton: PresentonLayoutSelector | None = None,
        native: NativeLayoutSelector | None = None,
    ) -> None:
        self._fixed = presenton is not None
        self._presenton = presenton or PresentonLayoutSelector()
        self._native = native or NativeLayoutSelector()
        self._by_template: dict[str, PresentonLayoutSelector] = {}
        self._last: PresentonLayoutSelector | None = None

    def select(
        self,
        item: StoryOutlineItem,
        *,
        index: int,
        theme_id: str,
        assets: Mapping[tuple[int, str], str] | None = None,
        plan: SlidePlan | None = None,
    ) -> str:
        return self._delegate(theme_id).select(
            item,
            index=index,
            theme_id=theme_id,
            assets=assets,
            plan=plan,
        )

    def rank(
        self,
        item: StoryOutlineItem,
        *,
        index: int,
        theme_id: str,
        assets: Mapping[tuple[int, str], str] | None = None,
        plan: SlidePlan | None = None,
    ) -> list[LayoutCandidateScore]:
        return self._delegate(theme_id).rank(
            item,
            index=index,
            theme_id=theme_id,
            assets=assets,
            plan=plan,
        )

    def content_constraints(self, layout_id: str) -> ContentConstraints:
        if layout_id in self._native.registry.layout_ids:
            return self._native.content_constraints(layout_id)
        candidates = [self._last, self._presenton, *self._by_template.values()]
        for selector in candidates:
            if selector is not None and layout_id in selector.adapter.layout_ids:
                return selector.content_constraints(layout_id)
        return self._presenton.content_constraints(layout_id)

    def _delegate(self, theme_id: str) -> PresentonLayoutSelector:
        if self._fixed:
            self._last = self._presenton
            return self._presenton
        from ..themes import parse_theme_ref, template_path_for

        template_id, _scheme = parse_theme_ref(theme_id)
        selector = self._by_template.get(template_id)
        if selector is None:
            selector = (
                self._presenton
                if template_id == "modern"
                else PresentonLayoutSelector(
                    PresentonTemplateAdapter(template_path_for(template_id))
                )
            )
            self._by_template[template_id] = selector
        self._last = selector
        return selector
