from app.generation.presenton_template import PresentonTemplateAdapter
from app.generation.themes import template_path_for


def _text_by_name(slide: dict[str, object], name: str) -> list[str]:
    return [
        str(element["runs"][0]["text"])
        for element in slide["elements"]
        if isinstance(element, dict)
        and element.get("type") == "text"
        and element.get("name") == name
        and isinstance(element.get("runs"), list)
        and element["runs"]
    ]


def test_momentum_cover_uses_story_copy_instead_of_template_lorem() -> None:
    adapter = PresentonTemplateAdapter(template_path_for("momentum"))
    slide = adapter.compile_slide(
        "title_with_accent_footer_6891",
        title="Harness AI",
        content="A practical field guide for teams adopting DeepSeek.",
        slide_index=0,
        slide_count=10,
        role="cover",
    )

    titles = " ".join(_text_by_name(slide, "cover_title"))
    subtitles = " ".join(_text_by_name(slide, "cover_subtitle"))
    joined = " ".join(
        str(element["runs"][0]["text"])
        for element in slide["elements"]
        if isinstance(element, dict) and element.get("type") == "text" and element.get("runs")
    )

    assert "Harness AI" in titles
    assert "DeepSeek" in subtitles
    assert "SALES" not in joined
    assert "Lorem" not in joined
    assert "2030" not in joined
    assert not any(
        str(element.get("name", "")) == "side_accent_art"
        for element in slide["elements"]
        if isinstance(element, dict)
    )


def test_momentum_omits_unfilled_photo_slots_and_extra_cards() -> None:
    adapter = PresentonTemplateAdapter(template_path_for("momentum"))
    slide = adapter.compile_slide(
        "title_intro_cards_decorative_frame_6592",
        title="DeepSeek-V3 đa năng",
        content="Nền tảng rẻ và nhanh cho chat.",
        slide_index=2,
        slide_count=10,
        role="content",
        blocks=[
            {"heading": "DeepSeek-V3", "body": "Tối ưu tốc độ và chi phí API."},
            {"heading": "DeepSeek-R1", "body": "Tối ưu suy luận và lập trình."},
        ],
    )

    assert _text_by_name(slide, "card_title") == ["DeepSeek-V3", "DeepSeek-R1"]
    assert not any(
        str(element.get("name", "")) in {"card_image", "corner_accent_image", "visual_card_image"}
        and element.get("type") in {"svg", "image"}
        for element in slide["elements"]
        if isinstance(element, dict)
    )


def test_modern_list_keeps_all_structured_cards() -> None:
    adapter = PresentonTemplateAdapter(template_path_for("modern"))
    slide = adapter.compile_slide(
        "title_description_bullet_points_list_with_icon",
        title="Trust is built through visible actions",
        content="Four coordinated practices make reliability tangible.",
        slide_index=1,
        slide_count=2,
        role="content",
        blocks=[
            {"heading": "Set clear expectations", "body": "State what customers can rely on."},
            {"heading": "Show operational proof", "body": "Make service evidence easy to inspect."},
            {"heading": "Resolve failures openly", "body": "Explain recovery without defensive language."},
            {"heading": "Measure confidence", "body": "Track whether trust improves after each change."},
        ],
    )

    assert _text_by_name(slide, "section_heading") == ["Trust is built through visible actions"]
    assert _text_by_name(slide, "card_title") == [
        "Set clear expectations",
        "Show operational proof",
        "Resolve failures openly",
        "Measure confidence",
    ]


def test_momentum_content_keeps_slide_title_off_the_first_card() -> None:
    adapter = PresentonTemplateAdapter(template_path_for("momentum"))
    slide = adapter.compile_slide(
        "title_intro_cards_decorative_frame_6592",
        title="DeepSeek-V3 đa năng",
        content="Nền tảng rẻ và nhanh cho chat.",
        slide_index=2,
        slide_count=10,
        role="content",
        blocks=[
            {"heading": "DeepSeek-V3", "body": "Tối ưu tốc độ và chi phí API."},
            {"heading": "DeepSeek-R1", "body": "Tối ưu suy luận và lập trình."},
        ],
    )

    assert _text_by_name(slide, "main_title") == ["DeepSeek-V3 đa năng"]
    assert "Nền tảng rẻ và nhanh cho chat." in " ".join(_text_by_name(slide, "intro_description"))
    assert _text_by_name(slide, "card_title")[:2] == ["DeepSeek-V3", "DeepSeek-R1"]
    assert all(not text.strip() for text in _text_by_name(slide, "card_title")[2:])
    markers = _text_by_name(slide, "footer_slide_marker") + _text_by_name(slide, "page_label")
    assert any(marker.lstrip("0") == "3" or marker == "03" for marker in markers)
