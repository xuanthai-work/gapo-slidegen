from uuid import uuid4

from app.generation.provider import GenerationRequest
from app.generation.stub_provider import StubPresentationProvider


def test_stub_provider_outputs_canonical_editable_document() -> None:
    presentation_id = uuid4()
    document = StubPresentationProvider().generate(
        GenerationRequest(
            presentation_id=presentation_id,
            title="Quarterly review",
            text="Revenue grew while onboarding time decreased.",
            sections=[
                {"index": 0, "title": "Revenue", "text": "Revenue grew."},
                {"index": 1, "title": "Onboarding", "text": "Onboarding time decreased."},
            ],
            language="en",
            slide_count=3,
        )
    )

    assert document["id"] == str(presentation_id)
    assert document["schemaVersion"] == 1
    slides = document["slides"]
    assert isinstance(slides, list)
    assert len(slides) == 3
    assert slides[1]["elements"][0]["type"] == "text"


def test_stub_provider_respects_thirty_slide_limit_input() -> None:
    document = StubPresentationProvider().generate(
        GenerationRequest(
            presentation_id=uuid4(),
            title="Long deck",
            text=" ".join(f"word-{index}" for index in range(600)),
            sections=[],
            language="en",
            slide_count=30,
        )
    )
    assert len(document["slides"]) == 30
