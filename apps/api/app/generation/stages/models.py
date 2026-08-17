from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

AssetSlotKind = Literal["image", "chart", "table", "svg"]

SlideRole = Literal[
    "cover",
    "agenda",
    "section",
    "hook",
    "problem",
    "solution",
    "big-stat",
    "comparison",
    "process",
    "timeline",
    "features",
    "case-study",
    "quote",
    "team",
    "cta",
    "summary",
    "content",
]


@dataclass(frozen=True, slots=True)
class ContentUnderstandingResult:
    """Lightweight semantic summary of a normalized source document."""

    intent: str = ""
    audience: str = ""
    tone: str = ""
    key_takeaways: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class StoryOutlineItem:
    """Typed view of one slide in the story plan."""

    id: str
    title: str
    content: str
    layout: str | None = None
    role: SlideRole | None = None
    layout_id: str | None = None
    content_budget: dict[str, int] = field(default_factory=dict)
    blocks: list[dict[str, str]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, item: dict[str, object]) -> StoryOutlineItem:
        blocks = item.get("blocks")
        content_budget = item.get("content_budget")
        return cls(
            id=str(item.get("id") or ""),
            title=str(item.get("title") or ""),
            content=str(item.get("content") or ""),
            layout=str(item.get("layout")) if item.get("layout") is not None else None,
            role=str(item.get("role")) if item.get("role") is not None else None,  # type: ignore[arg-type]
            layout_id=str(item.get("layout_id")) if item.get("layout_id") is not None else None,
            content_budget={
                str(k): int(v)
                for k, v in (content_budget.items() if isinstance(content_budget, dict) else {})
                if isinstance(v, int) or (isinstance(v, (int, float)) and float(v).is_integer())
            }
            if isinstance(content_budget, dict)
            else {},
            blocks=[dict(block) for block in blocks if isinstance(block, dict)]
            if isinstance(blocks, list)
            else [],
        )


@dataclass(frozen=True, slots=True)
class StoryOutline:
    """Ordered, validated story plan produced by the StoryPlanner stage."""

    items: list[StoryOutlineItem] = field(default_factory=list)

    @classmethod
    def from_dicts(cls, items: list[dict[str, object]]) -> StoryOutline:
        return cls(items=[StoryOutlineItem.from_dict(item) for item in items])


@dataclass(frozen=True, slots=True)
class AssetSlot:
    """A concrete slot inside a slide that may accept a generated asset."""

    slide_index: int
    name: str
    kind: AssetSlotKind


@dataclass(frozen=True, slots=True)
class AssetRequest:
    """Request to fill one asset slot."""

    slot: AssetSlot
    prompt: str | None = None
    data: dict[str, object] | None = None
    fallback_enabled: bool = True
    visual_intent: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class AssetPlan:
    """Collection of asset requests produced by the AssetPlanner stage."""

    requests: list[AssetRequest] = field(default_factory=list)
    owner_id: UUID | None = None
    language: str = "en"


@dataclass(frozen=True, slots=True)
class GeneratedAsset:
    """Result of generating one requested asset."""

    slot: AssetSlot
    asset_id: str | None = None
    warning: str | None = None
