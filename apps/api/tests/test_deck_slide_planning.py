from uuid import uuid4

from app.generation.provider import GenerationRequest, ProviderResponseError
from app.generation.stages.deck_planner import OutlineDeckPlanner, ProviderDeckPlanner
from app.generation.stages.models import StoryOutline, StoryOutlineItem
from app.generation.stages.slide_planner import OutlineSlidePlanner, ProviderSlidePlanner


def _request() -> GenerationRequest:
    return GenerationRequest(
        presentation_id=uuid4(),
        title="AI Agents",
        text="Source",
        sections=[],
        language="en",
        slide_count=2,
    )


def test_deck_planner_creates_narrative_without_copy_or_geometry() -> None:
    outline = StoryOutline(
        items=[
            StoryOutlineItem(id="cover", title="AI Agents", content="A practical guide"),
            StoryOutlineItem(
                id="comparison",
                title="Chatbots vs agents",
                content="Agents plan and act.",
                role="comparison",
                blocks=[
                    {"heading": "Chatbots", "body": "Respond"},
                    {"heading": "Agents", "body": "Plan and act"},
                ],
            ),
        ]
    )

    deck = OutlineDeckPlanner().plan(_request(), outline)

    assert deck.title == "AI Agents"
    assert [slide.role for slide in deck.slides] == ["cover", "comparison"]
    assert all(slide.content_structure == "unspecified" for slide in deck.slides)
    assert not hasattr(deck.slides[1], "content")
    assert not hasattr(deck.slides[1], "x")


def test_slide_planner_refines_one_slide_from_neighbor_context() -> None:
    outline = StoryOutline(
        items=[
            StoryOutlineItem(id="cover", title="AI Agents", content="A practical guide"),
            StoryOutlineItem(
                id="comparison",
                title="Chatbots vs agents",
                content="Agents plan and act.",
                role="comparison",
                blocks=[
                    {"heading": "Chatbots", "body": "Respond"},
                    {"heading": "Agents", "body": "Plan and act"},
                ],
            ),
        ]
    )
    deck = OutlineDeckPlanner().plan(_request(), outline)

    refined = OutlineSlidePlanner().plan(
        deck_plan=deck,
        current_slide=deck.slides[1],
        source_item=outline.items[1],
        previous_slide=deck.slides[0],
        next_slide=None,
    )

    assert refined.content_structure == "comparison"
    assert refined.relationship == "contrast"
    assert refined.item_count == 2
    assert refined.visual_priority == "balanced"
    assert refined.image_requirement == "none"


class FailingPlanningProvider:
    name = "failing"

    def plan_deck(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
    ):
        del request, outline
        raise ProviderResponseError("invalid deck plan")

    def plan_slide(self, **kwargs):
        del kwargs
        raise ProviderResponseError("invalid slide plan")


def test_provider_planners_fall_back_to_outline_semantics() -> None:
    outline = StoryOutline(
        items=[
            StoryOutlineItem(id="cover", title="AI Agents", content="A practical guide"),
            StoryOutlineItem(
                id="comparison",
                title="Chatbots vs agents",
                content="Agents plan and act.",
                role="comparison",
                blocks=[
                    {"heading": "Chatbots", "body": "Respond"},
                    {"heading": "Agents", "body": "Plan and act"},
                ],
            ),
        ]
    )
    deck_planner = ProviderDeckPlanner(
        FailingPlanningProvider(),
        fallback=OutlineDeckPlanner(),
    )
    slide_planner = ProviderSlidePlanner(
        FailingPlanningProvider(),
        fallback=OutlineSlidePlanner(),
    )

    deck = deck_planner.plan(_request(), outline)
    slide = slide_planner.plan(
        deck_plan=deck,
        current_slide=deck.slides[1],
        source_item=outline.items[1],
        previous_slide=deck.slides[0],
        next_slide=None,
    )

    assert deck.slides[1].role == "comparison"
    assert slide.content_structure == "comparison"
