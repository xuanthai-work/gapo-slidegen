from uuid import uuid4

from app.generation.provider import GenerationRequest
from app.generation.stages.asset_planner import StubAssetPlanner, VisualIntentAssetPlanner
from app.generation.stages.models import StoryOutline, StoryOutlineItem


def test_split_image_slide_requests_main_visual_panel() -> None:
    planner = StubAssetPlanner()
    outline = StoryOutline(
        items=[
            StoryOutlineItem(id="cover", title="Cover", content="", layout="cover"),
            StoryOutlineItem(
                id="split",
                title="Architecture",
                content="System overview diagram.",
                layout="split-image",
            ),
        ]
    )
    plan = planner.plan(
        outline,
        GenerationRequest(
            presentation_id=uuid4(),
            title="Deck",
            text="Source",
            sections=[],
            language="en",
            slide_count=2,
        ),
    )

    assert len(plan.requests) == 1
    request = plan.requests[0]
    assert request.slot.slide_index == 1
    assert request.slot.name == "left_media_image"
    assert request.slot.kind == "image"
    assert "Architecture" in request.prompt
    assert "System overview diagram" in request.prompt


def test_non_image_layouts_request_no_assets() -> None:
    planner = StubAssetPlanner()
    outline = StoryOutline(
        items=[
            StoryOutlineItem(id="cover", title="Cover", content="", layout="cover"),
            StoryOutlineItem(id="grid", title="Features", content="Feature grid.", layout="feature-grid"),
            StoryOutlineItem(id="list", title="Items", content="List of items.", layout="feature-list"),
        ]
    )
    plan = planner.plan(
        outline,
        GenerationRequest(
            presentation_id=uuid4(),
            title="Deck",
            text="Source",
            sections=[],
            language="en",
            slide_count=3,
        ),
    )
    assert plan.requests == []


def test_prompt_is_bounded() -> None:
    planner = StubAssetPlanner()
    long_content = "word " * 3_000
    outline = StoryOutline(
        items=[
            StoryOutlineItem(
                id="split",
                title="T",
                content=long_content,
                layout="split-image",
            ),
        ]
    )
    plan = planner.plan(
        outline,
        GenerationRequest(
            presentation_id=uuid4(),
            title="Deck",
            text="Source",
            sections=[],
            language="en",
            slide_count=1,
        ),
    )
    assert len(plan.requests[0].prompt) <= 1_000


def test_visual_intent_planner_keeps_stub_behavior() -> None:
    planner = VisualIntentAssetPlanner()
    outline = StoryOutline(
        items=[
            StoryOutlineItem(id="cover", title="Cover", content="", layout="cover"),
            StoryOutlineItem(
                id="split",
                title="Architecture",
                content="System overview diagram.",
                layout="split-image",
            ),
        ]
    )
    plan = planner.plan(
        outline,
        GenerationRequest(
            presentation_id=uuid4(),
            title="Deck",
            text="Source",
            sections=[],
            language="en",
            slide_count=2,
        ),
    )
    assert len(plan.requests) == 1
    assert plan.requests[0].slot.name == "left_media_image"
    assert plan.requests[0].visual_intent is not None
