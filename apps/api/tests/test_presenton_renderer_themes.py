from uuid import uuid4

from app.generation.provider import GenerationRequest
from app.generation.presenton_template import PresentonTemplateAdapter
from app.generation.stages.content_generator import build_content_generator
from app.generation.stages.native_content_generator import NativeContentGenerator
from app.generation.stages.models import StoryOutline, StoryOutlineItem
from app.generation.stages.presenton_content_generator import PresentonContentGenerator


def test_modern_blue_uses_presenton_other_themes_use_native() -> None:
    assert isinstance(build_content_generator("modern-blue"), PresentonContentGenerator)
    for theme_id in ("editorial-cobalt", "warm-studio", "midnight-signal"):
        assert isinstance(build_content_generator(theme_id), NativeContentGenerator)


def test_every_presenton_layout_exposes_content_constraints() -> None:
    adapter = PresentonTemplateAdapter()

    constraints = {
        layout_id: adapter.content_constraints(layout_id)
        for layout_id in adapter.layout_ids
    }

    assert set(constraints) == set(adapter.layout_ids)
    assert constraints["title_slide"].title_max_chars == 72
    assert constraints["title_description_bullet_points_grid_with_icon"].max_items == 4
    assert constraints["title_description_image"].max_items == 3


def test_presenton_renderer_applies_default_content_budgets() -> None:
    generator = PresentonContentGenerator()
    long_title = "A" * 120
    long_content = "B" * 400
    outline = StoryOutline(
        items=[
            StoryOutlineItem(
                id="cover",
                title=long_title,
                content=long_content,
                role="cover",
            ),
        ]
    )
    document = generator.render(
        GenerationRequest(
            presentation_id=uuid4(),
            title=long_title,
            text=long_content,
            sections=[],
            language="en",
            slide_count=1,
            theme_id="modern-blue",
        ),
        outline,
        assets={},
    )
    slide = document["slides"][0]
    title_elements = [
        element for element in slide["elements"]
        if element.get("type") == "text" and "heading" in str(element.get("name", "")).lower()
    ]
    assert title_elements
    rendered_title = title_elements[0]["runs"][0]["text"]
    assert len(rendered_title) <= 72
