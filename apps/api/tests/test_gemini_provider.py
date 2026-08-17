from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.generation.gemini_provider import GeneratedOutlineResponse, GoogleAIStudioProvider
from app.generation.provider import (
    GenerationRequest,
    OutlineRequest,
    ProviderResponseError,
    RewriteRequest,
    RewriteTextItem,
    SlideRewriteRequest,
)


class FakeModels:
    def __init__(self, items: list[dict[str, object]]) -> None:
        self.items = items
        self.calls: list[dict[str, object]] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(parsed={"items": self.items}, text=None)


class FakeClient:
    def __init__(self, items: list[dict[str, object]]) -> None:
        self.models = FakeModels(items)


class FailingModels:
    def generate_content(self, **kwargs):
        raise RuntimeError("request rejected for secret")


class RewriteModels:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(parsed={"text": "A clearer, shorter message."}, text=None)


class SlideRewriteModels:
    def __init__(self, items: list[dict[str, str]]) -> None:
        self.items = items
        self.calls: list[dict[str, object]] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(parsed={"items": self.items}, text=None)


def test_google_response_schema_avoids_unsupported_additional_properties() -> None:
    schema = GeneratedOutlineResponse.model_json_schema()
    assert "additionalProperties" not in schema
    item_schema = schema["$defs"]["GeneratedOutlineItem"]
    assert "additionalProperties" not in item_schema
    assert set(item_schema["required"]) == {"title", "content", "layout", "blocks"}
    block_schema = schema["$defs"]["GeneratedSlideBlock"]
    assert "additionalProperties" not in block_schema
    assert set(block_schema["required"]) == {"heading", "body"}


def test_google_ai_studio_generates_owned_outline_shape_without_network() -> None:
    client = FakeClient(
        [
            {"title": "Cloud migration", "content": "A practical migration plan.", "layout": "cover", "blocks": []},
            {"title": "Current state", "content": "The source-grounded summary.", "layout": "split-image", "blocks": []},
        ]
    )
    provider = GoogleAIStudioProvider(api_key="secret", model="chosen-model", client=client)

    items = provider.generate_outline(
        OutlineRequest(
            title="Cloud migration",
            text="Internal source text",
            sections=[],
            language="en",
            slide_count=2,
        )
    )

    assert [item["title"] for item in items] == ["Cloud migration", "Current state"]
    assert len({item["id"] for item in items}) == 2
    assert client.models.calls[0]["model"] == "chosen-model"
    assert "Internal source text" in str(client.models.calls[0]["contents"])
    assert "Do not merely repeat" in str(client.models.calls[0]["contents"])
    assert "not an outline" in str(client.models.calls[0]["contents"])


def test_google_ai_studio_grounds_document_sources_without_prompt_only_policy() -> None:
    client = FakeClient([{"title": "Report", "content": "Grounded summary", "layout": "cover", "blocks": []}])
    provider = GoogleAIStudioProvider(api_key="secret", model="chosen-model", client=client)
    provider.generate_outline(
        OutlineRequest(
            title="Report",
            text="Revenue was 10 units.",
            sections=[],
            language="en",
            slide_count=1,
            source_kind="pdf",
        )
    )
    prompt = str(client.models.calls[0]["contents"])
    assert "specific facts and numbers grounded in the source" in prompt
    assert "Do not merely repeat" not in prompt


def test_google_ai_studio_rejects_wrong_slide_count() -> None:
    provider = GoogleAIStudioProvider(
        api_key="secret",
        model="chosen-model",
        client=FakeClient([{"title": "Only one", "content": "A short deck.", "layout": "cover", "blocks": []}]),
    )
    with pytest.raises(ProviderResponseError, match="exactly 2"):
        provider.generate_outline(
            OutlineRequest(
                title="Deck",
                text="Source",
                sections=[],
                language="en",
                slide_count=2,
            )
        )


def test_google_ai_studio_can_choose_slide_count() -> None:
    client = FakeClient(
        [
            {"title": "Adaptive deck", "content": "A focused introduction.", "layout": "cover", "blocks": []},
            {"title": "One clear idea", "content": "The source only needs one supporting slide.", "layout": "split-image", "blocks": []},
        ]
    )
    provider = GoogleAIStudioProvider(api_key="secret", model="chosen-model", client=client)

    items = provider.generate_outline(
        OutlineRequest(
            title="Adaptive deck",
            text="Explain one narrow idea.",
            sections=[],
            language="en",
            slide_count=None,
        )
    )

    assert len(items) == 2
    prompt = str(client.models.calls[0]["contents"])
    assert "Choose the total slide count yourself" in prompt
    assert "Never exceed 30 slides" in prompt


def test_google_ai_studio_renders_reviewed_outline_without_another_api_call() -> None:
    client = FakeClient([])
    provider = GoogleAIStudioProvider(api_key="secret", model="chosen-model", client=client)
    document = provider.generate(
        GenerationRequest(
            presentation_id=uuid4(),
            title="Reviewed",
            text="Source",
            sections=[],
            language="en",
            slide_count=2,
            outline=[
                {"id": "cover", "title": "Reviewed", "content": ""},
                {"id": "body", "title": "Decision", "content": "Approved content"},
            ],
        )
    )

    assert client.models.calls == []
    assert [slide["title"] for slide in document["slides"]] == ["Reviewed", "Decision"]


def test_google_ai_studio_writes_structured_blocks_into_presenton_slots() -> None:
    client = FakeClient(
        [
            {
                "title": "Trust strategy",
                "content": "A practical plan for durable customer confidence.",
                "layout": "cover",
                "blocks": [],
            },
            {
                "title": "Trust is built through visible actions",
                "content": "Four coordinated practices make reliability tangible.",
                "layout": "feature-list",
                "blocks": [
                    {"heading": "Set clear expectations", "body": "State what customers can rely on."},
                    {"heading": "Show operational proof", "body": "Make service evidence easy to inspect."},
                    {"heading": "Resolve failures openly", "body": "Explain recovery without defensive language."},
                    {"heading": "Measure confidence", "body": "Track whether trust improves after each change."},
                ],
            },
        ]
    )
    provider = GoogleAIStudioProvider(api_key="secret", model="chosen-model", client=client)

    document = provider.generate(
        GenerationRequest(
            presentation_id=uuid4(),
            title="Trust strategy",
            text="Customers need consistent evidence before they trust a service.",
            sections=[],
            language="en",
            slide_count=2,
            theme_id="modern-blue",
        )
    )

    card_titles = [
        element["runs"][0]["text"]
        for element in document["slides"][1]["elements"]
        if str(element.get("name", "")).startswith("card_title")
    ]
    assert card_titles == [
        "Set clear expectations",
        "Show operational proof",
        "Resolve failures openly",
        "Measure confidence",
    ]
    card_bodies = [
        element["runs"][0]["text"]
        for element in document["slides"][1]["elements"]
        if str(element.get("name", "")).startswith("card_description")
    ]
    assert card_bodies == [
        "State what customers can rely on.",
        "Make service evidence easy to inspect.",
        "Explain recovery without defensive language.",
        "Track whether trust improves after each change.",
    ]


def test_google_ai_studio_preserves_selected_theme_during_rendering() -> None:
    provider = GoogleAIStudioProvider(
        api_key="secret",
        model="chosen-model",
        client=FakeClient([{"title": "Warm deck", "content": "A warm introduction.", "layout": "cover", "blocks": []}]),
    )

    document = provider.generate(
        GenerationRequest(
            presentation_id=uuid4(),
            title="Warm deck",
            text="Source",
            sections=[],
            language="en",
            slide_count=1,
            theme_id="warm-studio",
        )
    )

    assert document["theme"]["id"] == "warm-studio"
    assert document["slides"][0]["background"] == "#F2EDE5"


def test_google_ai_studio_redacts_key_from_provider_errors() -> None:
    provider = GoogleAIStudioProvider(
        api_key="secret",
        model="chosen-model",
        client=SimpleNamespace(models=FailingModels()),
    )
    with pytest.raises(ProviderResponseError) as caught:
        provider.generate_outline(
            OutlineRequest(
                title="Deck",
                text="Source",
                sections=[],
                language="en",
                slide_count=1,
            )
        )
    assert "secret" not in str(caught.value)
    assert "[redacted]" in str(caught.value)


def test_google_ai_studio_rewrites_selected_text_without_network() -> None:
    models = RewriteModels()
    provider = GoogleAIStudioProvider(
        api_key="secret",
        model="chosen-model",
        client=SimpleNamespace(models=models),
    )

    rewritten = provider.rewrite_text(
        RewriteRequest(
            text="This is a long and unclear message.",
            instruction="Make it concise",
            language="en",
        )
    )

    assert rewritten == "A clearer, shorter message."
    assert "Make it concise" in str(models.calls[0]["contents"])
    assert "This is a long and unclear message." in str(models.calls[0]["contents"])


def test_google_ai_studio_rewrites_slide_in_original_block_order() -> None:
    models = SlideRewriteModels(
        [
            {"id": "body", "text": "New body"},
            {"id": "title", "text": "New title"},
        ]
    )
    provider = GoogleAIStudioProvider(
        api_key="secret",
        model="chosen-model",
        client=SimpleNamespace(models=models),
    )

    rewritten = provider.rewrite_slide(
        SlideRewriteRequest(
            items=[
                RewriteTextItem(id="title", text="Old title"),
                RewriteTextItem(id="body", text="Old body"),
            ],
            instruction="Make this coherent",
            language="en",
        )
    )

    assert rewritten == [
        RewriteTextItem(id="title", text="New title"),
        RewriteTextItem(id="body", text="New body"),
    ]
    assert "Make this coherent" in str(models.calls[0]["contents"])
    assert '"id": "title"' in str(models.calls[0]["contents"])


def test_google_ai_studio_rejects_changed_slide_text_block_ids() -> None:
    provider = GoogleAIStudioProvider(
        api_key="secret",
        model="chosen-model",
        client=SimpleNamespace(
            models=SlideRewriteModels([{"id": "different", "text": "Changed"}])
        ),
    )

    with pytest.raises(ProviderResponseError, match="identities"):
        provider.rewrite_slide(
            SlideRewriteRequest(
                items=[RewriteTextItem(id="title", text="Original")],
                instruction="Rewrite",
                language="en",
            )
        )
