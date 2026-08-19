"""Content understanding implementation for the generation pipeline.

The gateway-based implementation asks the configured LLM to extract intent,
audience, tone, and key takeaways from a source so downstream prompts can
produce focused, audience-aware slide copy.
"""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from ..llm_schema import llm_json_schema
from ..provider import ProviderResponseError
from .models import ContentUnderstandingResult
from .protocols import ContentUnderstanding


class _UnderstandingResponse(BaseModel):
    intent: str = Field(min_length=1, max_length=300)
    audience: str = Field(min_length=1, max_length=300)
    tone: str = Field(min_length=1, max_length=200)
    key_takeaways: list[str] = Field(min_length=1, max_length=8)


def _extract_json_object(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.removeprefix("```json").removeprefix("```")
        stripped = stripped.removesuffix("```").strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end < start:
        raise ProviderResponseError("Content understanding returned text instead of a JSON object.")
    return stripped[start : end + 1]


class StubContentUnderstanding:
    """Deterministic no-op understanding used when no LLM is configured."""

    name = "stub"

    def understand(
        self,
        *,
        title: str,
        text: str,
        sections: list[dict[str, object]],
        language: str,
        source_kind: str,
    ) -> ContentUnderstandingResult | None:
        del title, text, sections, language, source_kind
        return None


class CompanyGatewayContentUnderstanding:
    """Extracts audience-aware context from the source via the company gateway."""

    name = "company-gateway"

    def __init__(self, provider: Any) -> None:
        self.provider = provider

    def _build_prompt(
        self,
        *,
        title: str,
        text: str,
        sections: list[dict[str, object]],
        language: str,
        source_kind: str,
    ) -> tuple[str, str]:
        # Match the outline stage's input window so the understanding that
        # steers the outline is derived from the same source slice the
        # outline actually sees. The provider exposes the configured limit.
        max_input_chars = getattr(self.provider, "max_input_chars", 120_000)
        source_kind_instruction = (
            "The user provided a creative request or prompt. Infer what the deck is likely about, who would care, and what tone would resonate."
            if source_kind == "prompt"
            else "The user supplied material. Extract the intent, audience, tone, and key takeaways directly from the source."
        )
        sections_text = "\n".join(
            f"- {section.get('title')}: {section.get('text')}"
            for section in sections
            if isinstance(section, dict)
        )
        if language == "vi":
            system = (
                "Bạn là chuyên gia phân tích nội dung thuyết trình. "
                "Trả về JSON duy nhất theo schema được cung cấp. Không bọc JSON trong Markdown."
            )
            user = (
                f"Phân tích nguồn dưới đây để xác định:\n"
                f"1. intent: mục đích chính của bài thuyết trình (1 câu)\n"
                f"2. audience: đối tượng chính và trình độ hiểu biết của họ\n"
                f"3. tone: giọng điệu phù hợp (ví dụ: chuyên nghiệp, thân thiện, quyết đoán, truyền cảm)\n"
                f"4. key_takeaways: 3-6 điểm chính người xem cần nhớ\n\n"
                f"Tiêu đề: {title}\n"
                f"{source_kind_instruction}\n\n"
                f"Nội dung nguồn:\n{text[:max_input_chars]}\n"
            )
            if sections_text:
                user += f"\nCác mục đã cung cấp:\n{sections_text}\n"
        else:
            system = (
                "You are a presentation content analyst. "
                "Return only valid JSON matching the provided schema. Never wrap JSON in Markdown."
            )
            user = (
                f"Analyze the source below to determine:\n"
                f"1. intent: the primary purpose of the deck (one sentence)\n"
                f"2. audience: the main audience and their level of understanding\n"
                f"3. tone: the appropriate tone (e.g. professional, friendly, decisive, inspiring)\n"
                f"4. key_takeaways: 3-6 key points the audience should remember\n\n"
                f"Title: {title}\n"
                f"{source_kind_instruction}\n\n"
                f"Source content:\n{text[:max_input_chars]}\n"
            )
            if sections_text:
                user += f"\nProvided sections:\n{sections_text}\n"
        return system, user

    def understand(
        self,
        *,
        title: str,
        text: str,
        sections: list[dict[str, object]],
        language: str,
        source_kind: str,
    ) -> ContentUnderstandingResult | None:
        schema = llm_json_schema(_UnderstandingResponse)
        system, user = self._build_prompt(
            title=title,
            text=text,
            sections=sections,
            language=language,
            source_kind=source_kind,
        )
        try:
            content = self.provider._chat(
                system=system,
                user=f"{user}\nReturn JSON matching this schema exactly:\n{schema}",
                timeout=httpx.Timeout(30),
            )
            response = _UnderstandingResponse.model_validate_json(_extract_json_object(content))
        except (ValidationError, ProviderResponseError) as error:
            raise ProviderResponseError(
                "Content understanding could not extract a valid summary."
            ) from error
        return ContentUnderstandingResult(
            intent=response.intent,
            audience=response.audience,
            tone=response.tone,
            key_takeaways=response.key_takeaways,
        )


def build_content_understanding(provider: Any | None = None) -> ContentUnderstanding:
    """Factory for the content understanding stage.

    Accepts an optional chat-provider instance that exposes a ``_chat`` method
    (typically the configured story planner). When no provider is supplied, or
    the provider cannot chat, returns a deterministic stub that lets the
    pipeline run without making extra LLM calls.
    """
    if provider is None or not hasattr(provider, "_chat"):
        return StubContentUnderstanding()
    return CompanyGatewayContentUnderstanding(provider=provider)
