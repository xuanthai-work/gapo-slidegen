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
    assert any(element["type"] == "text" for element in slides[1]["elements"])


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


def test_stub_provider_uses_reviewed_outline_verbatim() -> None:
    document = StubPresentationProvider().generate(
        GenerationRequest(
            presentation_id=uuid4(),
            title="Original title",
            text="Original text",
            sections=[],
            language="en",
            slide_count=2,
            outline=[
                {"id": "cover", "title": "Reviewed cover", "content": ""},
                {"id": "detail", "title": "Reviewed point", "content": "Reviewed content"},
            ],
        )
    )
    assert [slide["title"] for slide in document["slides"]] == [
        "Reviewed cover",
        "Reviewed point",
    ]


def test_stub_renderer_applies_theme_and_varied_editable_layouts() -> None:
    document = StubPresentationProvider().generate(
        GenerationRequest(
            presentation_id=uuid4(),
            title="Designed deck",
            text="Source",
            sections=[],
            language="en",
            slide_count=4,
            theme_id="warm-studio",
            outline=[
                {"id": "cover", "title": "Designed deck", "content": "A clear story"},
                {"id": "one", "title": "First", "content": "First body"},
                {"id": "two", "title": "Second", "content": "Second body"},
                {"id": "three", "title": "Third", "content": "Third body"},
            ],
        )
    )

    assert document["theme"]["id"] == "warm-studio"
    assert len({slide["background"] for slide in document["slides"]}) >= 2
    assert document["slides"][2]["elements"][0]["type"] == "shape"
    assert all(element["type"] in {"text", "shape"} for slide in document["slides"] for element in slide["elements"])


def test_themes_change_composition_not_only_colors() -> None:
    outline = [
        {"id": "cover", "title": "Design system", "content": "A practical field guide"},
        {"id": "one", "title": "Build a shared language", "content": "Use a small set of decisions so teams can move quickly while preserving quality."},
    ]
    documents = [
        StubPresentationProvider().generate(
            GenerationRequest(
                presentation_id=uuid4(),
                title="Design system",
                text="Source",
                sections=[],
                language="en",
                slide_count=2,
                theme_id=theme_id,
                outline=outline,
            )
        )
        for theme_id in ("editorial-cobalt", "warm-studio", "midnight-signal")
    ]

    cover_signatures = {
        tuple(
            (element["type"], element["position"]["x"], element["position"]["y"])
            for element in document["slides"][0]["elements"]
        )
        for document in documents
    }
    content_signatures = {
        tuple(
            (element["type"], element["position"]["x"], element["position"]["y"])
            for element in document["slides"][1]["elements"]
        )
        for document in documents
    }

    assert len(cover_signatures) == 3
    assert len(content_signatures) == 3


def test_renderer_uses_six_layout_archetypes_and_keeps_elements_on_canvas() -> None:
    outline = [{"id": "cover", "title": "Layout study", "content": ""}]
    outline.extend(
        {
            "id": f"slide-{index}",
            "title": f"Chapter {index}",
            "content": "A useful explanation with enough detail to use a standard content layout.",
        }
        for index in range(1, 7)
    )
    document = StubPresentationProvider().generate(
        GenerationRequest(
            presentation_id=uuid4(),
            title="Layout study",
            text="Source",
            sections=[],
            language="en",
            slide_count=7,
            outline=outline,
        )
    )

    signatures = {
        tuple((element["type"], element["position"]["x"], element["position"]["y"]) for element in slide["elements"])
        for slide in document["slides"][1:]
    }
    assert len(signatures) == 6
    for slide in document["slides"]:
        for element in slide["elements"]:
            assert element["position"]["x"] >= 0
            assert element["position"]["y"] >= 0
            assert element["position"]["x"] + element["size"]["width"] <= 1280
            assert element["position"]["y"] + element["size"]["height"] <= 720
