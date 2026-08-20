import pytest

from app.generation.layouts import ContentConstraints
from app.generation.models import SlideContent
from app.generation.stages.layout_selector import LayoutCandidateScore
from app.generation.stages.models import StoryOutlineItem
from app.generation.stages.repair_dispatcher import (
    apply_repair_action,
    choose_repair_action,
)
from app.generation.stages.visual_gate import VisualIssue


def _issue(code: str, slot: str = "body") -> VisualIssue:
    return VisualIssue(code=code, message=code, slot=slot, expected="x", observed="y")


def test_unreadable_chooses_next_layout() -> None:
    assert choose_repair_action([_issue("TEXT_UNREADABLE", "title")]) == "next_ranked_layout"


def test_missing_title_chooses_next_layout() -> None:
    assert choose_repair_action([_issue("TEXT_MISSING", "title")]) == "next_ranked_layout"


def test_truncated_body_chooses_tighter_truncate() -> None:
    assert choose_repair_action([_issue("TEXT_TRUNCATED", "body")]) == "tighter_truncate"


def test_empty_issues_choose_fail() -> None:
    assert choose_repair_action([]) == "fail"


def test_priority_unreadable_beats_truncated() -> None:
    assert (
        choose_repair_action(
            [
                _issue("TEXT_TRUNCATED", "body"),
                _issue("TEXT_UNREADABLE", "title"),
            ]
        )
        == "next_ranked_layout"
    )


def test_tighter_truncate_shrinks_body_and_drops_last_item() -> None:
    content = SlideContent(
        slide_id="s1",
        title="Title text that is long enough",
        layout_id="grid",
        slots={
            "body": "Sentence one. Sentence two. Sentence three. Sentence four.",
            "items": [
                {"heading": "A", "body": "Alpha point with a full sentence."},
                {"heading": "B", "body": "Bravo point with a full sentence."},
            ],
        },
    )
    item = StoryOutlineItem(id="s1", title="Title", content="x", layout_id="grid")
    constraints = ContentConstraints(72, 100, 40, 80, 2)
    next_content = apply_repair_action(
        "tighter_truncate",
        item=item,
        content=content,
        constraints=constraints,
        ranking=[],
        tried=set(),
        issues=[_issue("TEXT_TRUNCATED", "items.1.body")],
    )
    assert item.layout_id == "grid"
    assert isinstance(next_content.slots["items"], list)
    assert len(next_content.slots["items"]) == 1
    original_body = str(content.slots["body"])
    repaired_body = str(next_content.slots["body"])
    assert len(repaired_body) <= max(48, int(100 * 0.7))
    assert len(repaired_body) <= len(original_body)


def test_next_ranked_layout_sets_layout_id_and_skips_tried() -> None:
    content = SlideContent(slide_id="s1", title="T", layout_id="grid", slots={"body": "Hello world."})
    item = StoryOutlineItem(id="s1", title="T", content="Hello world.", layout_id="grid")
    ranking = [
        LayoutCandidateScore("grid", 10, ("current",)),
        LayoutCandidateScore("list", 8, ("next",)),
    ]
    next_content = apply_repair_action(
        "next_ranked_layout",
        item=item,
        content=content,
        constraints=ContentConstraints(72, 240, 60, 180, 6),
        ranking=ranking,
        tried={"grid"},
        issues=[_issue("TEXT_UNREADABLE", "title")],
    )
    assert item.layout_id == "list"
    assert next_content.layout_id == "list"


def test_next_ranked_layout_fails_when_exhausted() -> None:
    from app.generation.stages.orchestrator import SlideValidationFailed

    content = SlideContent(slide_id="s1", title="T", layout_id="grid", slots={"body": "Hi"})
    item = StoryOutlineItem(id="s1", title="T", content="Hi", layout_id="grid")
    with pytest.raises(SlideValidationFailed, match="TEXT_UNREADABLE"):
        apply_repair_action(
            "next_ranked_layout",
            item=item,
            content=content,
            constraints=ContentConstraints(72, 240, 60, 180, 6),
            ranking=[LayoutCandidateScore("grid", 10, ("only",))],
            tried={"grid"},
            issues=[_issue("TEXT_UNREADABLE", "title")],
        )
