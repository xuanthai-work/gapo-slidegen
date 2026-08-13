import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import TypeVar

from app.ai.base import AIProvider, ProviderFailure, ProviderFailureKind

ResultT = TypeVar("ResultT")
logger = logging.getLogger(__name__)


class AIOrchestrator:
    def __init__(
        self,
        providers: Sequence[AIProvider],
        *,
        retries_per_provider: int,
        timeout_seconds: int,
    ) -> None:
        if not providers:
            raise ValueError("At least one AI provider is required")
        self.providers = providers
        self.retries_per_provider = retries_per_provider
        self.timeout_seconds = timeout_seconds

    async def run_with_failover(
        self,
        operation: Callable[[AIProvider], Awaitable[ResultT]],
        *,
        request_id: str,
        job_id: str,
    ) -> ResultT:
        last_error: ProviderFailure | None = None

        for provider in self.providers:
            for attempt in range(self.retries_per_provider + 1):
                try:
                    async with asyncio.timeout(self.timeout_seconds):
                        result = await operation(provider)
                    logger.info(
                        "ai_call_succeeded",
                        extra={
                            "request_id": request_id,
                            "job_id": job_id,
                            "provider": provider.name,
                            "model": provider.model,
                            "attempt": attempt + 1,
                        },
                    )
                    return result
                except TimeoutError as error:
                    last_error = ProviderFailure(ProviderFailureKind.TIMEOUT, str(error))
                except ProviderFailure as error:
                    last_error = error

                logger.warning(
                    "ai_call_failed",
                    extra={
                        "request_id": request_id,
                        "job_id": job_id,
                        "provider": provider.name,
                        "model": provider.model,
                        "attempt": attempt + 1,
                        "failure_kind": last_error.kind.value,
                    },
                )

                if not last_error.retryable:
                    raise last_error
                if attempt < self.retries_per_provider:
                    await asyncio.sleep(0.25 * (2**attempt))

        if last_error is None:
            raise RuntimeError("AI provider chain ended without a result")
        raise last_error
