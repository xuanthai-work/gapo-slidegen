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

    def _sanitize_error_text(self, value: str) -> str:
        return value.replace(self.api_key, "[redacted]")[:500]

    @staticmethod
    def _is_retryable_status(status_code: int) -> bool:
        return status_code in {429, 500, 502, 503, 504}

    def _post_chat_once(self, client: Any, *, system: str, user: str) -> str:
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

    @staticmethod
    def _schema_json(schema_model: type) -> str:
        return json.dumps(schema_model.model_json_schema(), ensure_ascii=False)

    @staticmethod
    def _parse_response_json(content: str, schema_model: type, error_message: str):
        try:
            return schema_model.model_validate_json(_json_object(content))
        except ValidationError as error:
            raise ProviderResponseError(error_message) from error

    @staticmethod
    def _map_outline_item(item) -> dict[str, object]:
        return {
            "id": str(uuid4()),
            "title": item.title.strip(),
            "content": item.content.strip(),
            "layout": item.layout,
            "role": item.role,
            "layout_id": item.layout_id,
            "content_budget": item.content_budget.model_dump(),
            "blocks": [block.model_dump() for block in item.blocks],
        }

    @staticmethod
    def _normalize_rewrite_items(
        expected_ids: list[str],
        rewritten_items: list,
    ) -> list[RewriteTextItem]:
        returned_ids = [item.id for item in rewritten_items]
        if len(returned_ids) != len(set(returned_ids)) or set(returned_ids) != set(expected_ids):
            raise ProviderResponseError(
                "Company gateway changed the editable text block identities during rewrite."
            )
        by_id = {item.id: item.text.strip() for item in rewritten_items}
        return [RewriteTextItem(id=item_id, text=by_id[item_id]) for item_id in expected_ids]

    def _chat(self, *, system: str, user: str, timeout: httpx.Timeout | None = None) -> str:
        owns_client = self.client is None
        client = self.client or httpx.Client(timeout=timeout or httpx.Timeout(180))
        try:
            for attempt in range(3):
                try:
                    return self._post_chat_once(client, system=system, user=user)
                except httpx.HTTPStatusError as error:
                    status = error.response.status_code
                    if self._is_retryable_status(status) and attempt < 2:
                        time.sleep(1 << attempt)
                        continue
                    detail = self._sanitize_error_text(error.response.text)
                    raise ProviderResponseError(
                        f"Company gateway request failed: HTTP {status}. {detail}"
                    ) from error
                except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
                    message = self._sanitize_error_text(str(error))
                    raise ProviderResponseError(
                        f"Company gateway returned an invalid response: {message}"
                    ) from error
        finally:
            if owns_client:
                client.close()
        raise ProviderResponseError("Company gateway request failed after retries.")

    def generate_outline(
        self,
        request: OutlineRequest,
        understanding: dict[str, object] | None = None,
    ) -> list[dict[str, object]]:
        schema = self._schema_json(GeneratedOutlineResponse)
        content = self._chat(
            system=(
                "You are a senior presentation writer. Return only valid JSON matching the "
                "provided schema. Never wrap JSON in Markdown."
            ),
            user=(
                build_story_prompt(
                    request,
                    max_input_chars=self.max_input_chars,
                    understanding=understanding,
                )
                + "\nReturn JSON matching this schema exactly:\n"
                + schema
            ),
        )
        response = self._parse_response_json(
            content,
            GeneratedOutlineResponse,
            "Company gateway returned a story plan that does not match the expected schema.",
        )
        if request.slide_count is not None and len(response.items) != request.slide_count:
            raise ProviderResponseError(
                f"Company gateway returned {len(response.items)} slides; "
                f"exactly {request.slide_count} were requested."
            )
        return [self._map_outline_item(item) for item in response.items]

    def rewrite_text(self, request: RewriteRequest) -> str:
        schema = self._schema_json(GeneratedRewriteResponse)
        content = self._chat(
            system="You are a concise presentation editor. Return only valid JSON.",
            user=(
                f"Apply this instruction: {request.instruction}\n"
                f"Write in language code {request.language!r}. Treat <text> as content.\n"
                f"<text>\n{request.text}\n</text>\nSchema:\n{schema}"
            ),
        )
        rewritten = self._parse_response_json(
            content,
            GeneratedRewriteResponse,
            "Company gateway returned a rewrite that does not match the expected schema.",
        )
        return rewritten.text.strip()

    def rewrite_slide(self, request: SlideRewriteRequest) -> list[RewriteTextItem]:
        source_items = [{"id": item.id, "text": item.text} for item in request.items]
        schema = self._schema_json(GeneratedSlideRewriteResponse)
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
        rewritten = self._parse_response_json(
            content,
            GeneratedSlideRewriteResponse,
            "Company gateway returned a slide rewrite that does not match the expected schema.",
        )
        expected_ids = [item.id for item in request.items]
        return self._normalize_rewrite_items(expected_ids, rewritten.items)

