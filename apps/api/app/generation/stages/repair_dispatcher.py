from __future__ import annotations

from collections.abc import Callable
from typing import Literal, NoReturn

from ..content_schema import constrain_slide_content
from ..layouts import ContentConstraints
from ..models import SlideContent
from .layout_selector import LayoutCandidateScore
from .models import StoryOutlineItem
from .orchestrator import SlideValidationFailed
from .visual_gate import VisualIssue

RepairAction = Literal["tighter_truncate", "next_ranked_layout", "fail"]
VISUAL_GATE_MAX_REPAIRS = 2


def choose_repair_action(issues: list[VisualIssue]) -> RepairAction:
    if any(issue.code == "TEXT_UNREADABLE" for issue in issues):
        return "next_ranked_layout"
    if any(issue.code == "TEXT_MISSING" and issue.slot == "title" for issue in issues):
        return "next_ranked_layout"
    if any(
        issue.code in {"TEXT_MISSING", "TEXT_TRUNCATED"}
        and (issue.slot or "").startswith(("body", "items"))
        for issue in issues
    ):
        return "tighter_truncate"
    return "fail"


def scale_constraints(constraints: ContentConstraints, *, drop_last_item: bool) -> ContentConstraints:
    max_items = constraints.max_items
    if drop_last_item and max_items > 1:
        max_items -= 1
    return ContentConstraints(
        title_max_chars=max(24, int(constraints.title_max_chars * 0.7)),
        content_max_chars=max(48, int(constraints.content_max_chars * 0.7)),
        block_heading_max_chars=max(16, int(constraints.block_heading_max_chars * 0.7)),
        block_body_max_chars=max(32, int(constraints.block_body_max_chars * 0.7)),
        max_items=max(1, max_items),
    )


def apply_repair_action(
    action: RepairAction,
    *,
    item: StoryOutlineItem,
    content: SlideContent,
    constraints: ContentConstraints,
    ranking: list[LayoutCandidateScore],
    tried: set[str],
    issues: list[VisualIssue],
    layout_constraints: Callable[[str], ContentConstraints],
) -> tuple[SlideContent, ContentConstraints]:
    if action == "fail":
        _fail(item.id, issues)
    if action == "tighter_truncate":
        drop_last = any((issue.slot or "").startswith("items") for issue in issues)
        next_constraints = scale_constraints(constraints, drop_last_item=drop_last)
        if next_constraints != constraints:
            return constrain_slide_content(content, next_constraints), next_constraints
    return _apply_next_ranked_layout(
        item=item,
        content=content,
        ranking=ranking,
        tried=tried,
        issues=issues,
        layout_constraints=layout_constraints,
    )


def _apply_next_ranked_layout(
    *,
    item: StoryOutlineItem,
    content: SlideContent,
    ranking: list[LayoutCandidateScore],
    tried: set[str],
    issues: list[VisualIssue],
    layout_constraints: Callable[[str], ContentConstraints],
) -> tuple[SlideContent, ContentConstraints]:
    next_id = next(
        (
            candidate.layout_id
            for candidate in ranking
            if candidate.layout_id not in tried and candidate.layout_id != item.layout_id
        ),
        None,
    )
    if next_id is None:
        _fail(item.id, issues)
    object.__setattr__(item, "layout_id", next_id)
    next_constraints = layout_constraints(next_id)
    updated = SlideContent(
        slide_id=content.slide_id,
        title=content.title,
        layout_id=next_id,
        slots=content.slots,
    )
    return constrain_slide_content(updated, next_constraints), next_constraints


def _fail(slide_id: str, issues: list[VisualIssue]) -> NoReturn:
    codes = ", ".join(issue.code for issue in issues) or "fail"
    raise SlideValidationFailed(
        f"Slide {slide_id!r} failed visual validation: {codes}"
    )
