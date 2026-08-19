import json

from app.generation.content_schema import GeneratedDeckContent
from app.generation.llm_schema import llm_json_schema
from app.generation.outline_schema import (
    ContentBudget,
    GeneratedOutlineResponse,
    build_story_prompt,
)
from app.generation.planning_schema import GeneratedDeckPlan, GeneratedSlidePlan
from app.generation.provider import OutlineRequest


def test_content_budget_defaults_leave_room_for_facts() -> None:
    budget = ContentBudget()

    assert budget.title_max_chars == 80
    assert budget.content_max_chars == 500
    assert budget.block_heading_max_chars == 55
    assert budget.block_body_max_chars == 350


def test_story_prompt_asks_for_source_facts_not_slogan_copy() -> None:
    prompt = build_story_prompt(
        OutlineRequest(
            title="Hai Phong plant",
            text="The Hai Phong plant produced 12,000 tons in 2023 and employs 480 people.",
            sections=[],
            language="en",
            slide_count=None,
            source_kind="manuscript",
        ),
        max_input_chars=4_000,
    )

    assert "single takeaway sentence under 180" not in prompt
    assert "12,000 tons" in prompt
    assert "2-4 blocks" in prompt
    assert "Ground content and blocks in facts" in prompt
    assert "Do not write slogan-only slides" in prompt
    assert "under 500 characters" in prompt
    assert "under 350 characters" in prompt
    assert "under 320 characters" not in prompt
    assert "under 180 characters" not in prompt
    assert "Each block body should be at least one sentence" in prompt
    assert "Use the available space" in prompt
    assert "if a string is over budget, cut repetition" not in prompt
    assert "class of 30, each learner speaks about 4 minutes" in prompt
    assert "scores the recording, marks the missed sound" in prompt


def test_vietnamese_story_prompt_asks_for_source_facts() -> None:
    prompt = build_story_prompt(
        OutlineRequest(
            title="Nhà máy Hải Phòng",
            text="Nhà máy Hải Phòng sản xuất 12.000 tấn năm 2023.",
            sections=[],
            language="vi",
            slide_count=None,
            source_kind="manuscript",
        ),
        max_input_chars=4_000,
    )

    assert "câu takeaway chính, không quá 180" not in prompt
    assert "2-4 blocks" in prompt
    assert "Không viết slide chỉ gồm slogan" in prompt
    assert "không quá 500 ký tự" in prompt
    assert "không quá 350 ký tự" in prompt
    assert "không quá 320 ký tự" not in prompt
    assert "không quá 180 ký tự" not in prompt
    assert "Mỗi block body ít nhất một câu" in prompt
    assert "Dùng hết chỗ trống" in prompt
    assert "nếu vượt ngân sách thì cắt" not in prompt


def test_llm_schema_omits_string_length_constraints() -> None:
    for schema_model in (
        GeneratedOutlineResponse,
        GeneratedDeckPlan,
        GeneratedSlidePlan,
        GeneratedDeckContent,
    ):
        dumped = llm_json_schema(schema_model)
        assert "maxLength" not in dumped
        assert "minLength" not in dumped
        parsed = json.loads(dumped)
        assert parsed["properties"] or parsed.get("$defs")


def test_outline_llm_schema_omits_content_budget() -> None:
    dumped = llm_json_schema(GeneratedOutlineResponse)

    assert "content_budget" not in dumped
    assert "ContentBudget" not in dumped
    assert "title" in dumped
    assert "blocks" in dumped
