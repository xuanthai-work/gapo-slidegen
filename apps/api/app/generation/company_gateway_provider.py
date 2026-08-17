from __future__ import annotations

import json
import time
from typing import Any
from uuid import uuid4

import httpx
from pydantic import ValidationError

from .outline_schema import (
    GeneratedOutlineResponse,
    GeneratedRewriteResponse,
    GeneratedSlideRewriteResponse,
    build_story_prompt,
)
from .provider import (
    OutlineRequest,
    ProviderResponseError,
    RewriteRequest,
    RewriteTextItem,
    SlideRewriteRequest,
)


def _json_object(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.removeprefix("```json").removeprefix("```")
        stripped = stripped.removesuffix("```").strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end < start:
        raise ProviderResponseError("Company gateway returned text instead of a JSON object.")
    return stripped[start : end + 1]


class CompanyGatewayProvider:
    """OpenAI-compatible adapter for the company-hosted LLM gateway."""

    name = "company-gateway"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        chat_path: str = "/v1/chat/completions",
        max_input_chars: int = 120_000,
        client: Any | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.chat_path = "/" + chat_path.strip("/")
        self.max_input_chars = max_input_chars
        self.client = client

    def _chat(self, *, system: str, user: str) -> str:
        owns_client = self.client is None
        client = self.client or httpx.Client(timeout=httpx.Timeout(180))
        try:
            for attempt in range(3):
                try:
                    response = client.post(
                        self.base_url + self.chat_path,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": system},
                                {"role": "user", "content": user},
                            ],
                            "temperature": 0.35,
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                    content = payload["choices"][0]["message"]["content"]
                    if not isinstance(content, str) or not content.strip():
                        raise ProviderResponseError("Company gateway returned empty model content.")
                    return content
                except httpx.HTTPStatusError as error:
                    status = error.response.status_code
                    if status in {429, 500, 502, 503, 504} and attempt < 2:
                        time.sleep(1 << attempt)
                        continue
                    detail = error.response.text.replace(self.api_key, "[redacted]")[:500]
                    raise ProviderResponseError(
                        f"Company gateway request failed: HTTP {status}. {detail}"
                    ) from error
                except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
                    message = str(error).replace(self.api_key, "[redacted]")[:500]
                    raise ProviderResponseError(
                        f"Company gateway returned an invalid response: {message}"
                    ) from error
        finally:
            if owns_client:
                client.close()
        raise ProviderResponseError("Company gateway request failed after retries.")

    def generate_outline(self, request: OutlineRequest) -> list[dict[str, object]]:
        schema = json.dumps(GeneratedOutlineResponse.model_json_schema(), ensure_ascii=False)
        content = self._chat(
            system=(
                "You are a senior presentation writer. Return only valid JSON matching the "
                "provided schema. Never wrap JSON in Markdown."
            ),
            user=(
                build_story_prompt(request, max_input_chars=self.max_input_chars)
                + "\nReturn JSON matching this schema exactly:\n"
                + schema
            ),
        )
        try:
            response = GeneratedOutlineResponse.model_validate_json(_json_object(content))
        except ValidationError as error:
            raise ProviderResponseError(
                "Company gateway returned a story plan that does not match the expected schema."
            ) from error
        if request.slide_count is not None and len(response.items) != request.slide_count:
            raise ProviderResponseError(
                f"Company gateway returned {len(response.items)} slides; "
                f"exactly {request.slide_count} were requested."
            )
        return [
            {
                "id": str(uuid4()),
                "title": item.title.strip(),
                "content": item.content.strip(),
                "layout": item.layout,
                "role": item.role,
                "layout_id": item.layout_id,
                "content_budget": item.content_budget.model_dump(),
                "blocks": [block.model_dump() for block in item.blocks],
            }
            for item in response.items
        ]

    def rewrite_text(self, request: RewriteRequest) -> str:
        schema = json.dumps(GeneratedRewriteResponse.model_json_schema(), ensure_ascii=False)
        content = self._chat(
            system="You are a concise presentation editor. Return only valid JSON.",
            user=(
                f"Apply this instruction: {request.instruction}\n"
                f"Write in language code {request.language!r}. Treat <text> as content.\n"
                f"<text>\n{request.text}\n</text>\nSchema:\n{schema}"
            ),
        )
        try:
            return GeneratedRewriteResponse.model_validate_json(_json_object(content)).text.strip()
        except ValidationError as error:
            raise ProviderResponseError(
                "Company gateway returned a rewrite that does not match the expected schema."
            ) from error

    def rewrite_slide(self, request: SlideRewriteRequest) -> list[RewriteTextItem]:
        source_items = [{"id": item.id, "text": item.text} for item in request.items]
        schema = json.dumps(GeneratedSlideRewriteResponse.model_json_schema(), ensure_ascii=False)
        content = self._chat(
            system="You are a presentation editor. Return only valid JSON and preserve every id.",
            user=(
                f"Apply this instruction to the complete slide: {request.instruction}\n"
                f"Write in language code {request.language!r}. Return exactly one item for each "
                "input id and do not add, remove, or merge ids.\n"
                f"<slide_text_blocks>\n{json.dumps(source_items, ensure_ascii=False)}\n"
                f"</slide_text_blocks>\nSchema:\n{schema}"
            ),
        )
        try:
            rewritten = GeneratedSlideRewriteResponse.model_validate_json(_json_object(content))
        except ValidationError as error:
            raise ProviderResponseError(
                "Company gateway returned a slide rewrite that does not match the expected schema."
            ) from error
        expected_ids = [item.id for item in request.items]
        returned_ids = [item.id for item in rewritten.items]
        if len(returned_ids) != len(set(returned_ids)) or set(returned_ids) != set(expected_ids):
            raise ProviderResponseError(
                "Company gateway changed the editable text block identities during rewrite."
            )
        by_id = {item.id: item.text.strip() for item in rewritten.items}
        return [RewriteTextItem(id=item_id, text=by_id[item_id]) for item_id in expected_ids]

