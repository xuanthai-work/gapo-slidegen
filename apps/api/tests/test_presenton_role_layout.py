from uuid import uuid4

from app.generation.provider import GenerationRequest
from app.generation.stages.layout_selector import PresentonLayoutSelector
from app.generation.stages.models import StoryOutline, StoryOutlineItem
from app.generation.stages.presenton_content_generator import PresentonContentGenerator


def test_role_maps_to_preferred_layout() -> None:
    generator = PresentonContentGenerator()
    outline = StoryOutline(
        items=[
            StoryOutlineItem(id="cover", title="Pitch", content="", role="cover"),
            StoryOutlineItem(
                id="problem",
                title="Wasted hours",
                content="Teams lose time formatting slides.",
                role="problem",
            ),
        ]
    )
    document = generator.render(
        GenerationRequest(
            presentation_id=uuid4(),
            title="Pitch",
            text="Teams lose time formatting slides.",
            sections=[],
            language="en",
            slide_count=2,
            theme_id="modern-blue",
        ),
        outline,
        assets={},
    )
    assert [slide["layout_id"] for slide in document["slides"]] == [
        "title_slide",
        "title_description_image",
    ]


def test_explicit_layout_id_wins_over_role() -> None:
    generator = PresentonContentGenerator()
    outline = StoryOutline(
        items=[
            StoryOutlineItem(
                id="s1",
                title="A",
                content="B",
                role="big-stat",
                layout_id="title_description_bullet_points_grid_with_icon",
            ),
        ]
    )
    document = generator.render(
        GenerationRequest(
            presentation_id=uuid4(),
            title="A",
            text="B",
            sections=[],
            language="en",
            slide_count=1,
            theme_id="modern-blue",
        ),
        outline,
        assets={},
    )
    assert document["slides"][0]["layout_id"] == "title_description_bullet_points_grid_with_icon"


def test_legacy_layout_mapping_still_works() -> None:
    generator = PresentonContentGenerator()
    outline = StoryOutline(
        items=[
            StoryOutlineItem(
                id="s1",
                title="Features",
                content="Feature list.",
                layout="feature-list",
            ),
        ]
    )
    document = generator.render(
        GenerationRequest(
            presentation_id=uuid4(),
            title="Features",
            text="Feature list.",
            sections=[],
            language="en",
            slide_count=1,
            theme_id="modern-blue",
        ),
        outline,
        assets={},
    )
    assert document["slides"][0]["layout_id"] == "title_description_bullet_points_list_with_icon"


def test_fallback_rotates_when_no_role_or_layout() -> None:
    generator = PresentonContentGenerator()
    outline = StoryOutline(
        items=[
            StoryOutlineItem(id="s1", title="One", content="C1"),
            StoryOutlineItem(id="s2", title="Two", content="C2"),
        ]
    )
    document = generator.render(
        GenerationRequest(
            presentation_id=uuid4(),
            title="Deck",
            text="Content.",
            sections=[],
            language="en",
            slide_count=2,
            theme_id="modern-blue",
        ),
        outline,
        assets={},
    )
    layout_ids = [slide["layout_id"] for slide in document["slides"]]
    assert len(set(layout_ids)) == 2


def test_ranking_prefers_metric_layout_for_metric_blocks() -> None:
    selector = PresentonLayoutSelector()
    item = StoryOutlineItem(
        id="metrics",
        title="Results",
        content="Adoption accelerated.",
        role="big-stat",
        blocks=[
            {
                "heading": "Adoption",
                "body": "Weekly active teams",
                "label": "Growth",
                "value": "+42%",
            }
        ],
    )

    ranking = selector.rank(item, index=2, theme_id="modern-blue")

    assert ranking[0].layout_id == (
        "title_image_description_list_with_highlighted_text_heading_description"
    )
    assert ranking == sorted(ranking, key=lambda candidate: candidate.score, reverse=True)


def test_ranking_respects_layout_item_capacity() -> None:
    selector = PresentonLayoutSelector()
    item = StoryOutlineItem(
        id="features",
        title="Six capabilities",
        content="A broad platform.",
        role="features",
        blocks=[
            {"heading": f"Feature {index}", "body": "Description"}
            for index in range(6)
        ],
    )

    ranking = selector.rank(item, index=3, theme_id="modern-blue")

    assert ranking[0].layout_id == "title_list_of_cards_with_image"
    grid = next(
        candidate
        for candidate in ranking
        if candidate.layout_id == "title_description_bullet_points_grid_with_icon"
    )
    assert grid.score < ranking[0].score
    assert "item-capacity-exceeded" in grid.reasons
