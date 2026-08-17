import json

from app.generation.company_gateway_provider import CompanyGatewayProvider
from app.generation.provider import OutlineRequest


class FakeResponse:
    status_code = 200
    text = ""

    def __init__(self, content: dict[str, object]) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
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


def test_company_gateway_generates_structured_story_plan() -> None:
    client = FakeClient(
        {
            "items": [
                {
                    "title": "Internal AI",
                    "content": "A concise introduction to the company-hosted model.",
                    "layout": "cover",
                    "blocks": [],
                },
                {
                    "title": "Private inference",
                    "content": "The model runs behind the company gateway.",
                    "layout": "feature-grid",
                    "blocks": [
                        {"heading": "Controlled access", "body": "Consumer keys protect requests."},
                        {"heading": "Local routing", "body": "Traffic enters through the forwarded port."},
                    ],
                },
            ]
        }
    )
    provider = CompanyGatewayProvider(
        base_url="http://127.0.0.1:5000/",
        api_key="consumer-secret",
        model="cb/hnw-llm",
        client=client,
    )

    items = provider.generate_outline(
        OutlineRequest(
            title="Internal AI",
            text="Explain the internal model.",
            sections=[],
            language="en",
            slide_count=None,
        )
    )

    assert len(items) == 2
    assert items[1]["blocks"][0]["heading"] == "Controlled access"
    call = client.calls[0]
    assert call["url"] == "http://127.0.0.1:5000/v1/chat/completions"
    assert call["headers"]["Authorization"] == "Bearer consumer-secret"
    assert call["json"]["model"] == "cb/hnw-llm"


def test_company_gateway_accepts_json_after_reasoning_preamble() -> None:
    client = FakeClient(
        {
            "items": [
                {
                    "title": "One slide",
                    "content": "A complete one-slide response.",
                    "layout": "cover",
                    "blocks": [],
                }
            ]
        }
    )
    original_json = client.response.json

    def response_with_preamble():
        payload = original_json()
        content = payload["choices"][0]["message"]["content"]
        payload["choices"][0]["message"]["content"] = f"<think>planning</think>\n{content}"
        return payload

    client.response.json = response_with_preamble  # type: ignore[method-assign]
    provider = CompanyGatewayProvider(
        base_url="http://127.0.0.1:5000",
        api_key="consumer-secret",
        model="cb/hnw-llm",
        client=client,
    )

    items = provider.generate_outline(
        OutlineRequest(
            title="One slide",
            text="Keep it short.",
            sections=[],
            language="en",
            slide_count=1,
        )
    )

    assert items[0]["title"] == "One slide"
