from copy import deepcopy

from app.generation.stages.slide_repairer import DeterministicSlideRepairer
from app.generation.stages.slide_validator import RuleBasedSlideValidator


def _element(
    element_id: str,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    font_size: float = 18,
) -> dict[str, object]:
    return {
        "id": element_id,
        "type": "text",
        "position": {"x": x, "y": y},
        "size": {"width": width, "height": height},
        "font": {"size": font_size},
    }


def test_repairer_clamps_bounds_and_minimum_font_without_mutating_input() -> None:
    validator = RuleBasedSlideValidator(minimum_font_size=12)
    repairer = DeterministicSlideRepairer(minimum_font_size=12)
    slide = {
        "id": "slide-1",
        "elements": [
            _element(
                "outside",
                x=1250,
                y=-20,
                width=100,
                height=80,
                font_size=9,
            )
        ],
    }
    original = deepcopy(slide)

    repaired = repairer.repair(slide, validator.validate(slide))

    assert validator.validate(repaired).valid
    assert slide == original
    assert repaired["elements"][0]["position"] == {"x": 1180.0, "y": 0.0}
    assert repaired["elements"][0]["font"]["size"] == 12


def test_repairer_moves_later_overlapping_element_to_nearest_free_position() -> None:
    validator = RuleBasedSlideValidator()
    repairer = DeterministicSlideRepairer(grid_size=10)
    slide = {
        "id": "slide-1",
        "elements": [
            _element("first", x=100, y=100, width=200, height=80),
            _element("second", x=250, y=130, width=200, height=80),
        ],
    }

    repaired = repairer.repair(slide, validator.validate(slide))

    assert validator.validate(repaired).valid
    assert repaired["elements"][0]["position"] == {"x": 100, "y": 100}
    assert repaired["elements"][1]["position"] == {"x": 250.0, "y": 180.0}


def test_repairer_leaves_unrepairable_overlap_for_validator_to_report() -> None:
    validator = RuleBasedSlideValidator(canvas_width=100, canvas_height=100)
    repairer = DeterministicSlideRepairer(
        canvas_width=100,
        canvas_height=100,
        grid_size=10,
    )
    slide = {
        "id": "slide-1",
        "elements": [
            _element("first", x=0, y=0, width=100, height=100),
            _element("second", x=0, y=0, width=100, height=100),
        ],
    }

    repaired = repairer.repair(slide, validator.validate(slide))

    assert [issue.code for issue in validator.validate(repaired).issues] == [
        "ELEMENT_OVERLAP"
    ]


def test_repairer_relocates_each_overlapping_element_at_most_once() -> None:
    class CountingRepairer(DeterministicSlideRepairer):
        def __init__(self) -> None:
            super().__init__(grid_size=10)
            self.moved_ids: list[str] = []

        def _move_to_free_position(self, element, elements) -> None:
            self.moved_ids.append(str(element["id"]))
            super()._move_to_free_position(element, elements)

    validator = RuleBasedSlideValidator()
    repairer = CountingRepairer()
    slide = {
        "id": "slide-1",
        "elements": [
            _element("first", x=100, y=100, width=200, height=80),
            _element("second", x=120, y=110, width=200, height=80),
            _element("third", x=140, y=120, width=200, height=80),
        ],
    }

    repairer.repair(slide, validator.validate(slide))

    assert repairer.moved_ids.count("third") == 1
