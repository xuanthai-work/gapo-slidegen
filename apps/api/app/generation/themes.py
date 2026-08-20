from pathlib import Path
from typing import Final, Literal

from .presenton_template import MODERN_TEMPLATE_PATH, STAGE_HEIGHT, STAGE_WIDTH


TemplateId = Literal[
    "modern",
    "editorial",
    "executive",
    "swift",
    "standard",
    "momentum",
    "general",
    "dynamic",
]
ColorSchemeId = Literal[
    "edge-yellow",
    "light-rose",
    "mint-blue",
    "professional-blue",
    "professional-dark",
]

TEMPLATES_DIR: Final = Path(MODERN_TEMPLATE_PATH).parent
DEFAULT_TEMPLATE_ID: Final = "modern"
DEFAULT_COLOR_SCHEME_ID: Final = "professional-blue"
DEFAULT_THEME_ID: Final = f"{DEFAULT_TEMPLATE_ID}:{DEFAULT_COLOR_SCHEME_ID}"

TEMPLATES: Final[dict[str, dict[str, str]]] = {
    "modern": {"id": "modern", "name": "Modern"},
    "editorial": {"id": "editorial", "name": "Editorial"},
    "executive": {"id": "executive", "name": "Executive"},
    "swift": {"id": "swift", "name": "Swift"},
    "standard": {"id": "standard", "name": "Standard"},
    "momentum": {"id": "momentum", "name": "Momentum"},
    "general": {"id": "general", "name": "General"},
    "dynamic": {"id": "dynamic", "name": "Dynamic"},
}

COLOR_SCHEMES: Final[dict[str, dict[str, object]]] = {
    "edge-yellow": {
        "id": "edge-yellow",
        "name": "Edge Yellow",
        "colors": {
            "background": "#1F1F1F",
            "surface": "#424242",
            "primary": "#F5F547",
            "secondary": "#161616",
            "accent": "#F5F547",
            "text": "#F5F547",
            "muted": "#908C00",
            "on_primary": "#161616",
        },
        "fonts": {"heading": "Playfair Display", "body": "Playfair Display"},
    },
    "light-rose": {
        "id": "light-rose",
        "name": "Light Rose",
        "colors": {
            "background": "#F69C9C",
            "surface": "#FFAEB4",
            "primary": "#030204",
            "secondary": "#BF6A6B",
            "accent": "#030204",
            "text": "#030202",
            "muted": "#706D73",
            "on_primary": "#BEBEBE",
        },
        "fonts": {"heading": "Overpass", "body": "Overpass"},
    },
    "mint-blue": {
        "id": "mint-blue",
        "name": "Mint Blue",
        "colors": {
            "background": "#FFFFFF",
            "surface": "#80E7CF",
            "primary": "#3B3172",
            "secondary": "#3B3172",
            "accent": "#80E7CF",
            "text": "#3B3172",
            "muted": "#4AB39D",
            "on_primary": "#FFFFFF",
        },
        "fonts": {"heading": "Prompt", "body": "Prompt"},
    },
    "professional-blue": {
        "id": "professional-blue",
        "name": "Professional Blue",
        "colors": {
            "background": "#FFFFFF",
            "surface": "#DAE6FF",
            "primary": "#161616",
            "secondary": "#000000",
            "accent": "#DAE6FF",
            "text": "#000000",
            "muted": "#6F6F6F",
            "on_primary": "#EEEEEA",
        },
        "fonts": {"heading": "Inter", "body": "Inter"},
    },
    "professional-dark": {
        "id": "professional-dark",
        "name": "Professional Dark",
        "colors": {
            "background": "#050505",
            "surface": "#424242",
            "primary": "#EFF5F1",
            "secondary": "#050505",
            "accent": "#EFF5F1",
            "text": "#EFF5F1",
            "muted": "#959FB0",
            "on_primary": "#050505",
        },
        "fonts": {"heading": "Instrument Sans", "body": "Instrument Sans"},
    },
}

_LEGACY_THEME_IDS: Final[dict[str, tuple[str, str]]] = {
    "modern-blue": (DEFAULT_TEMPLATE_ID, DEFAULT_COLOR_SCHEME_ID),
    "editorial-cobalt": ("editorial", DEFAULT_COLOR_SCHEME_ID),
    "warm-studio": ("executive", "edge-yellow"),
    "midnight-signal": ("dynamic", "professional-dark"),
}


def parse_theme_ref(theme_id: str) -> tuple[str, str]:
    if theme_id in _LEGACY_THEME_IDS:
        return _LEGACY_THEME_IDS[theme_id]
    if ":" in theme_id:
        template_id, color_scheme_id = theme_id.split(":", 1)
        return template_id, color_scheme_id
    if theme_id in TEMPLATES:
        return theme_id, DEFAULT_COLOR_SCHEME_ID
    return DEFAULT_TEMPLATE_ID, DEFAULT_COLOR_SCHEME_ID


def compose_theme_id(template_id: str, color_scheme_id: str) -> str:
    return f"{template_id}:{color_scheme_id}"


def template_path_for(template_id: str) -> Path:
    candidate = TEMPLATES_DIR / f"{template_id}.json"
    if candidate.is_file():
        return candidate
    return Path(MODERN_TEMPLATE_PATH)


def get_theme(theme_id: str) -> dict[str, object]:
    template_id, color_scheme_id = parse_theme_ref(theme_id)
    template = TEMPLATES.get(template_id, TEMPLATES[DEFAULT_TEMPLATE_ID])
    scheme = COLOR_SCHEMES.get(color_scheme_id, COLOR_SCHEMES[DEFAULT_COLOR_SCHEME_ID])
    colors = dict(scheme["colors"])  # type: ignore[arg-type]
    fonts = dict(scheme["fonts"])  # type: ignore[arg-type]
    return {
        "id": compose_theme_id(str(template["id"]), str(scheme["id"])),
        "name": f"{template['name']} / {scheme['name']}",
        "colors": {
            "background": colors["background"],
            "surface": colors["surface"],
            "primary": colors["primary"],
            "secondary": colors["secondary"],
            "accent": colors["accent"],
            "text": colors["text"],
            "muted": colors["muted"],
        },
        "fonts": {"heading": str(fonts["heading"]), "body": str(fonts["body"])},
    }


def _hex_rgb(color: str) -> tuple[int, int, int] | None:
    value = color.lstrip("#")
    if len(value) == 3:
        value = "".join(channel * 2 for channel in value)
    if len(value) != 6:
        return None
    try:
        return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
    except ValueError:
        return None


def _luminance(color: str) -> float:
    rgb = _hex_rgb(color)
    if rgb is None:
        return 0.5
    red, green, blue = (channel / 255 for channel in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast_ratio(first: str, second: str) -> float:
    light = max(_luminance(first), _luminance(second))
    dark = min(_luminance(first), _luminance(second))
    return (light + 0.05) / (dark + 0.05)


def _on_primary_color(theme: dict[str, object], palette: dict[str, str]) -> str:
    scheme_id = parse_theme_ref(str(theme.get("id") or DEFAULT_THEME_ID))[1]
    scheme = COLOR_SCHEMES.get(scheme_id, COLOR_SCHEMES[DEFAULT_COLOR_SCHEME_ID])
    colors = scheme.get("colors")
    if isinstance(colors, dict) and colors.get("on_primary"):
        return str(colors["on_primary"])
    return palette["text"]


def _element_bounds(element: dict[str, object]) -> tuple[float, float, float, float] | None:
    position = element.get("position")
    size = element.get("size")
    if not isinstance(position, dict) or not isinstance(size, dict):
        return None
    return (
        float(position.get("x") or 0),
        float(position.get("y") or 0),
        float(size.get("width") or 0),
        float(size.get("height") or 0),
    )


def _fill_color(element: dict[str, object]) -> str | None:
    fill = element.get("fill")
    if not isinstance(fill, dict) or not fill.get("color"):
        return None
    for opacity in (fill.get("opacity", 1), element.get("opacity", 1)):
        if isinstance(opacity, (int, float)) and opacity < 0.2:
            return None
    return str(fill["color"])


def _is_canvas_fill(element: dict[str, object]) -> bool:
    bounds = _element_bounds(element)
    if bounds is None:
        return False
    _, _, width, height = bounds
    return width * height >= 0.85 * STAGE_WIDTH * STAGE_HEIGHT


def _iter_elements(node: object) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    if isinstance(node, dict):
        found.append(node)
        children = node.get("children")
        if isinstance(children, list):
            for child in children:
                found.extend(_iter_elements(child))
        if node.get("child") is not None:
            found.extend(_iter_elements(node["child"]))
    elif isinstance(node, list):
        for item in node:
            found.extend(_iter_elements(item))
    return found


def _pick_contrasting_color(background: str, candidates: list[str]) -> str:
    unique: list[str] = []
    seen: set[str] = set()
    for color in candidates:
        key = color.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(color)
    return max(unique, key=lambda color: _contrast_ratio(background, color))


def _background_behind(
    element: dict[str, object],
    painted: list[dict[str, object]],
    canvas: str,
) -> str:
    bounds = _element_bounds(element)
    if bounds is None:
        return canvas
    x, y, width, height = bounds
    sample_x = x + width / 2
    sample_y = y + height / 2
    found = canvas
    for other in painted:
        if other is element:
            continue
        color = _fill_color(other)
        other_bounds = _element_bounds(other)
        if color is None or other_bounds is None:
            continue
        ox, oy, ow, oh = other_bounds
        if ox <= sample_x <= ox + ow and oy <= sample_y <= oy + oh:
            found = color
    return found


def apply_color_scheme(slide: dict[str, object], theme: dict[str, object]) -> dict[str, object]:
    colors = theme.get("colors")
    fonts = theme.get("fonts")
    if not isinstance(colors, dict) or not isinstance(fonts, dict):
        return slide
    palette = {key: str(value) for key, value in colors.items()}
    heading = str(fonts.get("heading") or "Inter")
    body = str(fonts.get("body") or heading)
    on_primary = _on_primary_color(theme, palette)
    slide["background"] = palette["background"]
    painted = _iter_elements(slide.get("elements")) if isinstance(slide.get("elements"), list) else []

    for element in painted:
        font = element.get("font")
        if element.get("type") == "text" and isinstance(font, dict):
            font["family"] = heading if font.get("bold") else body
        fill = element.get("fill")
        if isinstance(fill, dict) and fill.get("color"):
            previous = str(fill["color"])
            if _is_canvas_fill(element):
                fill["color"] = palette["background"]
            elif _luminance(previous) > 0.72:
                fill["color"] = palette["surface"]
            else:
                fill["color"] = palette["primary"]
        stroke = element.get("stroke")
        if isinstance(stroke, dict) and stroke.get("color"):
            stroke["color"] = palette["muted"]

    text_candidates = [palette["text"], on_primary, "#111111", "#F7F7F7"]
    for element in painted:
        font = element.get("font")
        if element.get("type") != "text" or not isinstance(font, dict):
            continue
        background = _background_behind(element, painted, palette["background"])
        font["color"] = _pick_contrasting_color(background, text_candidates)
    return slide
