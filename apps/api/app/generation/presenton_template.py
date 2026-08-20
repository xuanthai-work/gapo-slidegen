from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Mapping
from uuid import uuid4

from .layouts.registry import ContentConstraints
from .copy_text import truncate_content_text
from .local_icon_registry import resolve_icon_for_context

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

# Layout shape hints help the selector pick a template that matches the actual
# content produced by the story planner.
LayoutShape = Literal[
    "cover",
    "text_only",
    "text_with_media",
    "two_column_text",
    "grid_cards",
    "metric_stack",
    "index_grid",
]


# Maps a Presenton layout id to its visual shape. The selector uses this to
# decide whether a layout fits the slide's blocks and asset availability.
LAYOUT_SHAPES: dict[str, LayoutShape] = {
    "title_slide": "cover",
    "table_of_contents": "index_grid",
    "section_header": "text_only",
    "title_description_bullet_points_grid_with_icon": "grid_cards",
    "title_description_bullet_points_list_with_icon": "two_column_text",
    "title_description_image": "text_with_media",
    "title_description_chart": "text_with_media",
    "title_description_chart_table": "text_with_media",
    "title_list_of_cards_with_alternating_image": "grid_cards",
    "title_list_of_cards_with_image": "grid_cards",
    "title_image_description_list_with_highlighted_text_heading_description": "metric_stack",
}


# Semantic slide role -> preferred Presenton layout ids. The renderer tries
# these ids in order and falls back to the legacy story layout mapping when
# none are available.
ROLE_LAYOUT_CANDIDATES: dict[str, tuple[str, ...]] = {
    "cover": ("title_slide",),
    "agenda": ("table_of_contents", "title_description_bullet_points_list_with_icon"),
    "section": ("section_header", "title_description_bullet_points_list_with_icon"),
    "hook": ("title_description_image", "title_slide"),
    "problem": ("title_description_image", "title_description_bullet_points_list_with_icon"),
    "solution": ("title_description_image", "title_description_bullet_points_grid_with_icon"),
    "big-stat": (
        "title_image_description_list_with_highlighted_text_heading_description",
        "title_description_bullet_points_grid_with_icon",
        "title_description_chart",
    ),
    "comparison": (
        "title_description_bullet_points_grid_with_icon",
        "title_description_image",
        "title_description_bullet_points_list_with_icon",
    ),
    "process": ("title_description_bullet_points_list_with_icon", "title_description_image"),
    "timeline": ("title_description_bullet_points_list_with_icon", "title_description_image"),
    "features": (
        "title_description_bullet_points_grid_with_icon",
        "title_list_of_cards_with_image",
        "title_description_bullet_points_list_with_icon",
    ),
    "case-study": (
        "title_list_of_cards_with_image",
        "title_list_of_cards_with_alternating_image",
        "title_description_image",
    ),
    "quote": ("title_description_image", "title_slide"),
    "team": ("title_list_of_cards_with_image", "title_list_of_cards_with_alternating_image"),
    "cta": ("title_description_image", "title_slide"),
    "summary": (
        "title_description_bullet_points_list_with_icon",
        "title_description_bullet_points_grid_with_icon",
    ),
    "content": (
        "title_description_bullet_points_list_with_icon",
        "title_description_bullet_points_grid_with_icon",
    ),
}

ROLE_CONTENT_BUDGETS: dict[str, dict[str, int]] = {
    "cover": {"title_max_chars": 72, "content_max_chars": 200},
    "quote": {"content_max_chars": 280, "block_body_max_chars": 280},
    "big-stat": {"block_heading_max_chars": 60, "block_body_max_chars": 140},
    "cta": {"title_max_chars": 64, "content_max_chars": 220},
    "summary": {"content_max_chars": 240, "block_body_max_chars": 180},
}

PRESENTON_LAYOUT_CONSTRAINTS: dict[str, ContentConstraints] = {
    "title_slide": ContentConstraints(72, 200, 55, 160, 0),
    "title_description_bullet_points_grid_with_icon": ContentConstraints(72, 220, 60, 160, 4),
    "title_description_bullet_points_list_with_icon": ContentConstraints(72, 240, 60, 180, 6),
    "title_description_chart": ContentConstraints(72, 220, 60, 160, 4),
    "title_description_chart_table": ContentConstraints(72, 200, 60, 160, 4),
    "title_description_image": ContentConstraints(72, 240, 60, 180, 3),
    "title_list_of_cards_with_alternating_image": ContentConstraints(72, 220, 60, 160, 4),
    "title_list_of_cards_with_image": ContentConstraints(72, 220, 60, 160, 6),
    "title_image_description_list_with_highlighted_text_heading_description": ContentConstraints(
        72, 220, 60, 160, 4
    ),
    "table_of_contents": ContentConstraints(72, 180, 60, 160, 8),
}
DEFAULT_LAYOUT_CONSTRAINTS = ContentConstraints(72, 240, 60, 180, 4)
COVER_LAYOUT_CONSTRAINTS = ContentConstraints(72, 200, 55, 160, 0)
INDEX_LAYOUT_CONSTRAINTS = ContentConstraints(72, 180, 60, 160, 8)


def is_cover_layout(layout_id: str) -> bool:
    name = layout_id.lower()
    if "cover" in name or name in {"title_slide", "title_intro"}:
        return True
    if name.startswith("title_slide") or name.startswith("centered_title_metadata"):
        return True
    return False


def is_auto_excluded_layout(layout_id: str) -> bool:
    name = layout_id.lower()
    if "table_of_contents" in name or "index_grid" in name:
        return False
    return any(token in name for token in ("chart", "table", "gauge", "donut"))


def _layout_shape(layout_id: str) -> LayoutShape:
    if layout_id in LAYOUT_SHAPES:
        return LAYOUT_SHAPES[layout_id]
    name = layout_id.lower()
    if is_cover_layout(layout_id):
        return "cover"
    if "table_of_contents" in name or "index_grid" in name or "agenda" in name:
        return "index_grid"
    if "metric" in name:
        return "metric_stack"
    if "grid" in name or "card" in name:
        return "grid_cards"
    if "list" in name or "bullet" in name:
        return "two_column_text"
    if any(token in name for token in ("image", "photo", "visual", "media")):
        return "text_with_media"
    return "text_only"


def _has_media_slot(layout_id: str) -> bool:
    """Return True if the layout reserves a panel for image/chart media."""
    return _layout_shape(layout_id) in {"text_with_media", "metric_stack"}


def _has_metric_slots(layout_id: str) -> bool:
    """Return True if the layout exposes metric_label/metric_value slots."""
    return _layout_shape(layout_id) == "metric_stack"


def _is_card_grid(layout_id: str) -> bool:
    return _layout_shape(layout_id) == "grid_cards"



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


def _normalize_slide_copy(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    cleaned = re.sub(r"\s+([,.!?;:])", r"\1", cleaned)
    return cleaned


def _merge_budgets(
    constraints: ContentConstraints,
    role: str | None,
    budgets: dict[str, int] | None,
) -> dict[str, int]:
    merged = constraints.as_budget()
    overrides = [ROLE_CONTENT_BUDGETS.get(role, {}) if role else {}, budgets or {}]
    for override in overrides:
        for field, limit in override.items():
            if field in merged:
                merged[field] = min(merged[field], limit)
    return merged


_ITEM_NAME_MARKERS = (
    "card_",
    "item_",
    "callout_",
    "step_",
    "milestone_",
    "column_",
    "row_",
    "feature_",
    "entry_",
    "panel_",
    "profile_",
    "person_",
    "plan_",
    "stage_",
    "metric_",
    "review_",
    "agenda_",
    "section_",
    "timeline_",
    "note_",
    "list_item",
    "detail_",
    "stacked_",
    "upper_text",
    "lower_text",
    "upper_card",
    "lower_card",
    "left_callout",
    "right_callout",
    "table_",
    "first_row",
    "second_row",
    "third_row",
    "fourth_row",
    "gauge_",
    "year_label",
    "duration_",
    "inner_metric",
    "middle_metric",
    "outer_metric",
    "large_metric",
    "lower_metric",
)
_PAGE_NAME_MARKERS = (
    "page_number",
    "page_marker",
    "page_folio",
    "page_label",
    "footer_page",
    "footer_slide",
    "footer_number",
    "footer_value",
    "footer_index",
    "pagination",
    "footer_marker",
)
_SLIDE_TITLE_TOKENS = ("title", "heading", "headline", "header_text", "header_title")
_SLIDE_BODY_TOKENS = (
    "subtitle",
    "supporting",
    "description",
    "paragraph",
    "body_copy",
    "body_paragraph",
    "body_text",
    "intro_description",
    "intro_paragraph",
    "intro_text",
    "intro_summary",
    "intro_statement",
    "intro_subtitle",
    "tagline",
    "summary",
    "caption_primary",
    "cover_subtitle",
    "slide_intro",
    "stack_body",
)


def _name_has(name: str, markers: tuple[str, ...]) -> bool:
    return any(marker in name for marker in markers)


_SLIDE_LEVEL_EXCLUSIONS = (
    "section_heading",
    "section_title",
    "section_header",
    "section_kicker",
)
_ITEM_HEADING_MARKERS = (
    "card_title",
    "entry_title",
    "item_title",
    "feature_title",
    "point_title",
    "callout_title",
    "step_title",
    "metric_label",
    "upper_text_heading",
    "lower_text_heading",
)


def _is_slide_level_name(name: str) -> bool:
    return _name_has(name, _SLIDE_LEVEL_EXCLUSIONS)


def _is_item_name(name: str) -> bool:
    if _is_slide_level_name(name):
        return False
    return _name_has(name, _ITEM_NAME_MARKERS)


def _is_item_heading_name(name: str) -> bool:
    if not _is_item_name(name):
        return False
    if _name_has(name, _ITEM_HEADING_MARKERS):
        return True
    if any(token in name for token in ("description", "caption", "body", "subtitle")):
        return False
    return any(token in name for token in ("title", "heading"))


def _is_page_name(name: str) -> bool:
    return _name_has(name, _PAGE_NAME_MARKERS)


def _is_slide_title_name(name: str) -> bool:
    if _is_page_name(name):
        return False
    if _is_slide_level_name(name):
        return True
    if _is_item_name(name):
        return False
    if any(token in name for token in ("subtitle", "supporting", "tagline", "caption")):
        return False
    return any(token in name for token in _SLIDE_TITLE_TOKENS)


def _is_slide_body_name(name: str) -> bool:
    if _is_item_name(name) or _is_page_name(name) or _is_slide_title_name(name):
        return False
    return any(token in name for token in _SLIDE_BODY_TOKENS)


def _iter_text_names(node: object) -> list[str]:
    names: list[str] = []
    if isinstance(node, dict):
        if node.get("type") == "text" and node.get("name"):
            names.append(str(node["name"]))
        for value in node.values():
            names.extend(_iter_text_names(value))
    elif isinstance(node, list):
        for value in node:
            names.extend(_iter_text_names(value))
    return names


def _child_has_item_text(node: dict[str, Any]) -> bool:
    return any(_is_item_heading_name(_normalized_name(name)) for name in _iter_text_names(node))


def _is_small_icon_slot(name: str, width: float, height: float) -> bool:
    normalized = _normalized_name(name)
    if any(token in normalized for token in ("icon", "avatar", "favicon")):
        return True
    return max(width, height) <= 96.0


class _ContentSlots:
    def __init__(
        self,
        title: str,
        content: str,
        *,
        cover: bool,
        blocks: list[dict[str, object]] | None = None,
        role: str | None = None,
        budgets: dict[str, int] | None = None,
        constraints: ContentConstraints,
        slide_index: int = 0,
    ) -> None:
        self.title = _normalize_slide_copy(title)
        self.content = _normalize_slide_copy(content)
        self.cover = cover
        self.role = role or "content"
        self.points = _content_points(self.content)
        self.structured = blocks is not None
        self.blocks = blocks or []
        self.counts: dict[str, int] = {}
        self.budgets = _merge_budgets(constraints, role, budgets)
        self.slide_index = slide_index

    def _respect_budget(self, text: str, field: str) -> str:
        limit = self.budgets.get(field)
        if limit is None:
            return text
        return truncate_content_text(text, limit)

    def _next(self, name: str) -> tuple[str, int]:
        index = self.counts.get(name, 0)
        self.counts[name] = index + 1
        if name.startswith("upper_text_"):
            index *= 2
        elif name.startswith("lower_text_"):
            index = index * 2 + 1
        return self.points[index % len(self.points)], index

    def _page_label(self) -> str:
        return f"{self.slide_index + 1:02d}"

    @staticmethod
    def _drop_template_copy(original: str) -> str:
        stripped = original.strip()
        if len(stripped) <= 2:
            return original
        return ""

    def text(self, name_value: object, original: str) -> str:
        name = _normalized_name(name_value)
        if self.cover:
            if _is_slide_title_name(name):
                return self._respect_budget(self.title, "title_max_chars")
            if _is_slide_body_name(name):
                return self._respect_budget(self.content, "content_max_chars")
            if name == "badge_initials":
                return "AI"
            if name == "card_primary_text":
                return "Internal presentation"
            if name == "card_secondary_text":
                return "Generated workspace"
            if _is_page_name(name):
                return self._page_label()
            return self._drop_template_copy(original)

        if _is_page_name(name):
            return self._page_label()
        if _is_slide_title_name(name):
            return self._respect_budget(self.title, "title_max_chars")
        if _is_slide_body_name(name):
            return self._respect_budget(self.content, "content_max_chars")
        point, index = self._next(name)
        block = self.blocks[index] if index < len(self.blocks) else {}
        block_heading = str(block.get("heading") or "").strip()
        block_body = str(block.get("body") or "").strip()
        block_label = str(block.get("label") or "").strip()
        block_value = str(block.get("value") or "").strip()
        heading, description = _card_copy(point)
        if any(token in name for token in ("number", "badge")):
            if self.structured and index >= len(self.blocks):
                return ""
            return str(index + 1).zfill(2)
        if "metric_label" in name:
            return self._respect_budget(
                block_label or ("" if self.structured else f"KEY POINT {index + 1:02d}"),
                "block_heading_max_chars",
            )
        if "metric_value" in name:
            return self._respect_budget(
                block_value or block_heading or ("" if self.structured else heading),
                "block_body_max_chars",
            )
        if any(token in name for token in ("description", "caption", "body")):
            return self._respect_budget(
                block_body or ("" if self.structured else description or point),
                "block_body_max_chars",
            )
        if any(token in name for token in ("title", "heading", "text")):
            return self._respect_budget(
                block_heading or ("" if self.structured else heading or point),
                "block_heading_max_chars",
            )
        return self._drop_template_copy(original)

    def item_slots_used(self) -> int:
        counts = [count for name, count in self.counts.items() if _is_item_heading_name(name)]
        return max(counts) if counts else 0


@lru_cache(maxsize=16)
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

    def content_constraints(self, layout_id: str) -> ContentConstraints:
        if layout_id not in self.layouts:
            raise ValueError(f"Unknown Presenton layout: {layout_id}")
        if layout_id in PRESENTON_LAYOUT_CONSTRAINTS:
            return PRESENTON_LAYOUT_CONSTRAINTS[layout_id]
        if is_cover_layout(layout_id):
            return COVER_LAYOUT_CONSTRAINTS
        name = layout_id.lower()
        if "table_of_contents" in name or "index_grid" in name or "agenda" in name:
            return INDEX_LAYOUT_CONSTRAINTS
        return DEFAULT_LAYOUT_CONSTRAINTS

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
        role: str | None = None,
        budgets: dict[str, int] | None = None,
    ) -> dict[str, object]:
        try:
            layout = self.layouts[layout_id]
        except KeyError as error:
            raise ValueError(f"Unknown Presenton layout: {layout_id}") from error

        title = _normalize_slide_copy(title)
        content = _normalize_slide_copy(content)

        self.elements: list[dict[str, object]] = []
        self.assets = assets or {}
        self.slots = _ContentSlots(
            title,
            content,
            cover=is_cover_layout(layout_id) or slide_index == 0,
            blocks=blocks,
            role=role,
            budgets=budgets,
            constraints=self.content_constraints(layout_id),
            slide_index=slide_index,
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
            if not _is_small_icon_slot(slot_name, width, height):
                return
            icon_svg = self._fallback_icon_svg(slot_name)
            if icon_svg:
                base.update(
                    {
                        "type": "svg",
                        "svg": icon_svg,
                        "alt": f"{slot_name.replace('_', ' ').title()} icon",
                        "decorative": True,
                        "name": str(source.get("name") or "Image icon fallback"),
                    }
                )
                self.elements.append(base)
                return
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

    def _fallback_icon_svg(self, slot_name: str) -> str | None:
        return resolve_icon_for_context(
            role=self.slots.role,
            slot_name=slot_name,
            title=self.slots.title,
            content=self.slots.content,
        )

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
        if self.slots.structured:
            remaining = max(0, len(self.slots.blocks) - self.slots.item_slots_used())
            kept: list[dict[str, Any]] = []
            for child in children:
                if _child_has_item_text(child):
                    if remaining <= 0:
                        continue
                    remaining -= 1
                kept.append(child)
            children = kept
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
