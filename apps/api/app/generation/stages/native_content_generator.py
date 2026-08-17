import re
from typing import Mapping
from uuid import uuid4

from ..themes import get_theme
from .models import StoryOutline, StoryOutlineItem
from ..provider import GenerationRequest


def _chunks(text: str, count: int) -> list[str]:
    if count <= 0:
        return []
    words = text.split()
    if not words:
        return [""] * count
    size = max(1, (len(words) + count - 1) // count)
    chunks = [" ".join(words[index : index + size]) for index in range(0, len(words), size)]
    return (chunks + [""] * count)[:count]


def _automatic_slide_count(text: str) -> int:
    word_count = len(text.split())
    return max(5, min(15, 4 + (word_count + 119) // 120))


def _text_element(
    text: str,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    size: int,
    color: str,
    family: str,
    bold: bool = False,
    align: str = "left",
    vertical_align: str = "top",
    line_height: float = 1.18,
    letter_spacing: float | None = None,
    italic: bool = False,
    name: str | None = None,
) -> dict[str, object]:
    font: dict[str, object] = {
        "family": family,
        "size": size,
        "color": color,
        "bold": bold,
        "italic": italic,
        "lineHeight": line_height,
    }
    if letter_spacing is not None:
        font["letterSpacing"] = letter_spacing
    element: dict[str, object] = {
        "id": str(uuid4()),
        "type": "text",
        "position": {"x": x, "y": y},
        "size": {"width": width, "height": height},
        "rotation": 0,
        "opacity": 1,
        "locked": False,
        "decorative": False,
        "runs": [{"text": text}],
        "font": font,
        "horizontalAlign": align,
        "verticalAlign": vertical_align,
    }
    if name:
        element["name"] = name
    return element


def _shape(
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    color: str,
    radius: int = 0,
    opacity: float = 1,
    shape: str = "rectangle",
    name: str | None = None,
) -> dict[str, object]:
    element: dict[str, object] = {
        "id": str(uuid4()),
        "type": "shape",
        "position": {"x": x, "y": y},
        "size": {"width": width, "height": height},
        "rotation": 0,
        "opacity": 1,
        "locked": False,
        "decorative": True,
        "shape": shape,
        "fill": {"color": color, "opacity": opacity},
        "cornerRadius": radius,
    }
    if name:
        element["name"] = name
    return element


def _body_font_size(text: str) -> int:
    if len(text) > 1_100:
        return 15
    if len(text) > 800:
        return 17
    if len(text) > 520:
        return 19
    if len(text) > 280:
        return 21
    return 24


def _title_font_size(title: str, preferred: int) -> int:
    if len(title) > 100:
        return max(28, preferred - 12)
    if len(title) > 65:
        return max(32, preferred - 7)
    return preferred


def _page_label(index: int, total: int) -> str:
    return f"{index:02d} / {total:02d}"


def _content_points(text: str, count: int) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return [""] * count
    parts = [
        part.strip().lstrip("•-*– ")
        for part in re.split(r"\n+|(?<=[.!?])\s+", cleaned)
        if part.strip().lstrip("•-*– ")
    ]
    if len(parts) < count:
        parts = _chunks(cleaned, count)
    if len(parts) > count:
        parts = [*parts[: count - 1], " ".join(parts[count - 1 :])]
    return (parts + [""] * count)[:count]


def _card_copy(text: str) -> tuple[str, str]:
    words = text.split()
    if len(words) <= 7:
        return text, ""
    return " ".join(words[:5]), " ".join(words[5:])


def _cover_slide(
    title: str,
    content: str,
    theme_id: str,
    colors: dict[str, str],
    fonts: dict[str, str],
) -> dict[str, object]:
    title_size = _title_font_size(title, 62)
    if theme_id == "warm-studio":
        background = colors["background"]
        elements = [
            _shape(x=1030, y=0, width=250, height=720, color=colors["primary"], name="Color field"),
            _shape(x=930, y=78, width=210, height=210, color=colors["accent"], opacity=0.9, shape="ellipse", name="Accent circle"),
            _text_element("01", x=82, y=72, width=100, height=44, size=18, color=colors["primary"], family=fonts["body"], bold=True, letter_spacing=2, name="Slide number"),
            _text_element(title, x=82, y=180, width=800, height=260, size=title_size, color=colors["text"], family=fonts["heading"], bold=True, line_height=1.04, name="Title"),
            _shape(x=82, y=486, width=92, height=6, color=colors["primary"], radius=3, name="Title rule"),
        ]
        if content:
            elements.append(_text_element(content, x=82, y=528, width=720, height=110, size=21, color=colors["muted"], family=fonts["body"], line_height=1.3, name="Subtitle"))
    elif theme_id == "midnight-signal":
        background = colors["secondary"]
        elements = [
            _shape(x=0, y=0, width=24, height=720, color=colors["primary"], name="Signal rail"),
            _shape(x=918, y=0, width=362, height=720, color=colors["surface"], name="Side field"),
            _shape(x=1010, y=86, width=176, height=176, color=colors["primary"], radius=24, name="Signal block"),
            _shape(x=1054, y=130, width=88, height=88, color=colors["accent"], radius=44, name="Signal core"),
            _text_element("01", x=82, y=74, width=100, height=40, size=17, color=colors["accent"], family=fonts["body"], bold=True, letter_spacing=2, name="Slide number"),
            _text_element(title, x=82, y=176, width=760, height=270, size=title_size, color=colors["text"], family=fonts["heading"], bold=True, line_height=1.02, name="Title"),
        ]
        if content:
            elements.append(_text_element(content, x=84, y=518, width=690, height=100, size=20, color=colors["muted"], family=fonts["body"], line_height=1.3, name="Subtitle"))
    else:
        background = colors["surface"]
        elements = [
            _shape(x=0, y=0, width=920, height=720, color=colors["secondary"], name="Editorial field"),
            _shape(x=80, y=76, width=10, height=568, color=colors["accent"], radius=5, name="Accent rail"),
            _text_element("01", x=124, y=76, width=100, height=40, size=17, color=colors["accent"], family=fonts["body"], bold=True, letter_spacing=2, name="Slide number"),
            _text_element(title, x=124, y=174, width=720, height=280, size=title_size, color="#FFFFFF", family=fonts["heading"], bold=True, line_height=1.02, name="Title"),
            _shape(x=1040, y=78, width=160, height=160, color=colors["primary"], radius=80, name="Cobalt marker"),
        ]
        if content:
            elements.append(_text_element(content, x=124, y=518, width=680, height=110, size=20, color="#C7D0DE", family=fonts["body"], line_height=1.3, name="Subtitle"))
    return {
        "id": str(uuid4()),
        "title": title,
        "background": background,
        "revision": 0,
        "elements": elements,
    }


def _content_slide(
    index: int,
    total: int,
    title: str,
    body: str,
    theme_id: str,
    colors: dict[str, str],
    fonts: dict[str, str],
) -> dict[str, object]:
    body_size = _body_font_size(body)
    title_size = _title_font_size(title, 42)
    orders = {
        "editorial-cobalt": ("header", "split", "statement", "margin", "band", "frame"),
        "warm-studio": ("margin", "frame", "header", "statement", "split", "band"),
        "midnight-signal": ("split", "band", "margin", "frame", "statement", "header"),
    }
    order = orders.get(theme_id, orders["editorial-cobalt"])
    if len(body) > 720:
        variant = "header"
    else:
        variant = order[(index - 1) % len(order)]
    label = _page_label(index + 1, total)
    light_background = colors["surface"] if theme_id != "midnight-signal" else colors["background"]
    light_text = colors["text"]

    if variant == "header":
        background = light_background
        elements = [
            _text_element(label, x=84, y=58, width=150, height=36, size=14, color=colors["primary"], family=fonts["body"], bold=True, letter_spacing=1.5, name="Page number"),
            _text_element(title, x=84, y=116, width=1070, height=118, size=title_size, color=light_text, family=fonts["heading"], bold=True, line_height=1.06, name="Title"),
            _shape(x=84, y=252, width=1110, height=2, color=colors["primary"], name="Header rule"),
            _shape(x=84, y=286, width=12, height=334, color=colors["accent"], radius=6, name="Accent rail"),
            _text_element(body, x=132, y=286, width=1010, height=350, size=body_size, color=light_text, family=fonts["body"], line_height=1.32, name="Body"),
        ]
    elif variant == "split":
        background = colors["background"]
        elements = [
            _shape(x=0, y=0, width=462, height=720, color=colors["primary"], name="Title field"),
            _text_element(label, x=62, y=58, width=150, height=36, size=14, color="#FFFFFF", family=fonts["body"], bold=True, letter_spacing=1.5, name="Page number"),
            _text_element(title, x=62, y=142, width=334, height=382, size=_title_font_size(title, 38), color="#FFFFFF", family=fonts["heading"], bold=True, line_height=1.08, name="Title"),
            _shape(x=62, y=610, width=92, height=6, color=colors["accent"], radius=3, name="Accent rule"),
            _text_element(body, x=526, y=104, width=660, height=510, size=body_size, color=light_text, family=fonts["body"], line_height=1.34, name="Body"),
        ]
    elif variant == "statement":
        background = colors["secondary"]
        elements = [
            _shape(x=84, y=70, width=78, height=8, color=colors["accent"], radius=4, name="Accent rule"),
            _text_element(label, x=1028, y=58, width=166, height=36, size=14, color=colors["muted"], family=fonts["body"], bold=True, align="right", letter_spacing=1.5, name="Page number"),
            _text_element(title, x=84, y=118, width=860, height=80, size=23, color=colors["accent"], family=fonts["body"], bold=True, name="Title"),
            _text_element(body, x=84, y=232, width=1060, height=350, size=min(38, body_size + 10), color="#FFFFFF", family=fonts["heading"], bold=True, line_height=1.14, vertical_align="middle", name="Statement"),
        ]
    elif variant == "margin":
        background = colors["background"]
        elements = [
            _text_element(str(index + 1).zfill(2), x=852, y=42, width=350, height=220, size=150, color=colors["accent"], family=fonts["heading"], bold=True, align="right", line_height=1, name="Large page number"),
            _text_element(title, x=82, y=96, width=680, height=150, size=title_size, color=light_text, family=fonts["heading"], bold=True, line_height=1.06, name="Title"),
            _shape(x=82, y=278, width=270, height=3, color=colors["primary"], name="Title rule"),
            _text_element(body, x=370, y=316, width=790, height=318, size=body_size, color=light_text, family=fonts["body"], line_height=1.34, name="Body"),
        ]
    elif variant == "band":
        background = light_background
        elements = [
            _shape(x=0, y=0, width=1280, height=286, color=colors["primary"], name="Title band"),
            _text_element(label, x=84, y=52, width=150, height=36, size=14, color="#FFFFFF", family=fonts["body"], bold=True, letter_spacing=1.5, name="Page number"),
            _text_element(title, x=84, y=112, width=1080, height=120, size=title_size, color="#FFFFFF", family=fonts["heading"], bold=True, line_height=1.06, name="Title"),
            _text_element(body, x=130, y=348, width=1020, height=292, size=body_size, color=light_text, family=fonts["body"], line_height=1.34, name="Body"),
        ]
    else:
        background = colors["background"]
        elements = [
            _shape(x=58, y=48, width=1164, height=3, color=colors["primary"], name="Top frame"),
            _shape(x=58, y=669, width=1164, height=3, color=colors["primary"], name="Bottom frame"),
            _shape(x=58, y=48, width=3, height=624, color=colors["primary"], name="Left frame"),
            _shape(x=1219, y=48, width=3, height=624, color=colors["primary"], name="Right frame"),
            _text_element(label, x=92, y=78, width=150, height=36, size=14, color=colors["primary"], family=fonts["body"], bold=True, letter_spacing=1.5, name="Page number"),
            _text_element(title, x=92, y=148, width=470, height=300, size=title_size, color=light_text, family=fonts["heading"], bold=True, line_height=1.06, name="Title"),
            _shape(x=622, y=146, width=4, height=430, color=colors["accent"], radius=2, name="Divider"),
            _text_element(body, x=680, y=148, width=448, height=430, size=body_size, color=light_text, family=fonts["body"], line_height=1.34, name="Body"),
        ]
    return {
        "id": str(uuid4()),
        "title": title,
        "background": background,
        "revision": 0,
        "elements": elements,
    }


class NativeContentGenerator:
    """Renders compatibility themes using product-owned native layout archetypes."""

    name = "native"

    def render(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: Mapping[tuple[int, str], str],
    ) -> dict[str, object]:
        del assets  # native layouts do not support auto asset injection yet
        theme = get_theme(request.theme_id)
        colors = theme["colors"]
        fonts = theme["fonts"]
        if not isinstance(colors, dict) or not isinstance(fonts, dict):
            raise ValueError("Theme configuration is invalid")
        palette = {key: str(value) for key, value in colors.items()}
        typography = {key: str(value) for key, value in fonts.items()}
        items = outline.items
        title_item = items[0] if items else StoryOutlineItem(id=str(uuid4()), title=request.title, content="")
        slides = [
            _cover_slide(
                title_item.title,
                title_item.content,
                str(theme["id"]),
                palette,
                typography,
            )
        ]
        for index, item in enumerate(items[1:], start=1):
            slides.append(
                _content_slide(
                    index,
                    len(items),
                    item.title or f"Key point {index}",
                    item.content,
                    str(theme["id"]),
                    palette,
                    typography,
                )
            )
        return {
            "id": str(request.presentation_id),
            "schemaVersion": 1,
            "title": request.title,
            "language": request.language,
            "revision": 0,
            "theme": theme,
            "slides": slides,
        }
