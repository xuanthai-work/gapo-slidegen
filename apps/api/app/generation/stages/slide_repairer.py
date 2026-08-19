from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from .slide_validator import SlideValidationResult


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


class DeterministicSlideRepairer:
    """Applies bounded geometry and typography fixes without using an LLM."""

    name = "deterministic"
    _COLLIDABLE_TYPES = {"text", "text-list", "image", "table", "chart", "svg"}

    def __init__(
        self,
        *,
        canvas_width: float = 1280,
        canvas_height: float = 720,
        minimum_font_size: float = 12,
        grid_size: float = 10,
    ) -> None:
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.minimum_font_size = minimum_font_size
        self.grid_size = max(1, grid_size)

    def repair(
        self,
        slide: dict[str, object],
        validation: SlideValidationResult,
    ) -> dict[str, object]:
        repaired = deepcopy(slide)
        raw_elements = repaired.get("elements")
        if not isinstance(raw_elements, list):
            return repaired
        elements = [item for item in raw_elements if isinstance(item, dict)]
        by_id = {str(item.get("id") or ""): item for item in elements}

        for issue in validation.issues:
            if not issue.element_ids:
                continue
            element = by_id.get(issue.element_ids[-1])
            if element is None:
                continue
            if issue.code == "ELEMENT_OUT_OF_BOUNDS":
                self._clamp_to_canvas(element)
            elif issue.code == "FONT_TOO_SMALL":
                self._raise_font_size(element)

        relocated_ids: set[str] = set()
        for issue in validation.issues:
            if issue.code != "ELEMENT_OVERLAP" or not issue.element_ids:
                continue
            element_id = issue.element_ids[-1]
            if element_id in relocated_ids:
                continue
            relocated_ids.add(element_id)
            element = by_id.get(element_id)
            if element is not None:
                self._move_to_free_position(element, elements)

        return repaired

    def _clamp_to_canvas(self, element: dict[str, object]) -> None:
        box = self._box(element)
        if box is None:
            return
        width = min(max(0.0, box.width), self.canvas_width)
        height = min(max(0.0, box.height), self.canvas_height)
        element["size"] = {"width": width, "height": height}
        element["position"] = {
            "x": min(max(0.0, box.x), self.canvas_width - width),
            "y": min(max(0.0, box.y), self.canvas_height - height),
        }

    def _raise_font_size(self, element: dict[str, object]) -> None:
        font = element.get("font")
        if not isinstance(font, dict):
            return
        font["size"] = self.minimum_font_size

    def _move_to_free_position(
        self,
        element: dict[str, object],
        elements: list[dict[str, object]],
    ) -> None:
        box = self._box(element)
        if box is None:
            return
        occupied = [
            other_box
            for other in elements
            if other is not element and self._is_collidable(other)
            if (other_box := self._box(other)) is not None
        ]
        candidates = self._candidate_positions(box, occupied)
        for x, y in candidates:
            candidate = _Box(x=x, y=y, width=box.width, height=box.height)
            if self._inside_canvas(candidate) and not any(
                candidate.overlaps(other) for other in occupied
            ):
                element["position"] = {"x": x, "y": y}
                return

    def _candidate_positions(
        self,
        box: _Box,
        occupied: list[_Box],
    ) -> list[tuple[float, float]]:
        candidates: list[tuple[float, float]] = []
        for other in occupied:
            candidates.extend(
                [
                    (box.x, other.bottom),
                    (other.right, box.y),
                    (box.x, other.y - box.height),
                    (other.x - box.width, box.y),
                ]
            )

        max_x = max(0.0, self.canvas_width - box.width)
        max_y = max(0.0, self.canvas_height - box.height)
        y = 0.0
        while y <= max_y:
            x = 0.0
            while x <= max_x:
                candidates.append((x, y))
                x += self.grid_size
            y += self.grid_size

        unique = list(dict.fromkeys(candidates))
        return sorted(
            unique,
            key=lambda point: (
                abs(point[0] - box.x) + abs(point[1] - box.y),
                point[0] != box.x,
                point[1],
                point[0],
            ),
        )

    def _inside_canvas(self, box: _Box) -> bool:
        return (
            box.x >= 0
            and box.y >= 0
            and box.right <= self.canvas_width
            and box.bottom <= self.canvas_height
        )

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

    def _is_collidable(self, element: dict[str, object]) -> bool:
        return (
            element.get("type") in self._COLLIDABLE_TYPES
            and not bool(element.get("decorative", False))
            and element.get("opacity", 1) != 0
        )
