from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.generation.provider import GenerationRequest
from app.generation.service import (
    build_delete_presentation_statement,
    build_owned_presentations_query,
    build_update_presentation_statement,
    collect_asset_ids,
)
from app.generation.stub_provider import StubPresentationProvider
from app.generation.validation import InvalidPresentationDocument, validate_presentation_document


def _document():
    presentation_id = uuid4()
    document = StubPresentationProvider().generate(
        GenerationRequest(
            presentation_id=presentation_id,
            title="Editable draft",
            text="A source paragraph.",
            sections=[],
            language="en",
            slide_count=2,
        )
    )
    return presentation_id, document


def test_generated_document_passes_save_boundary() -> None:
    presentation_id, document = _document()
    validate_presentation_document(document, presentation_id)


def test_save_boundary_rejects_wrong_id_and_more_than_thirty_slides() -> None:
    presentation_id, document = _document()
    wrong_id = deepcopy(document)
    wrong_id["id"] = str(uuid4())
    with pytest.raises(InvalidPresentationDocument, match="does not match"):
        validate_presentation_document(wrong_id, presentation_id)

    too_many = deepcopy(document)
    too_many["slides"] = [deepcopy(document["slides"][0]) for _ in range(31)]
    with pytest.raises(InvalidPresentationDocument, match="between 1 and 30"):
        validate_presentation_document(too_many, presentation_id)

    empty = deepcopy(document)
    empty["slides"] = []
    with pytest.raises(InvalidPresentationDocument, match="between 1 and 30"):
        validate_presentation_document(empty, presentation_id)


def test_optimistic_update_filters_owner_and_expected_revision() -> None:
    presentation_id, document = _document()
    owner_id = uuid4()
    sql = str(
        build_update_presentation_statement(
            presentation_id,
            owner_id,
            expected_revision=4,
            document=document,
        ).compile(dialect=postgresql.dialect())
    )
    assert "presentations.owner_id" in sql
    assert "presentations.revision" in sql
    assert "RETURNING" in sql


def test_optimistic_delete_filters_owner_and_expected_revision() -> None:
    presentation_id = uuid4()
    owner_id = uuid4()
    sql = str(
        build_delete_presentation_statement(
            presentation_id,
            owner_id,
            expected_revision=3,
        ).compile(dialect=postgresql.dialect())
    )
    assert "presentations.owner_id" in sql
    assert "presentations.revision" in sql
    assert "RETURNING" in sql


def test_presentation_list_is_owned_ordered_and_bounded() -> None:
    owner_id = uuid4()
    sql = str(
        build_owned_presentations_query(owner_id, limit=50).compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert str(owner_id) in sql
    assert "presentations.owner_id" in sql
    assert "ORDER BY presentations.updated_at DESC" in sql
    assert "LIMIT 50" in sql


def test_collect_asset_ids_includes_nested_images() -> None:
    first_id = uuid4()
    second_id = uuid4()
    document = {
        "slides": [
            {
                "elements": [
                    {"type": "image", "assetId": str(first_id)},
                    {
                        "type": "group",
                        "children": [{"type": "image", "assetId": str(second_id)}],
                    },
                ]
            }
        ]
    }
    assert collect_asset_ids(document) == {first_id, second_id}
