from uuid import uuid4

from app.generation.presenton_template import PresentonTemplateAdapter


def test_image_slot_becomes_icon_fallback_without_asset() -> None:
    adapter = PresentonTemplateAdapter()
    slide = adapter.compile_slide(
        "title_description_image",
        title="Architecture",
        content="System overview.",
        slide_index=1,
        slide_count=2,
        role="solution",
    )
    image_elements = [
        element for element in slide["elements"] if str(element.get("name", "")) == "left_media_image"
    ]
    assert len(image_elements) == 1
    assert image_elements[0]["type"] == "svg"
    assert "<svg" in str(image_elements[0]["svg"])


def test_image_slot_becomes_canonical_image_with_asset() -> None:
    adapter = PresentonTemplateAdapter()
    asset_id = str(uuid4())
    slide = adapter.compile_slide(
        "title_description_image",
        title="Architecture",
        content="System overview.",
        slide_index=1,
        slide_count=2,
        assets={"left_media_image": asset_id},
    )
    image_elements = [
        element for element in slide["elements"] if str(element.get("name", "")) == "left_media_image"
    ]
    assert len(image_elements) == 1
    element = image_elements[0]
    assert element["type"] == "image"
    assert element["assetId"] == asset_id
    assert element["fit"] == "cover"
    assert 0 <= element["focusX"] <= 1
    assert 0 <= element["focusY"] <= 1
    assert element["size"]["width"] > 0
    assert element["size"]["height"] > 0


def test_unmatched_image_slots_use_icon_fallback() -> None:
    adapter = PresentonTemplateAdapter()
    slide = adapter.compile_slide(
        "title_description_image",
        title="Architecture",
        content="System overview.",
        slide_index=1,
        slide_count=2,
        assets={"other_slot": str(uuid4())},
        role="solution",
    )
    image_elements = [
        element for element in slide["elements"] if str(element.get("name", "")) == "left_media_image"
    ]
    assert image_elements[0]["type"] == "svg"
