from app.generation.local_icon_registry import resolve_icon_for_context, resolve_icon_svg


def test_resolve_icon_svg_from_full_pack() -> None:
    svg = resolve_icon_svg("flow-arrow")
    assert svg is not None
    assert "<svg" in svg


def test_resolve_icon_for_context_uses_role_fallback() -> None:
    svg = resolve_icon_for_context(role="process", slot_name="main_visual_panel", title="", content="")
    assert svg is not None
    assert "<svg" in svg


def test_resolve_icon_for_context_matches_keywords_in_copy() -> None:
    svg = resolve_icon_for_context(
        role="content",
        slot_name="left_media_image",
        title="How data flows between nodes",
        content="Everything is JSON in the workflow.",
    )
    assert svg is not None
    assert "<svg" in svg
