from typing import cast

import pytest

from app.ai.base import AIProvider, ProviderFailure, ProviderFailureKind
from app.ai.orchestrator import AIOrchestrator


class FakeProvider:
    def __init__(self, name: str, result: str | Exception) -> None:
        self.name = name
        self.model = f"{name}-model"
        self.result = result


@pytest.mark.asyncio
async def test_retryable_failure_uses_next_provider() -> None:
    primary = FakeProvider(
        "primary", ProviderFailure(ProviderFailureKind.RATE_LIMIT, "limited")
    )
    fallback = FakeProvider("fallback", "ok")
    orchestrator = AIOrchestrator(
        [cast(AIProvider, primary), cast(AIProvider, fallback)],
        retries_per_provider=0,
        timeout_seconds=1,
    )

    async def operation(provider: AIProvider) -> str:
        fake = cast(FakeProvider, provider)
        if isinstance(fake.result, Exception):
            raise fake.result
        return fake.result

    result = await orchestrator.run_with_failover(
        operation, request_id="request-test", job_id="job-test"
    )

    assert result == "ok"


@pytest.mark.asyncio
async def test_non_retryable_failure_stops_chain() -> None:
    primary = FakeProvider(
        "primary", ProviderFailure(ProviderFailureKind.AUTHENTICATION, "bad key")
    )
    fallback = FakeProvider("fallback", "must-not-run")
    orchestrator = AIOrchestrator(
        [cast(AIProvider, primary), cast(AIProvider, fallback)],
        retries_per_provider=0,
        timeout_seconds=1,
    )

    async def operation(provider: AIProvider) -> str:
        fake = cast(FakeProvider, provider)
        if isinstance(fake.result, Exception):
            raise fake.result
        return fake.result

    with pytest.raises(ProviderFailure) as error:
        await orchestrator.run_with_failover(
            operation, request_id="request-test", job_id="job-test"
        )

    assert error.value.kind is ProviderFailureKind.AUTHENTICATION
