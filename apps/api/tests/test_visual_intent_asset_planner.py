from uuid import uuid4

from app.generation.provider import GenerationRequest
from app.generation.stages.asset_planner import VisualIntentAssetPlanner
from app.generation.stages.models import StoryOutline, StoryOutlineItem


def test_planner_emits_visual_intent_for_split_image() -> None:
    planner = VisualIntentAssetPlanner()
    outline = StoryOutline(
        items=[
            StoryOutlineItem(id="cover", title="Cover", content="", role="cover"),
            StoryOutlineItem(
                id="problem",
                title="Time wasted on manual formatting",
                content="Teams spend hours aligning boxes instead of thinking.",
                role="problem",
                layout_id="title_description_image",
            ),
        ]
    )
    plan = planner.plan(
        outline,
        GenerationRequest(
            presentation_id=uuid4(),
            title="Pitch",
            text="Content",
            sections=[],
            language="en",
            slide_count=2,
        ),
    )
    assert len(plan.requests) == 1
    request = plan.requests[0]
    assert request.slot.slide_index == 1
    assert request.slot.name == "left_media_image"
    assert request.visual_intent is not None
    intent = request.visual_intent
    assert intent["role"] == "problem"
    assert "mood" in intent
    assert isinstance(intent.get("avoid"), list)
    assert "red downward arrow" in request.prompt


def test_planner_uses_legacy_layout_when_no_layout_id() -> None:
    planner = VisualIntentAssetPlanner()
    outline = StoryOutline(
        items=[
            StoryOutlineItem(
                id="split",
                title="Architecture",
                content="System overview.",
                layout="split-image",
            ),
        ]
    )
    plan = planner.plan(
        outline,
        GenerationRequest(
            presentation_id=uuid4(),
            title="Architecture",
            text="System overview.",
            sections=[],
            language="en",
            slide_count=1,
        ),
    )
    assert len(plan.requests) == 1
    assert plan.requests[0].slot.name == "left_media_image"


def test_planner_skips_layouts_without_image_slots() -> None:
    planner = VisualIntentAssetPlanner()
    outline = StoryOutline(
        items=[
            StoryOutlineItem(
                id="grid",
                title="Features",
                content="Feature grid.",
                layout="feature-grid",
                role="features",
            ),
        ]
    )
    plan = planner.plan(
        outline,
        GenerationRequest(
            presentation_id=uuid4(),
            title="Features",
            text="Feature grid.",
            sections=[],
            language="en",
            slide_count=1,
        ),
    )
    assert plan.requests == []


def test_prompt_respects_provider_length_limit() -> None:
    planner = VisualIntentAssetPlanner()
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
            title="T",
            text="Source",
            sections=[],
            language="en",
            slide_count=1,
        ),
    )
    assert len(plan.requests[0].prompt) <= 1_000
