import re
from uuid import uuid4

from .provider import (
    GenerationRequest,
    OutlineRequest,
    ProviderConfigurationError,
    RewriteRequest,
    RewriteTextItem,
    SlideRewriteRequest,
)
from .presenton_template import MODERN_CONTENT_LAYOUT_IDS, PresentonTemplateAdapter
from .themes import get_theme


def _chunks(text: str, count: int) -> list[str]:
    if count <= 0:
        return []
    words = text.split()
    if not words:
        return [""] * count
    size = max(1, (len(words) + count - 1) // count)
    chunks = [" ".join(words[index : index + size]) for index in range(0, len(words), size)]
    return (chunks + [""] * count)[:count]


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


class StubPresentationProvider:
    """Deterministic local provider and native editable layout renderer."""

    name = "stub"

    def rewrite_text(self, request: RewriteRequest) -> str:
        raise ProviderConfigurationError(
            "AI rewrite is unavailable with the local stub provider. Configure an AI provider first."
        )

    def rewrite_slide(self, request: SlideRewriteRequest) -> list[RewriteTextItem]:
        raise ProviderConfigurationError(
            "AI rewrite is unavailable with the local stub provider. Configure an AI provider first."
        )

    def generate_outline(self, request: OutlineRequest) -> list[dict[str, object]]:
        content_count = max(0, request.slide_count - 1)
        section_texts = [
            str(section.get("text", "")).strip() for section in request.sections if section.get("text")
        ]
        bodies = section_texts[:content_count]
        if len(bodies) < content_count:
            bodies.extend(_chunks(request.text, content_count - len(bodies)))
        items: list[dict[str, object]] = [
            {"id": str(uuid4()), "title": request.title, "content": ""}
        ]
        for index, body in enumerate(bodies, start=1):
            section = request.sections[index - 1] if index - 1 < len(request.sections) else {}
            items.append(
                {
                    "id": str(uuid4()),
                    "title": str(section.get("title") or f"Key point {index}"),
                    "content": body,
                }
            )
        return items

    def _cover_slide(
        self,
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

    def _modern_cover_slide(
        self,
        title: str,
        content: str,
        colors: dict[str, str],
        fonts: dict[str, str],
    ) -> dict[str, object]:
        """Adapted from Presenton Modern `title_slide` at the pinned revision."""
        title_size = _title_font_size(title, 48)
        elements = [
            _text_element(title, x=40, y=204, width=578, height=130, size=title_size, color=colors["primary"], family=fonts["heading"], bold=True, line_height=1, name="primary_heading"),
            _shape(x=40, y=350, width=137, height=4, color=colors["primary"], radius=1, name="accent_rule"),
            _text_element(content, x=40, y=376, width=578, height=150, size=18, color=colors["text"], family=fonts["body"], line_height=1.3, name="supporting_paragraph"),
            _shape(x=702, y=64, width=538, height=592, color=colors["surface"], radius=4, name="main_visual_panel"),
            _shape(x=750, y=112, width=394, height=10, color=colors["primary"], radius=5, name="visual_rule"),
            _text_element("01", x=750, y=164, width=394, height=180, size=138, color=colors["primary"], family=fonts["heading"], bold=True, line_height=1, name="visual_index"),
            _text_element(title, x=754, y=470, width=390, height=110, size=22, color=colors["secondary"], family=fonts["body"], bold=True, line_height=1.15, name="visual_caption"),
        ]
        return {
            "id": str(uuid4()),
            "title": title,
            "background": colors["background"],
            "revision": 0,
            "elements": elements,
        }

    def _modern_content_slide(
        self,
        index: int,
        total: int,
        title: str,
        body: str,
        colors: dict[str, str],
        fonts: dict[str, str],
    ) -> dict[str, object]:
        """Canonical adaptations of the Presenton Modern content layouts."""
        variant = (index - 1) % 4
        title_size = _title_font_size(title, 46)
        elements: list[dict[str, object]] = [
            _shape(x=2, y=714, width=1276, height=4, color=colors["primary"], name="bottom_accent"),
            _text_element(_page_label(index + 1, total), x=1080, y=38, width=130, height=28, size=12, color=colors["muted"], family=fonts["body"], align="right", letter_spacing=1, name="page_number"),
        ]

        if variant in {0, 1}:
            points = _content_points(body, 5)
            elements.extend([
                _text_element(title, x=66, y=150, width=508, height=112, size=title_size, color=colors["primary"], family=fonts["heading"], bold=True, line_height=1, name="large_heading"),
                _text_element(points[0], x=67, y=286, width=512, height=190, size=18, color=colors["text"], family=fonts["body"], line_height=1.3, name="supporting_paragraph"),
            ])
            if variant == 0:
                positions = ((648, 82), (935, 82), (648, 298), (935, 298))
                for point_index, ((x, y), point) in enumerate(zip(positions, points[1:]), start=1):
                    heading, caption = _card_copy(point)
                    elements.extend([
                        _shape(x=x, y=y, width=275, height=190, color=colors["surface"], radius=12, name=f"feature_card_{point_index}"),
                        _shape(x=x + 24, y=y + 22, width=38, height=38, color=colors["primary"], radius=8, name=f"feature_marker_{point_index}"),
                        _text_element(str(point_index).zfill(2), x=x + 24, y=y + 29, width=38, height=22, size=12, color=colors["background"], family=fonts["body"], bold=True, align="center", name=f"feature_number_{point_index}"),
                        _text_element(heading, x=x + 24, y=y + 78, width=227, height=44, size=17, color=colors["secondary"], family=fonts["heading"], bold=True, line_height=1.1, name=f"card_title_{point_index}"),
                        _text_element(caption, x=x + 24, y=y + 126, width=227, height=48, size=11, color=colors["text"], family=fonts["body"], line_height=1.2, name=f"card_caption_{point_index}"),
                    ])
            else:
                for point_index, point in enumerate(points[1:], start=1):
                    heading, caption = _card_copy(point)
                    y = 74 + (point_index - 1) * 142
                    elements.extend([
                        _shape(x=648, y=y, width=562, height=124, color=colors["surface"], radius=12, name=f"list_card_{point_index}"),
                        _text_element(str(point_index).zfill(2), x=674, y=y + 28, width=54, height=28, size=17, color=colors["primary"], family=fonts["heading"], bold=True, name=f"list_number_{point_index}"),
                        _text_element(heading, x=744, y=y + 23, width=420, height=34, size=18, color=colors["secondary"], family=fonts["heading"], bold=True, name=f"list_title_{point_index}"),
                        _text_element(caption, x=744, y=y + 61, width=420, height=48, size=12, color=colors["text"], family=fonts["body"], line_height=1.2, name=f"list_caption_{point_index}"),
                    ])
        elif variant == 2:
            points = _content_points(body, 3)
            elements.append(_text_element(title, x=66, y=72, width=1090, height=92, size=title_size, color=colors["primary"], family=fonts["heading"], bold=True, line_height=1, name="large_heading"))
            for point_index, point in enumerate(points, start=1):
                heading, caption = _card_copy(point)
                x = 66 + (point_index - 1) * 386
                elements.extend([
                    _shape(x=x, y=208, width=354, height=390, color=colors["surface"], radius=14, name=f"profile_card_{point_index}"),
                    _text_element(str(point_index).zfill(2), x=x + 28, y=238, width=100, height=84, size=62, color=colors["primary"], family=fonts["heading"], bold=True, line_height=1, name=f"profile_number_{point_index}"),
                    _shape(x=x + 28, y=342, width=88, height=4, color=colors["primary"], radius=2, name=f"profile_rule_{point_index}"),
                    _text_element(heading, x=x + 28, y=380, width=298, height=70, size=22, color=colors["secondary"], family=fonts["heading"], bold=True, line_height=1.1, name=f"profile_title_{point_index}"),
                    _text_element(caption, x=x + 28, y=472, width=298, height=92, size=13, color=colors["text"], family=fonts["body"], line_height=1.25, name=f"profile_caption_{point_index}"),
                ])
        else:
            points = _content_points(body, 4)
            elements.extend([
                _text_element(title, x=66, y=82, width=520, height=170, size=title_size, color=colors["primary"], family=fonts["heading"], bold=True, line_height=1, name="large_heading"),
                _shape(x=66, y=282, width=508, height=290, color=colors["primary"], radius=8, name="highlight_panel"),
                _text_element(points[0], x=98, y=322, width=444, height=210, size=28, color=colors["background"], family=fonts["heading"], bold=True, line_height=1.18, vertical_align="middle", name="highlighted_text"),
            ])
            for point_index, point in enumerate(points[1:], start=1):
                heading, caption = _card_copy(point)
                y = 102 + (point_index - 1) * 174
                elements.extend([
                    _text_element(str(point_index).zfill(2), x=666, y=y, width=72, height=42, size=28, color=colors["primary"], family=fonts["heading"], bold=True, name=f"summary_number_{point_index}"),
                    _text_element(heading, x=758, y=y, width=410, height=42, size=20, color=colors["secondary"], family=fonts["heading"], bold=True, name=f"summary_title_{point_index}"),
                    _text_element(caption, x=758, y=y + 52, width=410, height=84, size=13, color=colors["text"], family=fonts["body"], line_height=1.25, name=f"summary_caption_{point_index}"),
                ])

        return {
            "id": str(uuid4()),
            "title": title,
            "background": colors["background"],
            "revision": 0,
            "elements": elements,
        }

    def _content_slide(
        self,
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

    def generate(self, request: GenerationRequest) -> dict[str, object]:
        outline = request.outline or self.generate_outline(
            OutlineRequest(
                title=request.title,
                text=request.text,
                sections=request.sections,
                language=request.language,
                slide_count=request.slide_count,
                source_kind=request.source_kind,
            )
        )
        theme = get_theme(request.theme_id)
        colors = theme["colors"]
        fonts = theme["fonts"]
        if not isinstance(colors, dict) or not isinstance(fonts, dict):
            raise ValueError("Theme configuration is invalid")
        palette = {key: str(value) for key, value in colors.items()}
        typography = {key: str(value) for key, value in fonts.items()}
        title_item = outline[0] if outline else {"title": request.title, "content": ""}
        if theme["id"] == "modern-blue":
            adapter = PresentonTemplateAdapter()
            slides = [
                adapter.compile_slide(
                    "title_slide",
                    title=str(title_item.get("title") or request.title),
                    content=str(title_item.get("content") or ""),
                    slide_index=0,
                    slide_count=len(outline),
                )
            ]
            for index, item in enumerate(outline[1:], start=1):
                slides.append(
                    adapter.compile_slide(
                        MODERN_CONTENT_LAYOUT_IDS[(index - 1) % len(MODERN_CONTENT_LAYOUT_IDS)],
                        title=str(item.get("title") or f"Key point {index}"),
                        content=str(item.get("content") or ""),
                        slide_index=index,
                        slide_count=len(outline),
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
        slides = [
            self._cover_slide(
                str(title_item.get("title") or request.title),
                str(title_item.get("content") or ""),
                str(theme["id"]),
                palette,
                typography,
            )
        ]
        for index, item in enumerate(outline[1:], start=1):
            slides.append(
                self._content_slide(
                    index,
                    len(outline),
                    str(item.get("title") or f"Key point {index}"),
                    str(item.get("content") or ""),
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
