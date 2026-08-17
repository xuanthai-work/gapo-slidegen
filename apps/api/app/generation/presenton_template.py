from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4


STAGE_WIDTH = 1280.0
STAGE_HEIGHT = 720.0
MODERN_TEMPLATE_PATH = Path(__file__).with_name("templates") / "modern.json"
MODERN_CONTENT_LAYOUT_IDS = (
    "title_description_bullet_points_grid_with_icon",
    "title_description_bullet_points_list_with_icon",
    "title_description_image",
    "title_list_of_cards_with_alternating_image",
    "title_list_of_cards_with_image",
    "title_image_description_list_with_highlighted_text_heading_description",
)
MODERN_STORY_LAYOUTS = {
    "feature-grid": "title_description_bullet_points_grid_with_icon",
    "feature-list": "title_description_bullet_points_list_with_icon",
    "split-image": "title_description_image",
    "alternating-cards": "title_list_of_cards_with_alternating_image",
    "profile-cards": "title_list_of_cards_with_image",
    "highlight-metrics": "title_image_description_list_with_highlighted_text_heading_description",
}

# Semantic slide role -> preferred Presenton layout ids. The renderer tries
# these ids in order and falls back to the legacy story layout mapping when
# none are available.
ROLE_LAYOUT_CANDIDATES: dict[str, tuple[str, ...]] = {
    "cover": ("title_slide",),
    "agenda": ("table_of_contents",),
    "section": ("section_header",),
    "hook": ("title_description_image", "title_slide"),
    "problem": ("title_description_image", "title_description_bullet_points_list_with_icon"),
    "solution": ("title_description_image", "title_description_bullet_points_grid_with_icon"),
    "big-stat": ("title_image_description_list_with_highlighted_text_heading_description",),
    "comparison": ("title_description_image", "title_description_bullet_points_grid_with_icon"),
    "process": ("title_description_bullet_points_list_with_icon",),
    "timeline": ("title_description_bullet_points_list_with_icon",),
    "features": ("title_description_bullet_points_grid_with_icon",),
    "case-study": ("title_list_of_cards_with_image", "title_list_of_cards_with_alternating_image"),
    "quote": ("quote_slide",),
    "team": ("title_list_of_cards_with_image",),
    "cta": ("closing_slide", "title_slide"),
    "summary": ("title_description_bullet_points_list_with_icon",),
    "content": ("title_description_bullet_points_list_with_icon",),
}


def _number(value: object, default: float = 0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _point(value: object) -> tuple[float, float]:
    if not isinstance(value, dict):
        return 0, 0
    return _number(value.get("x")), _number(value.get("y"))


def _size(value: object) -> tuple[float, float]:
    if not isinstance(value, dict):
        return 0, 0
    return _number(value.get("width")), _number(value.get("height"))


def _padding(value: object) -> tuple[float, float, float, float]:
    if not isinstance(value, dict):
        return 0, 0, 0, 0
    return (
        _number(value.get("top")),
        _number(value.get("right")),
        _number(value.get("bottom")),
        _number(value.get("left")),
    )


def _normalized_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")


def _content_points(text: str, count: int = 16) -> list[str]:
    parts = [
        part.strip().lstrip("•-*– ")
        for part in re.split(r"\n+|(?<=[.!?])\s+", text.strip())
        if part.strip().lstrip("•-*– ")
    ]
    if len(parts) < 2:
        words = text.split()
        chunk_size = max(1, (len(words) + 5) // 6)
        parts = [" ".join(words[index : index + chunk_size]) for index in range(0, len(words), chunk_size)]
    return (parts + [""] * count)[:count]


def _card_copy(text: str) -> tuple[str, str]:
    words = text.split()
    if len(words) <= 6:
        return text, ""
    return " ".join(words[:5]), " ".join(words[5:])


class _ContentSlots:
    def __init__(
        self,
        title: str,
        content: str,
        *,
        cover: bool,
        blocks: list[dict[str, object]] | None = None,
    ) -> None:
        self.title = title
        self.content = content
        self.cover = cover
        self.points = _content_points(content)
        self.structured = blocks is not None
        self.blocks = blocks or []
        self.counts: dict[str, int] = {}

    def _next(self, name: str) -> tuple[str, int]:
        index = self.counts.get(name, 0)
        self.counts[name] = index + 1
        if name.startswith("upper_text_"):
            index *= 2
        elif name.startswith("lower_text_"):
            index = index * 2 + 1
        return self.points[index % len(self.points)], index

    def text(self, name_value: object, original: str) -> str:
        name = _normalized_name(name_value)
        if self.cover:
            if name == "primary_heading":
                return self.title
            if name == "supporting_paragraph":
                return self.content
            if name == "badge_initials":
                return "AI"
            if name == "card_primary_text":
                return "Internal presentation"
            if name == "card_secondary_text":
                return "Generated workspace"
            return original

        title_slots = {
            "primary_heading",
            "large_heading",
            "section_heading",
            "main_heading",
            "stack_heading",
            "header_text",
        }
        if name in title_slots:
            return self.title
        if name in {"supporting_paragraph", "body_paragraph", "intro_paragraph", "stack_body"}:
            return self.content
        point, index = self._next(name)
        block = self.blocks[index] if index < len(self.blocks) else {}
        block_heading = str(block.get("heading") or "").strip()
        block_body = str(block.get("body") or "").strip()
        block_label = str(block.get("label") or "").strip()
        block_value = str(block.get("value") or "").strip()
        heading, description = _card_copy(point)
        if any(token in name for token in ("number", "badge")):
            return str(index + 1).zfill(2)
        if "metric_label" in name:
            return block_label or ("" if self.structured else f"KEY POINT {index + 1:02d}")
        if "metric_value" in name:
            return block_value or block_heading or ("" if self.structured else heading)
        if any(token in name for token in ("description", "caption", "body")):
            return block_body or ("" if self.structured else description or point)
        if any(token in name for token in ("title", "heading", "text")):
            return block_heading or ("" if self.structured else heading or point)
        return original


@lru_cache(maxsize=4)
def _load_template(path: str) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as template_file:
        template = json.load(template_file)
    if not isinstance(template.get("layouts"), list):
        raise ValueError("Presenton template has no layouts.")
    return template


class PresentonTemplateAdapter:
    """Compile pinned Presenton template-v2 layouts into flat native slide elements."""

    def __init__(self, template_path: Path = MODERN_TEMPLATE_PATH) -> None:
        self.template_path = template_path
        self.template = _load_template(str(template_path.resolve()))
        self.layouts = {
            str(layout["id"]): layout
            for layout in self.template["layouts"]
            if isinstance(layout, dict) and layout.get("id")
        }

    @property
    def layout_ids(self) -> tuple[str, ...]:
        return tuple(self.layouts)

    def compile_slide(
        self,
        layout_id: str,
        *,
        title: str,
        content: str,
        slide_index: int,
        slide_count: int,
        blocks: list[dict[str, object]] | None = None,
        assets: Mapping[str, str] | None = None,
    ) -> dict[str, object]:
        try:
            layout = self.layouts[layout_id]
        except KeyError as error:
            raise ValueError(f"Unknown Presenton layout: {layout_id}") from error

        self.elements: list[dict[str, object]] = []
        self.assets = assets or {}
        self.slots = _ContentSlots(
            title,
            content,
            cover=layout_id == "title_slide",
            blocks=blocks,
        )
        self.slide_index = slide_index
        self.slide_count = slide_count
        for component in layout.get("components", []):
            if not isinstance(component, dict):
                continue
            component_x, component_y = _point(component.get("position"))
            component_id = str(component.get("id") or "presenton-component")
            for element in component.get("elements", []):
                self._flatten(element, component_x, component_y, component_id)
        for element in layout.get("elements", []):
            self._flatten(element, 0, 0, "presenton-layout")

        return {
            "id": str(uuid4()),
            "title": title,
            "background": "#FFFFFF",
            "revision": 0,
            "layout_id": layout_id,
            "elements": self.elements,
        }

    def _base(
        self,
        source: dict[str, Any],
        x: float,
        y: float,
        width: float,
        height: float,
        component_id: str,
    ) -> dict[str, object] | None:
        x = max(0, min(STAGE_WIDTH, x))
        y = max(0, min(STAGE_HEIGHT, y))
        width = max(0, min(width, STAGE_WIDTH - x))
        height = max(0, min(height, STAGE_HEIGHT - y))
        if width <= 0 or height <= 0:
            return None
        result: dict[str, object] = {
            "id": str(uuid4()),
            "position": {"x": round(x, 2), "y": round(y, 2)},
            "size": {"width": round(width, 2), "height": round(height, 2)},
            "rotation": _number(source.get("rotation")),
            "opacity": max(0, min(1, _number(source.get("opacity"), 1))),
            "locked": False,
            "decorative": bool(source.get("decorative", False)),
            "componentId": component_id,
        }
        if source.get("name"):
            result["name"] = str(source["name"])
            result["componentSlot"] = str(source["name"])
        return result

    def _font(self, value: object) -> dict[str, object]:
        source = value if isinstance(value, dict) else {}
        font: dict[str, object] = {
            "family": str(source.get("family") or "Montserrat"),
            "size": _number(source.get("size"), 18),
            "color": str(source.get("color") or "#334155"),
            "bold": bool(source.get("bold", False)),
            "italic": bool(source.get("italic", False)),
            "underline": bool(source.get("underline", False)),
            "lineHeight": max(0.5, _number(source.get("line_height"), 1.2)),
        }
        if isinstance(source.get("letter_spacing"), (int, float)):
            font["letterSpacing"] = source["letter_spacing"]
        return font

    def _fill(self, value: object) -> dict[str, object] | None:
        if not isinstance(value, dict) or not value.get("color"):
            return None
        return {
            "color": str(value["color"]),
            "opacity": max(0, min(1, _number(value.get("opacity"), 1))),
        }

    def _stroke(self, value: object) -> dict[str, object] | None:
        if not isinstance(value, dict) or not value.get("color"):
            return None
        return {
            "color": str(value["color"]),
            "width": max(0, _number(value.get("width"), 1)),
            "opacity": max(0, min(1, _number(value.get("opacity"), 1))),
        }

    def _flatten(
        self,
        source: object,
        parent_x: float,
        parent_y: float,
        component_id: str,
        override: tuple[float, float, float, float] | None = None,
    ) -> None:
        if not isinstance(source, dict):
            return
        local_x, local_y = _point(source.get("position"))
        width, height = _size(source.get("size"))
        if override:
            x, y, available_width, available_height = override
            width = width or available_width
            height = height or available_height
        else:
            x, y = parent_x + local_x, parent_y + local_y

        element_type = source.get("type")
        if element_type == "text":
            base = self._base(source, x, y, width, height, component_id)
            if not base:
                return
            raw_runs = source.get("runs") if isinstance(source.get("runs"), list) else []
            original = "".join(str(run.get("text", "")) for run in raw_runs if isinstance(run, dict))
            text = self.slots.text(source.get("name"), original)
            alignment = source.get("alignment") if isinstance(source.get("alignment"), dict) else {}
            base.update(
                {
                    "type": "text",
                    "runs": [{"text": text}],
                    "font": self._font(source.get("font")),
                    "horizontalAlign": alignment.get("horizontal", "left"),
                    "verticalAlign": alignment.get("vertical", "top"),
                }
            )
            self.elements.append(base)
            return

        if element_type == "vector":
            points = source.get("points") if isinstance(source.get("points"), list) else []
            point_values = [_point(point) for point in points]
            if point_values:
                min_x = min(point[0] for point in point_values)
                min_y = min(point[1] for point in point_values)
                max_x = max(point[0] for point in point_values)
                max_y = max(point[1] for point in point_values)
                x += min_x
                y += min_y
                width, height = max_x - min_x, max_y - min_y
            base = self._base(source, x, y, width, height, component_id)
            if not base:
                return
            radii = source.get("corner_radii") if isinstance(source.get("corner_radii"), list) else []
            base.update(
                {
                    "type": "shape",
                    "shape": "rectangle",
                    "cornerRadius": max((_number(radius) for radius in radii), default=0),
                    "decorative": True,
                }
            )
            fill = self._fill(source.get("fill"))
            stroke = self._stroke(source.get("stroke"))
            if fill:
                base["fill"] = fill
            if stroke:
                base["stroke"] = stroke
            self.elements.append(base)
            return

        if element_type == "image":
            base = self._base(source, x, y, width, height, component_id)
            if not base:
                return
            slot_name = str(source.get("name") or "")
            asset_id = self.assets.get(slot_name)
            if asset_id:
                fit = str(source.get("fit") or "cover")
                focus_x = _number(source.get("focus_x"), 50) / 100
                focus_y = _number(source.get("focus_y"), 50) / 100
                base.update(
                    {
                        "type": "image",
                        "assetId": asset_id,
                        "fit": fit if fit in {"contain", "cover", "fill"} else "cover",
                        "focusX": max(0, min(1, focus_x)),
                        "focusY": max(0, min(1, focus_y)),
                        "cropScale": 1,
                        "flipHorizontal": False,
                        "flipVertical": False,
                        "alt": f"{slot_name.replace('_', ' ').title()} visual",
                    }
                )
                self.elements.append(base)
                return
            radius = source.get("border_radius")
            radius_values = radius.values() if isinstance(radius, dict) else []
            base.update(
                {
                    "type": "shape",
                    "shape": "rectangle",
                    "fill": {"color": "#F5F8FE", "opacity": 1},
                    "stroke": {"color": "#DCE5F5", "width": 1, "opacity": 1},
                    "cornerRadius": max((_number(value) for value in radius_values), default=4),
                    "decorative": False,
                    "name": str(source.get("name") or "Image placeholder"),
                }
            )
            self.elements.append(base)
            return

        if element_type == "container":
            base = self._base(source, x, y, width, height, component_id)
            if base and (source.get("fill") or source.get("stroke")):
                radius = source.get("border_radius")
                radius_values = radius.values() if isinstance(radius, dict) else []
                base.update(
                    {
                        "type": "shape",
                        "shape": "rectangle",
                        "cornerRadius": max((_number(value) for value in radius_values), default=0),
                        "decorative": True,
                    }
                )
                fill = self._fill(source.get("fill"))
                stroke = self._stroke(source.get("stroke"))
                if fill:
                    base["fill"] = fill
                if stroke:
                    base["stroke"] = stroke
                self.elements.append(base)
            top, right, bottom, left = _padding(source.get("padding"))
            child = source.get("child")
            if isinstance(child, dict):
                self._flatten(
                    child,
                    x + left,
                    y + top,
                    component_id,
                    (x + left, y + top, max(0, width - left - right), max(0, height - top - bottom)),
                )
            return

        if element_type == "group":
            for child in source.get("children", []):
                self._flatten(child, x, y, component_id)
            return

        if element_type in {"flex", "grid"}:
            self._flatten_layout(source, x, y, width, height, component_id)
            return

        if element_type in {"chart", "table"}:
            base = self._base(source, x, y, width, height, component_id)
            if base:
                base.update(
                    {
                        "type": "shape",
                        "shape": "rectangle",
                        "fill": {"color": "#F5F8FE", "opacity": 1},
                        "stroke": {"color": "#DCE5F5", "width": 1, "opacity": 1},
                        "cornerRadius": 8,
                        "decorative": False,
                    }
                )
                self.elements.append(base)

    def _flatten_layout(
        self,
        source: dict[str, Any],
        x: float,
        y: float,
        width: float,
        height: float,
        component_id: str,
    ) -> None:
        children = [child for child in source.get("children", []) if isinstance(child, dict)]
        if not children:
            return
        top, right, bottom, left = _padding(source.get("padding"))
        inner_x, inner_y = x + left, y + top
        inner_width = max(0, width - left - right)
        inner_height = max(0, height - top - bottom)
        if source.get("type") == "grid":
            columns = max(1, int(_number(source.get("columns"), 1)))
            column_gap = _number(source.get("column_gap"), _number(source.get("gap")))
            row_gap = _number(source.get("row_gap"), _number(source.get("gap")))
            rows = max(1, (len(children) + columns - 1) // columns)
            cell_width = max(0, (inner_width - column_gap * (columns - 1)) / columns)
            cell_height = max(0, (inner_height - row_gap * (rows - 1)) / rows)
            for index, child in enumerate(children):
                column, row = index % columns, index // columns
                self._flatten(
                    child,
                    inner_x,
                    inner_y,
                    component_id,
                    (
                        inner_x + column * (cell_width + column_gap),
                        inner_y + row * (cell_height + row_gap),
                        cell_width,
                        cell_height,
                    ),
                )
            return

        direction = source.get("direction", "row")
        gap = _number(source.get("gap"))
        main_available = inner_width if direction == "row" else inner_height
        specified = []
        for child in children:
            child_width, child_height = _size(child.get("size"))
            specified.append(child_width if direction == "row" else child_height)
        missing = sum(value <= 0 for value in specified)
        remaining = max(0, main_available - gap * (len(children) - 1) - sum(specified))
        fallback = remaining / missing if missing else 0
        cursor = inner_x if direction == "row" else inner_y
        for child, main_size in zip(children, specified):
            main_size = main_size or fallback
            child_width, child_height = _size(child.get("size"))
            if direction == "row":
                frame = (cursor, inner_y, main_size, child_height or inner_height)
            else:
                frame = (inner_x, cursor, child_width or inner_width, main_size)
            self._flatten(child, inner_x, inner_y, component_id, frame)
            cursor += main_size + gap
