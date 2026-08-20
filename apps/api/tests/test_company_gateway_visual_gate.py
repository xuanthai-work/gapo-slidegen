import json

import httpx
import pytest

from app.generation.models import SlideContent
from app.generation.stages.orchestrator import SlideValidationFailed
from app.generation.stages.visual_gate import CompanyGatewayOcrVisualGate


class FakeResponse:
    status_code = 200
    text = ""

    def __init__(
        self,
        content: dict[str, object] | None = None,
        *,
        raw_message: str | None = None,
        status_code: int = 200,
        text: str = "",
    ) -> None:
        self.content = content
        self.raw_message = raw_message
        self.status_code = status_code
        self.text = text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://127.0.0.1:5000/v1/chat/completions")
            response = httpx.Response(self.status_code, request=request, text=self.text)
            raise httpx.HTTPStatusError(
                "request failed", request=request, response=response
            )

    def json(self) -> dict[str, object]:
        if self.raw_message is not None:
            return {"choices": [{"message": {"content": self.raw_message}}]}
        assert self.content is not None
        return {
            "choices": [
                {"message": {"content": json.dumps(self.content, ensure_ascii=False)}}
            ]
        }


class FakeClient:
    def __init__(self, content: dict[str, object]) -> None:
        self.response = FakeResponse(content)
        self.calls: list[dict[str, object]] = []

    def post(self, url: str, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.response


class SequenceClient:
    def __init__(self, *responses: FakeResponse) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def post(self, url: str, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.responses.pop(0)


def _gate(**overrides: object) -> CompanyGatewayOcrVisualGate:
    kwargs: dict[str, object] = {
        "base_url": "http://127.0.0.1:5000",
        "api_key": "secret",
        "model": "ocr-vision",
        "chat_path": "/v1/chat/completions",
    }
    kwargs.update(overrides)
    return CompanyGatewayOcrVisualGate(**kwargs)


def _content() -> SlideContent:
    return SlideContent(
        slide_id="s1",
        title="Quarterly Review",
        layout_id="list",
        slots={"body": "Visible body copy."},
    )


def test_ocr_gate_sends_image_url_and_classifies() -> None:
    client = FakeClient(
        {
            "extracted_text": "Quarterly Review Visible body copy.",
            "unreadable": False,
            "notes": "",
        }
    )
    gate = _gate(client=client)

    result = gate.inspect(png=b"\x89PNG\r\n\x1a\n", slide={"id": "s1"}, content=_content())

    assert result.readable
    assert result.extracted_text == "Quarterly Review Visible body copy."
    call = client.calls[0]
    assert call["url"] == "http://127.0.0.1:5000/v1/chat/completions"
    assert call["headers"]["Authorization"] == "Bearer secret"
    payload = call["json"]
    assert payload["model"] == "ocr-vision"
    assert payload["temperature"] == 0
    assert payload["max_tokens"] == 2048
    assert payload["messages"][0]["role"] == "system"
    user = payload["messages"][1]["content"]
    assert any(part.get("type") == "image_url" for part in user)
    image = next(part for part in user if part.get("type") == "image_url")
    assert image["image_url"]["url"].startswith("data:image/png;base64,")
    serialized = json.dumps(payload)
    assert '"id": "s1"' not in serialized
    assert "layout_id" not in serialized


def test_ocr_gate_invalid_json_raises_slide_validation_failed() -> None:
    client = SequenceClient(FakeResponse(raw_message="not-json"))
    gate = _gate(client=client)

    with pytest.raises(SlideValidationFailed, match="VISUAL_GATE_UNAVAILABLE"):
        gate.inspect(png=b"\x89PNG\r\n\x1a\n", slide={"id": "s1"}, content=_content())


def test_ocr_gate_retries_once_on_retryable_status(monkeypatch) -> None:
    monkeypatch.setattr("app.generation.stages.visual_gate.time.sleep", lambda *_: None)
    client = SequenceClient(
        FakeResponse(status_code=503, text="temporary"),
        FakeResponse(
            {
                "extracted_text": "Quarterly Review Visible body copy.",
                "unreadable": False,
                "notes": "",
            }
        ),
    )
    gate = _gate(client=client)

    result = gate.inspect(png=b"\x89PNG\r\n\x1a\n", slide={"id": "s1"}, content=_content())

    assert result.readable
    assert len(client.calls) == 2


def test_ocr_gate_http_fail_after_retry_raises_unavailable(monkeypatch) -> None:
    monkeypatch.setattr("app.generation.stages.visual_gate.time.sleep", lambda *_: None)
    client = SequenceClient(
        FakeResponse(status_code=503, text="temporary"),
        FakeResponse(status_code=503, text="still down"),
    )
    gate = _gate(client=client)

    with pytest.raises(SlideValidationFailed, match="VISUAL_GATE_UNAVAILABLE"):
        gate.inspect(png=b"\x89PNG\r\n\x1a\n", slide={"id": "s1"}, content=_content())

    assert len(client.calls) == 2
