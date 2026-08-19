from uuid import uuid4

from .registry import (
    ContentConstraints,
    NativeLayoutContext,
    NativeLayoutDefinition,
    NativeLayoutRegistry,
)


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
    decorative: bool = False,
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
        "decorative": decorative,
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


def _slide(
    context: NativeLayoutContext,
    *,
    background: str,
    elements: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "id": str(uuid4()),
        "title": context.title,
        "background": background,
        "revision": 0,
        "elements": elements,
    }


def _cover_warm(context: NativeLayoutContext) -> dict[str, object]:
    colors, fonts = context.colors, context.fonts
    elements = [
        _shape(x=1030, y=0, width=250, height=720, color=colors["primary"], name="Color field"),
        _shape(x=930, y=78, width=210, height=210, color=colors["accent"], opacity=0.9, shape="ellipse", name="Accent circle"),
        _text_element("01", x=82, y=72, width=100, height=44, size=18, color=colors["primary"], family=fonts["body"], bold=True, letter_spacing=2, name="Slide number"),
        _text_element(context.title, x=82, y=180, width=800, height=260, size=_title_font_size(context.title, 62), color=colors["text"], family=fonts["heading"], bold=True, line_height=1.04, name="Title"),
        _shape(x=82, y=486, width=92, height=6, color=colors["primary"], radius=3, name="Title rule"),
    ]
    if context.body:
        elements.append(_text_element(context.body, x=82, y=528, width=720, height=110, size=21, color=colors["muted"], family=fonts["body"], line_height=1.3, name="Subtitle"))
    return _slide(context, background=colors["background"], elements=elements)


def _cover_midnight(context: NativeLayoutContext) -> dict[str, object]:
    colors, fonts = context.colors, context.fonts
    elements = [
        _shape(x=0, y=0, width=24, height=720, color=colors["primary"], name="Signal rail"),
        _shape(x=918, y=0, width=362, height=720, color=colors["surface"], name="Side field"),
        _shape(x=1010, y=86, width=176, height=176, color=colors["primary"], radius=24, name="Signal block"),
        _shape(x=1054, y=130, width=88, height=88, color=colors["accent"], radius=44, name="Signal core"),
        _text_element("01", x=82, y=74, width=100, height=40, size=17, color=colors["accent"], family=fonts["body"], bold=True, letter_spacing=2, name="Slide number"),
        _text_element(context.title, x=82, y=176, width=760, height=270, size=_title_font_size(context.title, 62), color=colors["text"], family=fonts["heading"], bold=True, line_height=1.02, name="Title"),
    ]
    if context.body:
        elements.append(_text_element(context.body, x=84, y=518, width=690, height=100, size=20, color=colors["muted"], family=fonts["body"], line_height=1.3, name="Subtitle"))
    return _slide(context, background=colors["secondary"], elements=elements)


def _cover_editorial(context: NativeLayoutContext) -> dict[str, object]:
    colors, fonts = context.colors, context.fonts
    elements = [
        _shape(x=0, y=0, width=920, height=720, color=colors["secondary"], name="Editorial field"),
        _shape(x=80, y=76, width=10, height=568, color=colors["accent"], radius=5, name="Accent rail"),
        _text_element("01", x=124, y=76, width=100, height=40, size=17, color=colors["accent"], family=fonts["body"], bold=True, letter_spacing=2, name="Slide number"),
        _text_element(context.title, x=124, y=174, width=720, height=280, size=_title_font_size(context.title, 62), color="#FFFFFF", family=fonts["heading"], bold=True, line_height=1.02, name="Title"),
        _shape(x=1040, y=78, width=160, height=160, color=colors["primary"], radius=80, name="Cobalt marker"),
    ]
    if context.body:
        elements.append(_text_element(context.body, x=124, y=518, width=680, height=110, size=20, color="#C7D0DE", family=fonts["body"], line_height=1.3, name="Subtitle"))
    return _slide(context, background=colors["surface"], elements=elements)


def _content_header(context: NativeLayoutContext) -> dict[str, object]:
    colors, fonts = context.colors, context.fonts
    text_color = colors["text"]
    elements = [
        _text_element(_page_label(context), x=84, y=58, width=150, height=36, size=14, color=colors["primary"], family=fonts["body"], bold=True, letter_spacing=1.5, name="Page number"),
        _text_element(context.title, x=84, y=116, width=1070, height=118, size=_title_font_size(context.title, 42), color=text_color, family=fonts["heading"], bold=True, line_height=1.06, name="Title"),
        _shape(x=84, y=252, width=1110, height=2, color=colors["primary"], name="Header rule"),
        _shape(x=84, y=286, width=12, height=334, color=colors["accent"], radius=6, name="Accent rail"),
        _text_element(context.body, x=132, y=286, width=1010, height=350, size=_body_font_size(context.body), color=text_color, family=fonts["body"], line_height=1.32, name="Body"),
    ]
    for block_index, block in enumerate(context.blocks[:3]):
        heading = str(block.get("heading") or "").strip()
        body = str(block.get("body") or "").strip()
        y_base = 286 + (block_index + 1) * 110
        if heading:
            elements.append(_text_element(heading, x=132, y=y_base, width=1010, height=28, size=18, color=text_color, family=fonts["heading"], bold=True, line_height=1.1, name=f"Block {block_index + 1} heading"))
        if body:
            elements.append(_text_element(body, x=132, y=y_base + 30, width=1010, height=70, size=16, color=text_color, family=fonts["body"], line_height=1.2, name=f"Block {block_index + 1} body"))
    background = colors["background"] if context.theme_id == "midnight-signal" else colors["surface"]
    return _slide(context, background=background, elements=elements)


def _content_split(context: NativeLayoutContext) -> dict[str, object]:
    colors, fonts = context.colors, context.fonts
    elements = [
        _shape(x=0, y=0, width=462, height=720, color=colors["primary"], name="Title field"),
        _text_element(_page_label(context), x=62, y=58, width=150, height=36, size=14, color="#FFFFFF", family=fonts["body"], bold=True, letter_spacing=1.5, name="Page number"),
        _text_element(context.title, x=62, y=142, width=334, height=382, size=_title_font_size(context.title, 38), color="#FFFFFF", family=fonts["heading"], bold=True, line_height=1.08, name="Title"),
        _shape(x=62, y=610, width=92, height=6, color=colors["accent"], radius=3, name="Accent rule"),
        _text_element(context.body, x=526, y=104, width=660, height=510, size=_body_font_size(context.body), color=colors["text"], family=fonts["body"], line_height=1.34, name="Body"),
    ]
    return _slide(context, background=colors["background"], elements=elements)


def _content_statement(context: NativeLayoutContext) -> dict[str, object]:
    colors, fonts = context.colors, context.fonts
    elements = [
        _shape(x=84, y=70, width=78, height=8, color=colors["accent"], radius=4, name="Accent rule"),
        _text_element(_page_label(context), x=1028, y=58, width=166, height=36, size=14, color=colors["muted"], family=fonts["body"], bold=True, align="right", letter_spacing=1.5, name="Page number"),
        _text_element(context.title, x=84, y=118, width=860, height=80, size=23, color=colors["accent"], family=fonts["body"], bold=True, name="Title"),
        _text_element(context.body, x=84, y=232, width=1060, height=350, size=min(38, _body_font_size(context.body) + 10), color="#FFFFFF", family=fonts["heading"], bold=True, line_height=1.14, vertical_align="middle", name="Statement"),
    ]
    return _slide(context, background=colors["secondary"], elements=elements)


def _content_margin(context: NativeLayoutContext) -> dict[str, object]:
    colors, fonts = context.colors, context.fonts
    elements = [
        _text_element(str(context.index + 1).zfill(2), x=852, y=42, width=350, height=220, size=150, color=colors["accent"], family=fonts["heading"], bold=True, align="right", line_height=1, name="Large page number"),
        _text_element(context.title, x=82, y=96, width=680, height=150, size=_title_font_size(context.title, 42), color=colors["text"], family=fonts["heading"], bold=True, line_height=1.06, name="Title"),
        _shape(x=82, y=278, width=270, height=3, color=colors["primary"], name="Title rule"),
        _text_element(context.body, x=370, y=316, width=790, height=318, size=_body_font_size(context.body), color=colors["text"], family=fonts["body"], line_height=1.34, name="Body"),
    ]
    return _slide(context, background=colors["background"], elements=elements)


def _content_band(context: NativeLayoutContext) -> dict[str, object]:
    colors, fonts = context.colors, context.fonts
    elements = [
        _shape(x=0, y=0, width=1280, height=286, color=colors["primary"], name="Title band"),
        _text_element(_page_label(context), x=84, y=52, width=150, height=36, size=14, color="#FFFFFF", family=fonts["body"], bold=True, letter_spacing=1.5, name="Page number"),
        _text_element(context.title, x=84, y=112, width=1080, height=120, size=_title_font_size(context.title, 42), color="#FFFFFF", family=fonts["heading"], bold=True, line_height=1.06, name="Title"),
        _text_element(context.body, x=130, y=348, width=1020, height=292, size=_body_font_size(context.body), color=colors["text"], family=fonts["body"], line_height=1.34, name="Body"),
    ]
    background = colors["background"] if context.theme_id == "midnight-signal" else colors["surface"]
    return _slide(context, background=background, elements=elements)


def _content_frame(context: NativeLayoutContext) -> dict[str, object]:
    colors, fonts = context.colors, context.fonts
    elements = [
        _shape(x=58, y=48, width=1164, height=3, color=colors["primary"], name="Top frame"),
        _shape(x=58, y=669, width=1164, height=3, color=colors["primary"], name="Bottom frame"),
        _shape(x=58, y=48, width=3, height=624, color=colors["primary"], name="Left frame"),
        _shape(x=1219, y=48, width=3, height=624, color=colors["primary"], name="Right frame"),
        _text_element(_page_label(context), x=92, y=78, width=150, height=36, size=14, color=colors["primary"], family=fonts["body"], bold=True, letter_spacing=1.5, name="Page number"),
        _text_element(context.title, x=92, y=148, width=470, height=300, size=_title_font_size(context.title, 42), color=colors["text"], family=fonts["heading"], bold=True, line_height=1.06, name="Title"),
        _shape(x=622, y=146, width=4, height=430, color=colors["accent"], radius=2, name="Divider"),
        _text_element(context.body, x=680, y=148, width=448, height=430, size=_body_font_size(context.body), color=colors["text"], family=fonts["body"], line_height=1.34, name="Body"),
    ]
    return _slide(context, background=colors["background"], elements=elements)


def _page_label(context: NativeLayoutContext) -> str:
    return f"{context.index + 1:02d} / {context.total:02d}"


def build_native_layout_registry() -> NativeLayoutRegistry:
    registry = NativeLayoutRegistry()
    for definition in (
        NativeLayoutDefinition(
            "cover-editorial",
            ContentConstraints(72, 130, 55, 120, 0),
            _cover_editorial,
        ),
        NativeLayoutDefinition(
            "cover-midnight",
            ContentConstraints(72, 130, 55, 120, 0),
            _cover_midnight,
        ),
        NativeLayoutDefinition(
            "cover-warm",
            ContentConstraints(72, 130, 55, 120, 0),
            _cover_warm,
        ),
        NativeLayoutDefinition(
            "content-band",
            ContentConstraints(80, 300, 55, 120, 0),
            _content_band,
        ),
        NativeLayoutDefinition(
            "content-frame",
            ContentConstraints(80, 320, 55, 120, 0),
            _content_frame,
        ),
        NativeLayoutDefinition(
            "content-header",
            ContentConstraints(80, 500, 55, 120, 3),
            _content_header,
        ),
        NativeLayoutDefinition(
            "content-margin",
            ContentConstraints(80, 360, 55, 120, 0),
            _content_margin,
        ),
        NativeLayoutDefinition(
            "content-split",
            ContentConstraints(72, 400, 55, 120, 0),
            _content_split,
        ),
        NativeLayoutDefinition(
            "content-statement",
            ContentConstraints(64, 220, 42, 72, 0),
            _content_statement,
        ),
    ):
        registry.register(definition)
    return registry
