from uuid import uuid4

from .provider import GenerationRequest


def _chunks(text: str, count: int) -> list[str]:
    if count <= 0:
        return []
    words = text.split()
    if not words:
        return [""] * count
    size = max(1, (len(words) + count - 1) // count)
    chunks = [" ".join(words[index : index + size]) for index in range(0, len(words), size)]
    return (chunks + [""] * count)[:count]


def _text_element(text: str, *, y: int, height: int, size: int, bold: bool = False) -> dict[str, object]:
    return {
        "id": str(uuid4()),
        "type": "text",
        "position": {"x": 96, "y": y},
        "size": {"width": 1088, "height": height},
        "rotation": 0,
        "opacity": 1,
        "locked": False,
        "decorative": False,
        "runs": [{"text": text}],
        "font": {"family": "Arial", "size": size, "color": "#172033", "bold": bold},
        "horizontalAlign": "left",
        "verticalAlign": "top",
    }


class StubPresentationProvider:
    """Deterministic local provider used to exercise the pipeline without external data transfer."""

    name = "stub"

    def generate(self, request: GenerationRequest) -> dict[str, object]:
        content_count = max(0, request.slide_count - 1)
        section_texts = [
            str(section.get("text", "")).strip() for section in request.sections if section.get("text")
        ]
        bodies = section_texts[:content_count]
        if len(bodies) < content_count:
            remaining = _chunks(request.text, content_count - len(bodies))
            bodies.extend(remaining)

        slides: list[dict[str, object]] = [
            {
                "id": str(uuid4()),
                "title": request.title,
                "background": "#FFFFFF",
                "revision": 0,
                "elements": [
                    _text_element(request.title, y=145, height=190, size=56, bold=True),
                    {
                        "id": str(uuid4()),
                        "type": "shape",
                        "position": {"x": 96, "y": 380},
                        "size": {"width": 300, "height": 14},
                        "rotation": 0,
                        "opacity": 1,
                        "locked": False,
                        "decorative": True,
                        "shape": "rectangle",
                        "fill": {"color": "#285FC7", "opacity": 1},
                        "cornerRadius": 7,
                    },
                ],
            }
        ]
        for index, body in enumerate(bodies, start=1):
            section = request.sections[index - 1] if index - 1 < len(request.sections) else {}
            heading = str(section.get("title") or f"Key point {index}")
            slides.append(
                {
                    "id": str(uuid4()),
                    "title": heading,
                    "background": "#F7F9FC",
                    "revision": 0,
                    "elements": [
                        _text_element(heading, y=76, height=90, size=34, bold=True),
                        _text_element(body, y=190, height=390, size=22),
                    ],
                }
            )

        return {
            "id": str(request.presentation_id),
            "schemaVersion": 1,
            "title": request.title,
            "language": request.language,
            "revision": 0,
            "theme": {
                "id": "editorial-cobalt",
                "name": "Editorial cobalt",
                "colors": {
                    "background": "#F4F6F9",
                    "surface": "#FFFFFF",
                    "primary": "#285FC7",
                    "secondary": "#172033",
                    "accent": "#285FC7",
                    "text": "#172033",
                    "muted": "#778296",
                },
                "fonts": {"heading": "Arial", "body": "Arial"},
            },
            "slides": slides,
        }
