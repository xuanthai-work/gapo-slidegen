import pytest

from app.schemas.presentation import Outline
from app.services.outlines import OutlineQualityError, validate_outline


def outline_with(titles: list[str]) -> Outline:
    return Outline.model_validate(
        {
            "title": "Deck",
            "slides": [
                {
                    "id": f"slide-{index}",
                    "title": title,
                    "objective": "Explain the topic",
                    "key_points": ["Grounded point"],
                }
                for index, title in enumerate(titles, start=1)
            ],
        }
    )


def test_outline_requires_expected_slide_count() -> None:
    with pytest.raises(OutlineQualityError, match="exactly 5"):
        validate_outline(outline_with(["One", "Two"]), 5)


def test_outline_rejects_duplicate_titles() -> None:
    with pytest.raises(OutlineQualityError, match="titles must be unique"):
        validate_outline(outline_with(["Same", "same"]), 2)
