from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.generation.outlines import (
    InvalidOutline,
    build_owned_outline_query,
    build_source_outline_query,
    build_update_outline_statement,
    validate_outline_items,
)
from app.generation.provider import OutlineRequest
from app.generation.stub_provider import StubPresentationProvider


def test_stub_outline_has_requested_slide_count_and_stable_ids() -> None:
    items = StubPresentationProvider().generate_outline(
        OutlineRequest(
            title="Reviewed deck",
            text="One two three four five six seven eight nine ten.",
            sections=[],
            language="en",
            slide_count=4,
        )
    )
    assert len(items) == 4
    assert items[0]["title"] == "Reviewed deck"
    assert len({item["id"] for item in items}) == 4


def test_outline_validation_rejects_empty_duplicate_and_oversized_input() -> None:
    with pytest.raises(InvalidOutline, match="between 1 and 30"):
        validate_outline_items([])
    duplicate = [
        {"id": "same", "title": "One", "content": ""},
        {"id": "same", "title": "Two", "content": ""},
    ]
    with pytest.raises(InvalidOutline, match="unique"):
        validate_outline_items(duplicate)
    with pytest.raises(InvalidOutline, match="between 1 and 30"):
        validate_outline_items(
            [{"id": f"item-{index}", "title": "Slide", "content": ""} for index in range(31)]
        )


def test_outline_queries_filter_owner_and_revision() -> None:
    outline_id = uuid4()
    owner_id = uuid4()
    owned_sql = str(
        build_owned_outline_query(outline_id, owner_id).compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    update_sql = str(
        build_update_outline_statement(
            outline_id,
            owner_id,
            3,
            [{"id": "slide-1", "title": "Title", "content": ""}],
        ).compile(dialect=postgresql.dialect())
    )
    assert str(owner_id) in owned_sql
    assert "outlines.owner_id" in owned_sql
    assert "outlines.owner_id" in update_sql
    assert "outlines.revision" in update_sql
    assert "RETURNING" in update_sql

    source_sql = str(
        build_source_outline_query(uuid4(), owner_id).compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert "outlines.source_id" in source_sql
    assert "outlines.owner_id" in source_sql
    assert "LIMIT 1" in source_sql
