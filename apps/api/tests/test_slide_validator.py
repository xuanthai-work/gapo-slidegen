from app.generation.stages.slide_validator import RuleBasedSlideValidator


def _element(
    element_id: str,
    *,
    element_type: str = "text",
    x: float = 10,
    y: float = 10,
    width: float = 100,
    height: float = 40,
    font_size: float = 18,
    decorative: bool = False,
) -> dict[str, object]:
    element: dict[str, object] = {
        "id": element_id,
        "type": element_type,
        "position": {"x": x, "y": y},
        "size": {"width": width, "height": height},
        "opacity": 1,
        "decorative": decorative,
    }
    if element_type in {"text", "text-list"}:
        element["font"] = {"size": font_size}
    return element


def test_slide_validator_accepts_non_overlapping_elements_inside_canvas() -> None:
    validator = RuleBasedSlideValidator()
    slide = {
        "id": "slide-1",
        "elements": [
            _element("title"),
            _element("image", element_type="image", x=300, y=100, width=400, height=300),
        ],
    }

    result = validator.validate(slide)

    assert result.valid
    assert result.issues == []


def test_slide_validator_reports_out_of_bounds_elements() -> None:
    validator = RuleBasedSlideValidator()
    slide = {
        "id": "slide-1",
        "elements": [
            _element("outside", x=1200, y=680, width=100, height=60),
        ],
    }

    result = validator.validate(slide)

    assert [issue.code for issue in result.issues] == ["ELEMENT_OUT_OF_BOUNDS"]
    assert result.issues[0].element_ids == ("outside",)


def test_slide_validator_reports_content_overlap() -> None:
    validator = RuleBasedSlideValidator()
    slide = {
        "id": "slide-1",
        "elements": [
            _element("first", x=100, y=100, width=200, height=80),
            _element("second", x=250, y=130, width=200, height=80),
        ],
    }

    result = validator.validate(slide)

    assert [issue.code for issue in result.issues] == ["ELEMENT_OVERLAP"]
    assert result.issues[0].element_ids == ("first", "second")


def test_slide_validator_ignores_overlap_with_decorative_elements() -> None:
    validator = RuleBasedSlideValidator()
    slide = {
        "id": "slide-1",
        "elements": [
            _element(
                "background",
                element_type="shape",
                x=0,
                y=0,
                width=1280,
                height=720,
                decorative=True,
            ),
            _element("title", x=100, y=100, width=500, height=100),
        ],
    }

    assert validator.validate(slide).valid


def test_slide_validator_reports_text_below_minimum_font_size() -> None:
    validator = RuleBasedSlideValidator(minimum_font_size=12)
    slide = {
        "id": "slide-1",
        "elements": [_element("caption", font_size=10)],
    }

    result = validator.validate(slide)

    assert [issue.code for issue in result.issues] == ["FONT_TOO_SMALL"]
    assert result.issues[0].element_ids == ("caption",)
