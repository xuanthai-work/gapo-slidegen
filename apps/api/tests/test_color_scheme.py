from app.generation.themes import apply_color_scheme, get_theme


def _luminance(color: str) -> float:
    value = color.lstrip("#")
    red = int(value[0:2], 16) / 255
    green = int(value[2:4], 16) / 255
    blue = int(value[4:6], 16) / 255
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast(a: str, b: str) -> float:
    light, dark = max(_luminance(a), _luminance(b)), min(_luminance(a), _luminance(b))
    return (light + 0.05) / (dark + 0.05)


def _text(name: str, color: str, x: float, y: float, width: float = 360, height: float = 80) -> dict:
    return {
        "type": "text",
        "name": name,
        "position": {"x": x, "y": y},
        "size": {"width": width, "height": height},
        "font": {"color": color, "family": "Montserrat", "size": 28, "bold": True},
        "runs": [{"text": name}],
    }


def _shape(color: str, x: float, y: float, width: float, height: float) -> dict:
    return {
        "type": "shape",
        "shape": "rectangle",
        "position": {"x": x, "y": y},
        "size": {"width": width, "height": height},
        "fill": {"color": color, "opacity": 1},
    }


def test_light_template_text_does_not_stay_white_on_a_light_scheme() -> None:
    theme = get_theme("modern:professional-blue")
    slide = apply_color_scheme(
        {
            "background": "#FFFFFF",
            "elements": [
                _text("Cover title", "#FFFFFF", 48, 80),
                _shape("#111111", 720, 80, 480, 240),
                _text("On dark panel", "#FFFFFF", 740, 100, 440, 80),
            ],
        },
        theme,
    )

    title = next(element for element in slide["elements"] if element.get("name") == "Cover title")
    on_panel = next(element for element in slide["elements"] if element.get("name") == "On dark panel")
    panel = next(element for element in slide["elements"] if element.get("type") == "shape")

    assert _contrast(title["font"]["color"], slide["background"]) >= 4.5
    assert _contrast(on_panel["font"]["color"], panel["fill"]["color"]) >= 4.5


def test_dark_scheme_keeps_light_text_on_the_canvas() -> None:
    theme = get_theme("dynamic:professional-dark")
    slide = apply_color_scheme(
        {
            "background": "#FFFFFF",
            "elements": [_text("Cover title", "#FFFFFF", 48, 80)],
        },
        theme,
    )

    title = slide["elements"][0]
    assert _contrast(title["font"]["color"], slide["background"]) >= 4.5
