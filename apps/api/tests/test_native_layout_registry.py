from uuid import uuid4

import pytest

from app.generation.layouts import (
    NativeLayoutContext,
    NativeLayoutRegistry,
    build_native_layout_registry,
)
from app.generation.provider import GenerationRequest
from app.generation.models import SlideContent
from app.generation.stages.layout_selector import (
    NativeLayoutSelector,
    ThemeDispatchLayoutSelector,
)
from app.generation.stages.models import StoryOutline, StoryOutlineItem
from app.generation.stages.native_content_generator import NativeContentGenerator
from app.generation.stages.slide_validator import RuleBasedSlideValidator
from app.generation.themes import get_theme


def test_native_layout_registry_exposes_product_owned_layouts() -> None:
    registry = build_native_layout_registry()

    assert set(registry.layout_ids) == {
        "cover-editorial",
        "cover-midnight",
        "cover-warm",
        "content-band",
        "content-frame",
        "content-header",
        "content-margin",
        "content-split",
        "content-statement",
    }


def test_native_layouts_own_their_content_constraints() -> None:
    registry = build_native_layout_registry()

    cover = registry.content_constraints("cover-warm")
    header = registry.content_constraints("content-header")
    statement = registry.content_constraints("content-statement")

    assert cover.title_max_chars == 72
    assert cover.content_max_chars == 200
    assert cover.max_items == 0
    assert header.max_items == 3
    assert header.block_body_max_chars == 220
    assert statement.content_max_chars < header.content_max_chars


def test_native_layout_registry_rejects_unknown_layout() -> None:
    registry = NativeLayoutRegistry()
    context = NativeLayoutContext(
        title="Unknown",
        body="",
        theme_id="modern-blue",
        colors={},
        fonts={},
    )

    with pytest.raises(ValueError, match="Unknown native layout"):
        registry.compile("missing", context)


class RecordingLayoutRegistry:
    def __init__(self) -> None:
        self.calls: list[tuple[str, NativeLayoutContext]] = []

    def compile(
        self,
        layout_id: str,
        context: NativeLayoutContext,
    ) -> dict[str, object]:
        self.calls.append((layout_id, context))
        return {
            "id": f"compiled-{len(self.calls)}",
            "title": context.title,
            "background": context.colors["background"],
            "revision": 0,
            "elements": [],
        }


def test_native_content_generator_delegates_geometry_to_registry() -> None:
    registry = RecordingLayoutRegistry()
    generator = NativeContentGenerator(registry=registry)
    outline = StoryOutline(
        items=[
            StoryOutlineItem(id="cover", title="Architecture", content="A clear boundary"),
            StoryOutlineItem(
                id="detail",
                title="Deterministic layouts",
                content="Code owns geometry.",
                role="big-stat",
            ),
        ]
    )

    generator.render(
        GenerationRequest(
            presentation_id=uuid4(),
            title="Architecture",
            text="Source",
            sections=[],
            language="en",
            slide_count=2,
            theme_id="warm-studio",
        ),
        outline,
        assets={},
    )

    assert [layout_id for layout_id, _ in registry.calls] == [
        "cover-warm",
        "content-statement",
    ]
    assert registry.calls[1][1].index == 1
    assert registry.calls[1][1].total == 2


def _editorial_context(**overrides: object) -> NativeLayoutContext:
    theme = get_theme("editorial-cobalt")
    colors = {key: str(value) for key, value in theme["colors"].items()}
    fonts = {key: str(value) for key, value in theme["fonts"].items()}
    payload: dict[str, object] = {
        "title": "Layout geometry must stay conflict-free",
        "body": "A lead paragraph that used to fill the same well as the item blocks.",
        "theme_id": "editorial-cobalt",
        "colors": colors,
        "fonts": fonts,
        "index": 1,
        "total": 8,
        "blocks": [
            {"heading": "First item", "body": "Supporting detail one."},
            {"heading": "Second item", "body": "Supporting detail two."},
            {"heading": "Third item", "body": "Supporting detail three."},
        ],
    }
    payload.update(overrides)
    return NativeLayoutContext(**payload)  # type: ignore[arg-type]


def test_content_header_keeps_body_and_item_blocks_from_overlapping() -> None:
    slide = build_native_layout_registry().compile(
        "content-header",
        _editorial_context(),
    )

    result = RuleBasedSlideValidator().validate(slide)

    assert result.valid, [issue.message for issue in result.issues]


def test_content_header_without_blocks_stays_inside_the_canvas() -> None:
    slide = build_native_layout_registry().compile(
        "content-header",
        _editorial_context(blocks=[]),
    )

    result = RuleBasedSlideValidator().validate(slide)

    assert result.valid, [issue.message for issue in result.issues]


def test_native_selector_uses_header_when_slide_has_structured_blocks() -> None:
    item = StoryOutlineItem(
        id="problem",
        title="Why teams stall",
        content="Formatting still eats the week.",
        role="problem",
        blocks=[
            {"heading": "Three tools", "body": "Design, notes, and export live in different apps."},
            {"heading": "No owner", "body": "Each deck is rebuilt from scratch."},
        ],
    )

    selector = NativeLayoutSelector()

    assert selector.select(item, index=1, theme_id="warm-studio") == "content-header"
    assert selector.content_constraints("content-header").max_items == 3


def test_native_selector_keeps_statement_for_quote_even_with_blocks() -> None:
    item = StoryOutlineItem(
        id="quote",
        title="What users said",
        content="We stopped rebuilding slides.",
        role="quote",
        blocks=[
            {"heading": "A", "body": "B"},
            {"heading": "C", "body": "D"},
        ],
    )

    assert NativeLayoutSelector().select(item, index=2, theme_id="editorial-cobalt") == (
        "content-statement"
    )


def test_theme_dispatch_selector_routes_native_and_presenton_by_theme() -> None:
    selector = ThemeDispatchLayoutSelector()
    cover = StoryOutlineItem(id="cover", title="Pitch", content="", role="cover")

    assert selector.select(cover, index=0, theme_id="modern-blue") == "title_slide"
    assert selector.select(cover, index=0, theme_id="warm-studio") == "cover-warm"


def test_native_generator_compiles_selected_layout_id_and_keeps_blocks() -> None:
    registry = RecordingLayoutRegistry()
    generator = NativeContentGenerator(registry=registry)
    outline = StoryOutline(
        items=[
            StoryOutlineItem(id="cover", title="Architecture", content="A clear boundary"),
            StoryOutlineItem(
                id="detail",
                title="Why geometry must stay owned by layout",
                content="Lead copy that should sit above the facts.",
                role="problem",
                layout_id="content-header",
            ),
        ]
    )
    contents = {
        "detail": SlideContent(
            slide_id="detail",
            layout_id="content-header",
            title="Why geometry must stay owned by layout",
            slots={
                "body": "Lead copy that should sit above the facts.",
                "items": [
                    {"heading": "First fact", "body": "Design, notes, and export are separate."},
                    {"heading": "Second fact", "body": "Each deck is rebuilt from scratch."},
                ],
            },
        )
    }

    generator.render(
        GenerationRequest(
            presentation_id=uuid4(),
            title="Architecture",
            text="Source",
            sections=[],
            language="en",
            slide_count=2,
            theme_id="warm-studio",
        ),
        outline,
        assets={},
        contents=contents,
    )

    assert registry.calls[1][0] == "content-header"
    assert [block["heading"] for block in registry.calls[1][1].blocks] == [
        "First fact",
        "Second fact",
    ]


def test_native_header_layout_renders_block_copy_on_the_slide() -> None:
    generator = NativeContentGenerator()
    outline = StoryOutline(
        items=[
            StoryOutlineItem(id="cover", title="Pitch", content="Intro"),
            StoryOutlineItem(
                id="detail",
                title="The cost of restitching decks",
                content="Teams lose two days each cycle.",
                role="problem",
                layout_id="content-header",
            ),
        ]
    )
    contents = {
        "detail": SlideContent(
            slide_id="detail",
            layout_id="content-header",
            title="The cost of restitching decks",
            slots={
                "body": "Teams lose two days each cycle.",
                "items": [
                    {
                        "heading": "12 hours in Figma",
                        "body": "Visual design is rebuilt for every client.",
                    },
                    {
                        "heading": "No shared outline",
                        "body": "Narrative lives in chat threads.",
                    },
                ],
            },
        )
    }

    slide = generator.render_slide(
        GenerationRequest(
            presentation_id=uuid4(),
            title="Pitch",
            text="Source",
            sections=[],
            language="en",
            slide_count=2,
            theme_id="editorial-cobalt",
        ),
        outline,
        index=1,
        assets={},
        contents=contents,
    )

    texts = [
        run.get("text")
        for element in slide["elements"]
        if isinstance(element, dict)
        for run in (element.get("runs") or [])
        if isinstance(run, dict)
    ]
    assert "12 hours in Figma" in texts
    assert "No shared outline" in texts
    assert RuleBasedSlideValidator().validate(slide).valid
