from dataclasses import FrozenInstanceError, asdict

import pytest

from app.generation.models import DeckPlan, SlideContent, SlidePlan


def test_slide_plan_represents_semantics_without_geometry() -> None:
    plan = SlidePlan(
        id="slide-03",
        index=3,
        role="comparison",
        communication_goal="Contrast chatbots with AI agents",
        content_structure="two-sided-comparison",
        item_count=3,
        relationship="contrast",
        visual_priority="balanced",
        image_requirement="none",
        density="medium",
        preferred_archetype="comparison-2col",
    )

    serialized = asdict(plan)

    assert serialized["communication_goal"] == "Contrast chatbots with AI agents"
    assert serialized["item_count"] == 3
    assert {"x", "y", "width", "height"}.isdisjoint(serialized)


def test_deck_plan_holds_ordered_slide_plans_without_slide_copy() -> None:
    slide = SlidePlan(
        id="slide-01",
        index=1,
        role="cover",
        communication_goal="Introduce the topic",
        content_structure="headline",
    )

    deck = DeckPlan(
        title="AI Agents",
        audience="Software engineers",
        objective="Explain agent architecture and adoption",
        narrative_arc="problem → shift → architecture → applications → risks",
        language="en",
        slides=[slide],
    )

    assert deck.slides == [slide]
    assert "content" not in asdict(deck)["slides"][0]


def test_slide_content_addresses_layout_slots_by_name() -> None:
    content = SlideContent(
        slide_id="slide-03",
        title="Chatbots vs AI Agents",
        slots={
            "left_heading": "Chatbots",
            "left_items": ["Respond to individual prompts"],
            "right_heading": "AI Agents",
            "right_items": ["Plan multi-step objectives"],
        },
    )

    assert content.slots["right_heading"] == "AI Agents"
    assert content.slots["left_items"] == ["Respond to individual prompts"]


def test_generation_plan_models_prevent_field_reassignment() -> None:
    plan = SlidePlan(
        id="slide-01",
        index=1,
        role="cover",
        communication_goal="Introduce the topic",
        content_structure="headline",
    )

    with pytest.raises(FrozenInstanceError):
        plan.role = "content"  # type: ignore[misc]
