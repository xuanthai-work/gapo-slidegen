import pytest

from app.generation.layouts import ContentConstraints
from app.generation.models import SlideContent
from app.generation.stages.layout_selector import LayoutCandidateScore
from app.generation.stages.models import StoryOutlineItem
from app.generation.stages.repair_dispatcher import (
    apply_repair_action,
    choose_repair_action,
    scale_constraints,
)
from app.generation.stages.visual_gate import VisualIssue

CATALOG = ContentConstraints(72, 240, 60, 180, 6)
TIGHT_LIST = ContentConstraints(24, 48, 16, 32, 1)


def _issue(code: str, slot: str = "body") -> VisualIssue:
    return VisualIssue(code=code, message=code, slot=slot, expected="x", observed="y")


def _lookup(layout_id: str) -> ContentConstraints:
    if layout_id == "list":
        return TIGHT_LIST
    return CATALOG


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
    next_content, applied = apply_repair_action(
        "tighter_truncate",
        item=item,
        content=content,
        constraints=constraints,
        ranking=[],
        tried=set(),
        issues=[_issue("TEXT_TRUNCATED", "items.1.body")],
        layout_constraints=_lookup,
    )
    assert item.layout_id == "grid"
    assert isinstance(next_content.slots["items"], list)
    assert len(next_content.slots["items"]) == 1
    original_body = str(content.slots["body"])
    repaired_body = str(next_content.slots["body"])
    assert applied.content_max_chars == max(48, int(100 * 0.7))
    assert len(repaired_body) <= applied.content_max_chars
    assert len(repaired_body) <= len(original_body)


def test_second_tighter_truncate_shrinks_further() -> None:
    body = (
        "Sentence one is long enough to wrap across the layout bound. "
        "Sentence two continues the argument with more detail. "
        "Sentence three adds supporting context so truncation has room to cut. "
        "Sentence four keeps going until the copy exceeds the scaled content limit."
    )
    content = SlideContent(
        slide_id="s1",
        title="Title",
        layout_id="grid",
        slots={
            "body": body,
            "items": [
                {"heading": "A", "body": "Alpha"},
                {"heading": "B", "body": "Bravo"},
                {"heading": "C", "body": "Charlie"},
            ],
        },
    )
    item = StoryOutlineItem(id="s1", title="Title", content="x", layout_id="grid")
    constraints = ContentConstraints(72, 200, 40, 80, 3)
    issues = [_issue("TEXT_TRUNCATED", "items.2.body")]
    first, first_constraints = apply_repair_action(
        "tighter_truncate",
        item=item,
        content=content,
        constraints=constraints,
        ranking=[],
        tried=set(),
        issues=issues,
        layout_constraints=_lookup,
    )
    second, second_constraints = apply_repair_action(
        "tighter_truncate",
        item=item,
        content=first,
        constraints=first_constraints,
        ranking=[],
        tried=set(),
        issues=issues,
        layout_constraints=_lookup,
    )
    first_items = first.slots["items"]
    second_items = second.slots["items"]
    assert isinstance(first_items, list)
    assert isinstance(second_items, list)
    assert len(second_items) < len(first_items)
    assert second_constraints.content_max_chars < first_constraints.content_max_chars
    assert len(str(second.slots["body"])) <= len(str(first.slots["body"]))


def test_tighter_truncate_at_floor_switches_layout() -> None:
    content = SlideContent(
        slide_id="s1",
        title="Title",
        layout_id="grid",
        slots={"body": "Short body copy."},
    )
    item = StoryOutlineItem(id="s1", title="Title", content="x", layout_id="grid")
    floor = ContentConstraints(24, 48, 16, 32, 1)
    ranking = [
        LayoutCandidateScore("grid", 10, ("current",)),
        LayoutCandidateScore("list", 8, ("next",)),
    ]
    next_content, applied = apply_repair_action(
        "tighter_truncate",
        item=item,
        content=content,
        constraints=floor,
        ranking=ranking,
        tried={"grid"},
        issues=[_issue("TEXT_TRUNCATED", "body")],
        layout_constraints=_lookup,
    )
    assert item.layout_id == "list"
    assert next_content.layout_id == "list"
    assert applied == TIGHT_LIST


def test_next_ranked_layout_sets_layout_id_and_skips_tried() -> None:
    content = SlideContent(slide_id="s1", title="T", layout_id="grid", slots={"body": "Hello world."})
    item = StoryOutlineItem(id="s1", title="T", content="Hello world.", layout_id="grid")
    ranking = [
        LayoutCandidateScore("grid", 10, ("current",)),
        LayoutCandidateScore("list", 8, ("next",)),
    ]
    next_content, _applied = apply_repair_action(
        "next_ranked_layout",
        item=item,
        content=content,
        constraints=CATALOG,
        ranking=ranking,
        tried={"grid"},
        issues=[_issue("TEXT_UNREADABLE", "title")],
        layout_constraints=_lookup,
    )
    assert item.layout_id == "list"
    assert next_content.layout_id == "list"


def test_next_ranked_layout_constrains_copy_to_new_layout() -> None:
    long_body = (
        "Sentence one is long enough to wrap across the layout bound. "
        "Sentence two continues the argument with more detail. "
        "Sentence three adds supporting context so truncation has room to cut."
    )
    content = SlideContent(
        slide_id="s1",
        title="A reasonably long title that should shrink",
        layout_id="grid",
        slots={"body": long_body},
    )
    item = StoryOutlineItem(id="s1", title="T", content=long_body, layout_id="grid")
    ranking = [
        LayoutCandidateScore("grid", 10, ("current",)),
        LayoutCandidateScore("list", 8, ("next",)),
    ]
    next_content, applied = apply_repair_action(
        "next_ranked_layout",
        item=item,
        content=content,
        constraints=CATALOG,
        ranking=ranking,
        tried={"grid"},
        issues=[_issue("TEXT_UNREADABLE", "title")],
        layout_constraints=_lookup,
    )
    assert next_content.layout_id == "list"
    assert applied == TIGHT_LIST
    assert len(next_content.title) <= TIGHT_LIST.title_max_chars
    assert len(str(next_content.slots["body"])) <= TIGHT_LIST.content_max_chars
    assert len(str(next_content.slots["body"])) < len(long_body)


def test_next_ranked_layout_fails_when_exhausted() -> None:
    from app.generation.stages.orchestrator import SlideValidationFailed

    content = SlideContent(slide_id="s1", title="T", layout_id="grid", slots={"body": "Hi"})
    item = StoryOutlineItem(id="s1", title="T", content="Hi", layout_id="grid")
    with pytest.raises(SlideValidationFailed, match="TEXT_UNREADABLE"):
        apply_repair_action(
            "next_ranked_layout",
            item=item,
            content=content,
            constraints=CATALOG,
            ranking=[LayoutCandidateScore("grid", 10, ("only",))],
            tried={"grid"},
            issues=[_issue("TEXT_UNREADABLE", "title")],
            layout_constraints=_lookup,
        )


def test_scale_constraints_hits_floors() -> None:
    scaled = scale_constraints(ContentConstraints(24, 48, 16, 32, 1), drop_last_item=True)
    assert scaled == ContentConstraints(24, 48, 16, 32, 1)
