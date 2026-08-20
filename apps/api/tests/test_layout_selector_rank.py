from app.generation.stages.layout_selector import (
    NativeLayoutSelector,
    PresentonLayoutSelector,
    ThemeDispatchLayoutSelector,
)
from app.generation.stages.models import StoryOutlineItem


def test_dispatch_rank_matches_presenton_top_layout() -> None:
    item = StoryOutlineItem(
        id="p1",
        title="Wasted hours",
        content="Teams lose time formatting slides.",
        role="problem",
    )
    presenton = PresentonLayoutSelector()
    dispatch = ThemeDispatchLayoutSelector()
    expected = presenton.rank(item, index=1, theme_id="modern-blue")
    got = dispatch.rank(item, index=1, theme_id="modern-blue")
    assert got[0].layout_id == expected[0].layout_id
    assert len(got) == len(expected)


def test_native_rank_is_single_select_result() -> None:
    item = StoryOutlineItem(id="c", title="Cover", content="", role="cover")
    selector = NativeLayoutSelector()
    ranked = selector.rank(item, index=0, theme_id="editorial-cobalt")
    assert len(ranked) == 1
    assert ranked[0].layout_id == selector.select(item, index=0, theme_id="editorial-cobalt")
