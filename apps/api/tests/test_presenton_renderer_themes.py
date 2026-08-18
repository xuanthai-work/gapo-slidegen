from uuid import uuid4

from app.generation.provider import GenerationRequest
from app.generation.stages.content_generator import build_content_generator
from app.generation.stages.models import StoryOutline, StoryOutlineItem
from app.generation.stages.presenton_content_generator import PresentonContentGenerator


def test_all_product_themes_use_presenton_renderer() -> None:
    for theme_id in ("modern-blue", "editorial-cobalt", "warm-studio", "midnight-signal"):
        assert isinstance(build_content_generator(theme_id), PresentonContentGenerator)


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
