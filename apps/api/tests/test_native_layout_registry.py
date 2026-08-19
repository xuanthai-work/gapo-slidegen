from uuid import uuid4

import pytest

from app.generation.layouts import (
    NativeLayoutContext,
    NativeLayoutRegistry,
    build_native_layout_registry,
)
from app.generation.provider import GenerationRequest
from app.generation.stages.models import StoryOutline, StoryOutlineItem
from app.generation.stages.native_content_generator import NativeContentGenerator


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
    assert cover.max_items == 0
    assert header.max_items == 3
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
