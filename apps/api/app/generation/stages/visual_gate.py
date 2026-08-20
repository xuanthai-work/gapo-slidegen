from __future__ import annotations

import base64
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

import httpx
from pydantic import BaseModel, ValidationError

from ..llm_schema import llm_json_schema
from ..models import SlideContent
from ..provider import ProviderResponseError

VisualIssueCode = Literal["TEXT_MISSING", "TEXT_TRUNCATED", "TEXT_UNREADABLE"]
_ALLOWED_CODES = frozenset({"TEXT_MISSING", "TEXT_TRUNCATED", "TEXT_UNREADABLE"})

_OCR_SYSTEM = (
    "Return only JSON. Extract visible slide text in reading order. "
    "Do not suggest layouts or repairs."
)
_OCR_USER_PROMPT = (
    "Extract all visible text from this slide screenshot in reading order. "
    "Set unreadable true only if the slide text cannot be read. "
    "Return JSON matching this schema exactly:"
)


class _OcrResponse(BaseModel):
    extracted_text: str = ""
    unreadable: bool = False
    notes: str = ""


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

@dataclass(frozen=True, slots=True)
class VisualIssue:
    code: VisualIssueCode
    message: str
    slot: str | None = None
    element_ids: tuple[str, ...] = ()
    expected: str = ""
    observed: str = ""


@dataclass(frozen=True, slots=True)
class VisualGateResult:
    extracted_text: str
    issues: list[VisualIssue] = field(default_factory=list)

    @property
    def readable(self) -> bool:
        return not self.issues


class VisualGate(Protocol):
    name: str

    def inspect(
        self,
        *,
        png: bytes,
        slide: dict[str, object],
        content: SlideContent,
    ) -> VisualGateResult:
        ...


def intended_slots(content: SlideContent) -> list[tuple[str, str]]:
    slots: list[tuple[str, str]] = []
    title = content.title.strip()
    if title:
        slots.append(("title", title))
    body = content.slots.get("body")
    if isinstance(body, str) and body.strip():
        slots.append(("body", body.strip()))
    items = content.slots.get("items")
    if isinstance(items, list):
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            for field_name in ("heading", "body", "label", "value"):
                value = item.get(field_name)
                if isinstance(value, str) and value.strip():
                    slots.append((f"items.{index}.{field_name}", value.strip()))
    return slots


def normalize_text(value: str) -> str:
    collapsed = " ".join(value.split())
    return unicodedata.normalize("NFC", collapsed).casefold()


def _lcs_len(left: str, right: str) -> int:
    if not left or not right:
        return 0
    previous = [0] * (len(right) + 1)
    for left_ch in left:
        current = [0]
        for index, right_ch in enumerate(right):
            if left_ch == right_ch:
                current.append(previous[index] + 1)
            else:
                current.append(max(previous[index + 1], current[-1]))
        previous = current
    return previous[-1]


def coverage(expected: str, extracted: str) -> float:
    if not expected:
        return 1.0
    if expected in extracted:
        return 1.0
    return _lcs_len(expected, extracted) / len(expected)


def classify_extracted_text(
    *,
    extracted: str,
    unreadable: bool,
    content: SlideContent,
) -> VisualGateResult:
    slots = intended_slots(content)
    observed = normalize_text(extracted)
    if not slots:
        return VisualGateResult(extracted_text=extracted, issues=[])
    concat = normalize_text(" ".join(text for _, text in slots))
    first_slot, first_expected = slots[0]
    if unreadable or (not observed and concat) or (
        len(concat) >= 20 and coverage(concat, observed) < 0.30
    ):
        return VisualGateResult(
            extracted_text=extracted,
            issues=[
                VisualIssue(
                    code="TEXT_UNREADABLE",
                    message=f"Slide text is not readable in the screenshot ({first_slot}).",
                    slot=first_slot,
                    expected=first_expected,
                    observed=extracted,
                )
            ],
        )
    issues: list[VisualIssue] = []
    for slot, expected_raw in slots:
        expected = normalize_text(expected_raw)
        score = coverage(expected, observed)
        code: VisualIssueCode | None = None
        if score < 0.50:
            code = "TEXT_MISSING"
        elif 0.50 <= score < 0.85:
            code = "TEXT_TRUNCATED"
        elif (
            len(expected) >= 24
            and score < 0.95
            and expected[: max(1, len(expected) // 2)] in observed
        ):
            code = "TEXT_TRUNCATED"
        if code is None:
            continue
        issues.append(
            VisualIssue(
                code=code,
                message=f"Slot {slot!r} failed visual readability ({code}).",
                slot=slot,
                expected=expected_raw,
                observed=extracted,
            )
        )
    return VisualGateResult(extracted_text=extracted, issues=issues)


class CompanyGatewayOcrVisualGate:
    """OCR visual gate via the company OpenAI-compatible gateway."""

    name = "company-gateway-ocr"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        chat_path: str = "/v1/chat/completions",
        client: Any | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.chat_path = "/" + chat_path.strip("/")
        self.client = client

    @staticmethod
    def _is_retryable_status(status_code: int) -> bool:
        return status_code in {429, 500, 502, 503, 504}

    def _post_ocr_once(self, client: Any, *, png: bytes) -> str:
        image_url = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
        response = client.post(
            self.base_url + self.chat_path,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": _OCR_SYSTEM},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": _OCR_USER_PROMPT + "\n" + llm_json_schema(_OcrResponse),
                            },
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    },
                ],
                "temperature": 0,
                "max_tokens": 2048,
            },
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ProviderResponseError("Company gateway returned empty model content.")
        return content

    def _chat_ocr(self, *, png: bytes) -> str:
        owns_client = self.client is None
        client = self.client or httpx.Client(timeout=httpx.Timeout(180))
        try:
            for attempt in range(2):
                try:
                    return self._post_ocr_once(client, png=png)
                except httpx.HTTPStatusError as error:
                    status = error.response.status_code
                    if self._is_retryable_status(status) and attempt < 1:
                        time.sleep(1 << attempt)
                        continue
                    raise ProviderResponseError(
                        f"Company gateway request failed: HTTP {status}."
                    ) from error
                except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
                    raise ProviderResponseError(
                        f"Company gateway returned an invalid response: {error}"
                    ) from error
        finally:
            if owns_client:
                client.close()
        raise ProviderResponseError("Company gateway request failed after retries.")

    def inspect(
        self,
        *,
        png: bytes,
        slide: dict[str, object],
        content: SlideContent,
    ) -> VisualGateResult:
        from .orchestrator import SlideValidationFailed

        del slide  # Intentionally unused: never send slide JSON to the model.
        try:
            raw = self._chat_ocr(png=png)
            parsed = _OcrResponse.model_validate_json(_json_object(raw))
        except (ProviderResponseError, ValidationError) as error:
            raise SlideValidationFailed(
                "Slide failed visual validation: VISUAL_GATE_UNAVAILABLE"
            ) from error
        return classify_extracted_text(
            extracted=parsed.extracted_text,
            unreadable=parsed.unreadable,
            content=content,
        )
