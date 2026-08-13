from typing import NoReturn

from google import genai
from google.genai import errors as google_errors
from google.genai import types as google_types
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)
from pydantic import ValidationError

from app.ai.base import ProviderFailure, ProviderFailureKind
from app.schemas.presentation import Outline
from app.schemas.slide import SlideContent

SYSTEM_INSTRUCTION = """You create concise, professional presentation outlines.
Return only the requested structured data. Never invent statistics, quotations, or
claims that are not supplied by the user. Do not output HTML or code. Use unique,
lowercase kebab-case slide IDs. Keep slide titles short and key points distinct."""


def outline_prompt(*, prompt: str, language: str, slide_count: int) -> str:
    language_name = "English" if language == "en" else "Vietnamese"
    return f"""Create exactly {slide_count} slides in {language_name}.
The deck needs a clear narrative: opening, structured development, and conclusion.
Each slide must have 2-5 concise key points. The presentation request is:

{prompt}"""


class GoogleAIProvider:
    name = "google"

    def __init__(self, *, api_key: str, model: str) -> None:
        self.model = model
        self.client = genai.Client(api_key=api_key)

    async def generate_outline(
        self, *, prompt: str, language: str, slide_count: int
    ) -> Outline:
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=outline_prompt(
                    prompt=prompt, language=language, slide_count=slide_count
                ),
                config=google_types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.3,
                    response_mime_type="application/json",
                    response_schema=Outline,
                ),
            )
            if response.parsed is not None:
                return Outline.model_validate(response.parsed)
            if not response.text:
                raise ProviderFailure(
                    ProviderFailureKind.POLICY_REFUSAL,
                    "Gemini returned no outline",
                )
            return Outline.model_validate_json(response.text)
        except ProviderFailure:
            raise
        except ValidationError as error:
            raise ProviderFailure(
                ProviderFailureKind.INVALID_RESPONSE, "Gemini returned an invalid outline"
            ) from error
        except google_errors.APIError as error:
            _raise_google_failure(error)

    async def generate_slide(
        self, *, outline: Outline, slide_index: int, theme_key: str
    ) -> SlideContent:
        del outline, slide_index, theme_key
        raise ProviderFailure(ProviderFailureKind.INTERNAL, "Slide generation is not ready")


class OpenAIProvider:
    name = "openai"

    def __init__(self, *, api_key: str, model: str) -> None:
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate_outline(
        self, *, prompt: str, language: str, slide_count: int
    ) -> Outline:
        try:
            response = await self.client.responses.parse(
                model=self.model,
                instructions=SYSTEM_INSTRUCTION,
                input=outline_prompt(
                    prompt=prompt, language=language, slide_count=slide_count
                ),
                text_format=Outline,
                temperature=0.3,
            )
            if response.output_parsed is None:
                raise ProviderFailure(
                    ProviderFailureKind.POLICY_REFUSAL,
                    "OpenAI returned no outline",
                )
            return response.output_parsed
        except ProviderFailure:
            raise
        except ValidationError as error:
            raise ProviderFailure(
                ProviderFailureKind.INVALID_RESPONSE, "OpenAI returned an invalid outline"
            ) from error
        except (APITimeoutError, APIConnectionError, APIStatusError) as error:
            _raise_openai_failure(error)

    async def generate_slide(
        self, *, outline: Outline, slide_index: int, theme_key: str
    ) -> SlideContent:
        del outline, slide_index, theme_key
        raise ProviderFailure(ProviderFailureKind.INTERNAL, "Slide generation is not ready")


def _raise_google_failure(error: google_errors.APIError) -> NoReturn:
    if error.code == 429:
        kind = ProviderFailureKind.RATE_LIMIT
    elif error.code >= 500:
        kind = ProviderFailureKind.UNAVAILABLE
    elif error.code in {401, 403}:
        kind = ProviderFailureKind.AUTHENTICATION
    else:
        kind = ProviderFailureKind.INVALID_REQUEST
    raise ProviderFailure(kind, f"Google API request failed ({error.code})") from error


def _raise_openai_failure(error: Exception) -> NoReturn:
    if isinstance(error, APITimeoutError):
        kind = ProviderFailureKind.TIMEOUT
    elif isinstance(error, APIConnectionError):
        kind = ProviderFailureKind.NETWORK
    elif isinstance(error, RateLimitError):
        kind = ProviderFailureKind.RATE_LIMIT
    elif isinstance(error, AuthenticationError):
        kind = ProviderFailureKind.AUTHENTICATION
    elif isinstance(error, BadRequestError):
        kind = ProviderFailureKind.INVALID_REQUEST
    elif isinstance(error, APIStatusError) and error.status_code >= 500:
        kind = ProviderFailureKind.UNAVAILABLE
    else:
        kind = ProviderFailureKind.INTERNAL
    raise ProviderFailure(kind, "OpenAI API request failed") from error
