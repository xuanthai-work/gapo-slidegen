import math
from uuid import UUID


class InvalidPresentationDocument(ValueError):
    pass


ALLOWED_ELEMENT_TYPES = {
    "text",
    "text-list",
    "image",
    "shape",
    "line",
    "table",
    "chart",
    "svg",
    "group",
    "container",
    "flex",
    "grid",
}


def _validate_element(element: object, *, depth: int = 0) -> None:
    if depth > 20 or not isinstance(element, dict):
        raise InvalidPresentationDocument("Invalid or excessively nested slide element.")
    if not isinstance(element.get("id"), str) or not element["id"]:
        raise InvalidPresentationDocument("Every slide element requires a stable id.")
    if element.get("type") not in ALLOWED_ELEMENT_TYPES:
        raise InvalidPresentationDocument(f"Unsupported slide element type: {element.get('type')!r}.")
    for key in ("position", "size"):
        value = element.get(key)
        if not isinstance(value, dict):
            raise InvalidPresentationDocument(f"Element {element['id']} requires {key}.")
        for coordinate in value.values():
            if not isinstance(coordinate, (int, float)) or not math.isfinite(coordinate):
                raise InvalidPresentationDocument(f"Element {element['id']} has invalid geometry.")
    size = element["size"]
    if size.get("width", -1) < 0 or size.get("height", -1) < 0:
        raise InvalidPresentationDocument(f"Element {element['id']} has a negative size.")

    children = element.get("children")
    if children is not None:
        if not isinstance(children, list):
            raise InvalidPresentationDocument(f"Element {element['id']} has invalid children.")
        for child in children:
            _validate_element(child, depth=depth + 1)
    child = element.get("child")
    if child is not None:
        _validate_element(child, depth=depth + 1)


def validate_presentation_document(document: dict[str, object], presentation_id: UUID) -> None:
    if document.get("id") != str(presentation_id):
        raise InvalidPresentationDocument("Document id does not match the presentation id.")
    if document.get("schemaVersion") != 1:
        raise InvalidPresentationDocument("Unsupported presentation schema version.")
    title = document.get("title")
    if not isinstance(title, str) or not title.strip() or len(title) > 500:
        raise InvalidPresentationDocument("Presentation title is invalid.")
    slides = document.get("slides")
    if not isinstance(slides, list) or not slides or len(slides) > 30:
        raise InvalidPresentationDocument("A presentation must contain between 1 and 30 slides.")

    slide_ids: set[str] = set()
    for slide in slides:
        if not isinstance(slide, dict) or not isinstance(slide.get("id"), str):
            raise InvalidPresentationDocument("Every slide requires a stable id.")
        if slide["id"] in slide_ids:
            raise InvalidPresentationDocument("Slide ids must be unique.")
        slide_ids.add(slide["id"])
        elements = slide.get("elements")
        if not isinstance(elements, list):
            raise InvalidPresentationDocument(f"Slide {slide['id']} requires an element list.")
        element_ids: set[str] = set()
        for element in elements:
            _validate_element(element)
            element_id = element["id"]
            if element_id in element_ids:
                raise InvalidPresentationDocument(f"Element ids must be unique within slide {slide['id']}.")
            element_ids.add(element_id)
