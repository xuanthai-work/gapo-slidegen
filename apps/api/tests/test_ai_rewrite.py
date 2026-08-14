from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.generation.provider import (
    ProviderConfigurationError,
    RewriteRequest,
    RewriteTextItem,
    SlideRewriteRequest,
)
from app.generation.router import get_rewrite_provider
from app.main import app


class FakeRewriteProvider:
    name = "fake-ai"

    def __init__(self) -> None:
        self.requests: list[RewriteRequest] = []
        self.slide_requests: list[SlideRewriteRequest] = []

    def rewrite_text(self, request: RewriteRequest) -> str:
        self.requests.append(request)
        return "Rewritten for the slide."

    def rewrite_slide(self, request: SlideRewriteRequest) -> list[RewriteTextItem]:
        self.slide_requests.append(request)
        return [RewriteTextItem(id=item.id, text=f"Rewritten: {item.text}") for item in request.items]


class UnavailableRewriteProvider:
    name = "stub"

    def rewrite_text(self, request: RewriteRequest) -> str:
        raise ProviderConfigurationError("AI rewrite is unavailable.")

    def rewrite_slide(self, request: SlideRewriteRequest) -> list[RewriteTextItem]:
        raise ProviderConfigurationError("AI rewrite is unavailable.")


def test_rewrite_route_uses_authenticated_backend_provider() -> None:
    provider = FakeRewriteProvider()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user")
    app.dependency_overrides[get_rewrite_provider] = lambda: provider
    try:
        response = TestClient(app).post(
            "/v1/ai/rewrite",
            json={
                "text": "Long original text",
                "instruction": "Make it concise",
                "language": "en",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"text": "Rewritten for the slide.", "provider": "fake-ai"}
    assert provider.requests == [
        RewriteRequest(
            text="Long original text",
            instruction="Make it concise",
            language="en",
        )
    ]


def test_rewrite_route_reports_unavailable_provider() -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user")
    app.dependency_overrides[get_rewrite_provider] = lambda: UnavailableRewriteProvider()
    try:
        response = TestClient(app).post(
            "/v1/ai/rewrite",
            json={"text": "Original", "instruction": "Rewrite", "language": "en"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == "AI rewrite is unavailable."


def test_rewrite_slide_route_preserves_text_block_identities() -> None:
    provider = FakeRewriteProvider()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user")
    app.dependency_overrides[get_rewrite_provider] = lambda: provider
    try:
        response = TestClient(app).post(
            "/v1/ai/rewrite-slide",
            json={
                "items": [
                    {"id": "title", "text": "Original title"},
                    {"id": "body", "text": "Original body"},
                ],
                "instruction": "Make the slide concise",
                "language": "en",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"id": "title", "text": "Rewritten: Original title"},
            {"id": "body", "text": "Rewritten: Original body"},
        ],
        "provider": "fake-ai",
    }
    assert provider.slide_requests == [
        SlideRewriteRequest(
            items=[
                RewriteTextItem(id="title", text="Original title"),
                RewriteTextItem(id="body", text="Original body"),
            ],
            instruction="Make the slide concise",
            language="en",
        )
    ]


def test_rewrite_slide_route_rejects_duplicate_text_block_ids() -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user")
    app.dependency_overrides[get_rewrite_provider] = FakeRewriteProvider
    try:
        response = TestClient(app).post(
            "/v1/ai/rewrite-slide",
            json={
                "items": [
                    {"id": "duplicate", "text": "Title"},
                    {"id": "duplicate", "text": "Body"},
                ],
                "instruction": "Rewrite",
                "language": "en",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
