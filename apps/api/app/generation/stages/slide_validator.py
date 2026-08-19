from dataclasses import dataclass, field
from typing import Literal

ValidationIssueCode = Literal[
    "ELEMENT_OUT_OF_BOUNDS",
    "ELEMENT_OVERLAP",
    "FONT_TOO_SMALL",
]


@dataclass(frozen=True, slots=True)
class SlideValidationIssue:
    code: ValidationIssueCode
    message: str
    element_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SlideValidationResult:
    issues: list[SlideValidationIssue] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.issues


@dataclass(frozen=True, slots=True)
class _Box:
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def overlaps(self, other: "_Box") -> bool:
        return (
            self.x < other.right
            and self.right > other.x
            and self.y < other.bottom
            and self.bottom > other.y
        )


class RuleBasedSlideValidator:
    """Runs deterministic checks that do not require text rendering or vision."""

    _COLLIDABLE_TYPES = {"text", "text-list", "image", "table", "chart", "svg"}

    def __init__(
        self,
        *,
        canvas_width: float = 1280,
        canvas_height: float = 720,
        minimum_font_size: float = 12,
    ) -> None:
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.minimum_font_size = minimum_font_size

    def validate(self, slide: dict[str, object]) -> SlideValidationResult:
        raw_elements = slide.get("elements")
        elements = (
            [element for element in raw_elements if isinstance(element, dict)]
            if isinstance(raw_elements, list)
            else []
        )
        issues: list[SlideValidationIssue] = []
        collidable: list[tuple[str, _Box]] = []

        for element in elements:
            element_id = str(element.get("id") or "")
            box = self._box(element)
            if box is None:
                continue
            if (
                box.x < 0
                or box.y < 0
                or box.right > self.canvas_width
                or box.bottom > self.canvas_height
            ):
                issues.append(
                    SlideValidationIssue(
                        code="ELEMENT_OUT_OF_BOUNDS",
                        message=f"Element {element_id!r} extends outside the slide canvas.",
                        element_ids=(element_id,),
                    )
                )

            font_size = self._font_size(element)
            if font_size is not None and font_size < self.minimum_font_size:
                issues.append(
                    SlideValidationIssue(
                        code="FONT_TOO_SMALL",
                        message=(
                            f"Element {element_id!r} uses {font_size:g}pt text; "
                            f"minimum is {self.minimum_font_size:g}pt."
                        ),
                        element_ids=(element_id,),
                    )
                )

            if self._is_collidable(element):
                for other_id, other_box in collidable:
                    if box.overlaps(other_box):
                        issues.append(
                            SlideValidationIssue(
                                code="ELEMENT_OVERLAP",
                                message=(
                                    f"Elements {other_id!r} and {element_id!r} overlap."
                                ),
                                element_ids=(other_id, element_id),
                            )
                        )
                collidable.append((element_id, box))

        return SlideValidationResult(issues=issues)

    @staticmethod
    def _box(element: dict[str, object]) -> _Box | None:
        position = element.get("position")
        size = element.get("size")
        if not isinstance(position, dict) or not isinstance(size, dict):
            return None
        values = (
            position.get("x"),
            position.get("y"),
            size.get("width"),
            size.get("height"),
        )
        if not all(isinstance(value, (int, float)) for value in values):
            return None
        x, y, width, height = values
        return _Box(float(x), float(y), float(width), float(height))

    def _font_size(self, element: dict[str, object]) -> float | None:
        if element.get("type") not in {"text", "text-list"}:
            return None
        font = element.get("font")
        if not isinstance(font, dict):
            return None
        size = font.get("size")
        return float(size) if isinstance(size, (int, float)) else None

    def _is_collidable(self, element: dict[str, object]) -> bool:
        return (
            element.get("type") in self._COLLIDABLE_TYPES
            and not bool(element.get("decorative", False))
            and element.get("opacity", 1) != 0
        )
