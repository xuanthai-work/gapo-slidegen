from app.generation.models import SlideContent
from app.generation.stages.visual_gate import classify_extracted_text


def _content(*, title: str, body: str, items: list[dict[str, str]] | None = None) -> SlideContent:
    slots: dict[str, object] = {"body": body}
    if items is not None:
        slots["items"] = items
    return SlideContent(slide_id="s1", title=title, layout_id="list", slots=slots)


def test_substring_match_is_readable() -> None:
    result = classify_extracted_text(
        extracted="Quarterly Review Teams lost 12 hours formatting slides.",
        unreadable=False,
        content=_content(
            title="Quarterly Review",
            body="Teams lost 12 hours formatting slides.",
        ),
    )
    assert result.readable
    assert result.issues == []


def test_missing_title_emits_text_missing() -> None:
    result = classify_extracted_text(
        extracted="Some other chrome on the canvas",
        unreadable=False,
        content=_content(title="Quarterly Review", body=""),
    )
    assert [issue.code for issue in result.issues] == ["TEXT_MISSING"]
    assert result.issues[0].slot == "title"


def test_partial_body_emits_text_truncated() -> None:
    body = "Teams lost twelve hours every week formatting slides for the board."
    result = classify_extracted_text(
        extracted="Quarterly Review Teams lost twelve hours every week formatting",
        unreadable=False,
        content=_content(title="Quarterly Review", body=body),
    )
    codes = {(issue.slot, issue.code) for issue in result.issues}
    assert ("body", "TEXT_TRUNCATED") in codes


def test_model_unreadable_flag_wins() -> None:
    result = classify_extracted_text(
        extracted="Quarterly Review Teams lost 12 hours formatting slides.",
        unreadable=True,
        content=_content(
            title="Quarterly Review",
            body="Teams lost 12 hours formatting slides.",
        ),
    )
    assert [issue.code for issue in result.issues] == ["TEXT_UNREADABLE"]


def test_empty_extraction_with_copy_is_unreadable() -> None:
    result = classify_extracted_text(
        extracted="",
        unreadable=False,
        content=_content(title="Quarterly Review", body="Body copy here."),
    )
    assert [issue.code for issue in result.issues] == ["TEXT_UNREADABLE"]


def test_vietnamese_diacritics_match_after_nfc() -> None:
    title = "Báo cáo quý"
    result = classify_extracted_text(
        extracted="Báo cáo quý Nội dung slide.",
        unreadable=False,
        content=_content(title=title, body="Nội dung slide."),
    )
    assert result.readable
