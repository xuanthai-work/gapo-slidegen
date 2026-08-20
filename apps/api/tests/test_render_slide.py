from uuid import uuid4

from app.generation.models import SlideContent
from app.generation.provider import GenerationRequest
from app.generation.stages.content_generator import ThemeDispatchContentGenerator
from app.generation.stages.models import StoryOutline, StoryOutlineItem
from app.generation.stages.presenton_content_generator import PresentonContentGenerator


def _request() -> GenerationRequest:
    return GenerationRequest(
        presentation_id=uuid4(),
        title="Deck",
        text="Source",
        sections=[],
        language="en",
        slide_count=2,
        theme_id="modern-blue",
    )


def _outline() -> StoryOutline:
    return StoryOutline(
        items=[
            StoryOutlineItem(id="cover", title="Cover", content="Intro", layout_id="title_slide"),
            StoryOutlineItem(
                id="point-1",
                title="Point",
                content="Body copy",
                layout_id="title_description_image",
            ),
        ]
    )


def test_presenton_render_slide_compiles_one_item_independently() -> None:
    generator = PresentonContentGenerator()
    outline = _outline()
    contents = {
        "point-1": SlideContent(
            slide_id="point-1",
            title="Point",
            layout_id="title_description_image",
            slots={"body": "Body copy"},
        )
    }

    slide = generator.render_slide(
        _request(),
        outline,
        index=1,
        assets={},
        contents=contents,
    )

    assert slide["title"] == "Point"
    assert isinstance(slide.get("elements"), list)


def test_theme_dispatch_render_slide_delegates_without_rendering_the_deck() -> None:
    generator = ThemeDispatchContentGenerator()
    outline = _outline()
    first = generator.render_slide(_request(), outline, index=0, assets={}, contents={})
    second = generator.render_slide(_request(), outline, index=1, assets={}, contents={})

    assert first != second
    assert isinstance(first.get("elements"), list)
    assert isinstance(second.get("elements"), list)
