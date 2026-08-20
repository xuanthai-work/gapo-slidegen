from types import SimpleNamespace
from uuid import uuid4

from app.generation.company_gateway_provider import CompanyGatewayProvider
from app.generation.provider import GenerationRequest, OutlineRequest
from app.generation.stages import GenerationPipeline
from app.generation.stages.content_generator import ThemeDispatchContentGenerator
from app.generation.stages.orchestrator import NullAssetGenerator, NullAssetPlanner


class FakeHttpClient:
    """Minimal httpx-like client that returns a pre-canned chat response."""

    def __init__(self, items: list[dict[str, object]]) -> None:
        self.items = items
        self.calls: list[dict[str, object]] = []

    def post(self, _url: str, **kwargs):
        self.calls.append(kwargs)
        payload = {
            "choices": [
                {"message": {"content": self._as_json(self.items)}}
            ]
        }
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: payload,
        )

    def close(self) -> None:
        pass

    @staticmethod
    def _as_json(items: list[dict[str, object]]) -> str:
        return __import__("json").dumps({"items": items}, ensure_ascii=False)


class FailingHttpClient:
    def post(self, _url: str, **kwargs):
        raise RuntimeError("request rejected for secret")

    def close(self) -> None:
        pass


def _build_pipeline(client: FakeHttpClient) -> GenerationPipeline:
    planner = CompanyGatewayProvider(
        base_url="http://gateway",
        api_key="secret",
        model="chosen-model",
        client=client,
    )
    return GenerationPipeline(
        story_planner=planner,
        content_generator=ThemeDispatchContentGenerator(),
        asset_planner=NullAssetPlanner(),
        asset_generator=NullAssetGenerator(),
    )


def test_pipeline_renders_reviewed_outline_without_another_api_call() -> None:
    client = FakeHttpClient([])
    pipeline = _build_pipeline(client)
    document = pipeline.generate(
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

    assert client.calls == []
    assert [slide["title"] for slide in document["slides"]] == ["Reviewed", "Decision"]


def test_pipeline_writes_structured_blocks_into_presenton_slots() -> None:
    client = FakeHttpClient(
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
    pipeline = _build_pipeline(client)
    document = pipeline.generate(
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


def test_pipeline_preserves_selected_theme_during_rendering() -> None:
    client = FakeHttpClient(
        [{"title": "Warm deck", "content": "A warm introduction.", "layout": "cover", "blocks": []}]
    )
    pipeline = _build_pipeline(client)
    document = pipeline.generate(
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

    assert document["theme"]["id"] == "executive:edge-yellow"
    assert document["slides"][0]["background"] == "#1F1F1F"


def test_pipeline_rejects_wrong_slide_count_from_gateway() -> None:
    client = FakeHttpClient(
        [{"title": "Only one", "content": "A short deck.", "layout": "cover", "blocks": []}]
    )
    pipeline = _build_pipeline(client)
    from app.generation.provider import ProviderResponseError

    with __import__("pytest").raises(ProviderResponseError, match="exactly 2"):
        pipeline.generate(
            GenerationRequest(
                presentation_id=uuid4(),
                title="Deck",
                text="Source",
                sections=[],
                language="en",
                slide_count=2,
            )
        )
