from functools import lru_cache

from app.ai.base import AIProvider
from app.ai.orchestrator import AIOrchestrator
from app.ai.providers import GoogleAIProvider, OpenAIProvider
from app.core.config import get_settings


@lru_cache
def get_ai_orchestrator() -> AIOrchestrator:
    settings = get_settings()
    providers: list[AIProvider] = []

    if settings.GOOGLE_API_KEY is not None:
        providers.append(
            GoogleAIProvider(
                api_key=settings.GOOGLE_API_KEY.get_secret_value(),
                model=settings.GOOGLE_MODEL,
            )
        )
    if settings.OPENAI_API_KEY is not None:
        api_key = settings.OPENAI_API_KEY.get_secret_value()
        providers.extend(
            [
                OpenAIProvider(api_key=api_key, model=settings.OPENAI_FALLBACK_MODEL),
                OpenAIProvider(api_key=api_key, model=settings.OPENAI_FALLBACK_2_MODEL),
            ]
        )

    return AIOrchestrator(
        providers,
        retries_per_provider=settings.AI_MAX_RETRIES_PER_PROVIDER,
        timeout_seconds=settings.AI_REQUEST_TIMEOUT_SECONDS,
    )
