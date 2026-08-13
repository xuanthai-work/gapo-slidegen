from enum import StrEnum
from typing import Protocol

from app.schemas.presentation import Outline
from app.schemas.slide import SlideContent


class ProviderFailureKind(StrEnum):
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    UNAVAILABLE = "unavailable"
    NETWORK = "network"
    INVALID_RESPONSE = "invalid_response"
    INVALID_REQUEST = "invalid_request"
    POLICY_REFUSAL = "policy_refusal"
    AUTHENTICATION = "authentication"
    INTERNAL = "internal"


RETRYABLE_FAILURES = {
    ProviderFailureKind.TIMEOUT,
    ProviderFailureKind.RATE_LIMIT,
    ProviderFailureKind.UNAVAILABLE,
    ProviderFailureKind.NETWORK,
    ProviderFailureKind.INVALID_RESPONSE,
}


class ProviderFailure(Exception):
    def __init__(self, kind: ProviderFailureKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind

    @property
    def retryable(self) -> bool:
        return self.kind in RETRYABLE_FAILURES


class AIProvider(Protocol):
    name: str
    model: str

    async def generate_outline(
        self, *, prompt: str, language: str, slide_count: int
    ) -> Outline: ...

    async def generate_slide(
        self, *, outline: Outline, slide_index: int, theme_key: str
    ) -> SlideContent: ...
