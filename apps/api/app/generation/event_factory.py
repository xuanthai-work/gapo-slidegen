from __future__ import annotations

from collections.abc import Callable

from ..config import Settings
from .event_transport import (
    GenerationEventPublisher,
    GenerationEventSubscriber,
    RedisGenerationEventPublisher,
    RedisGenerationEventSubscriber,
)

ClientFactory = Callable[[str], object]


def build_generation_event_publisher(
    settings: Settings,
    *,
    client_factory: ClientFactory | None = None,
) -> GenerationEventPublisher | None:
    """Build the sync worker boundary only when streaming is enabled."""

    if not settings.generation_streaming_enabled:
        return None
    if client_factory is None:
        from redis import Redis

        client_factory = Redis.from_url
    client = client_factory(settings.redis_url.get_secret_value())
    return RedisGenerationEventPublisher(
        client,
        channel_prefix=settings.generation_event_channel_prefix,
    )


def build_generation_event_subscriber(
    settings: Settings,
    *,
    client_factory: ClientFactory | None = None,
) -> GenerationEventSubscriber | None:
    """Build the async API boundary only when streaming is enabled."""

    if not settings.generation_streaming_enabled:
        return None
    if client_factory is None:
        from redis.asyncio import Redis

        client_factory = Redis.from_url
    client = client_factory(settings.redis_url.get_secret_value())
    return RedisGenerationEventSubscriber(
        client,
        channel_prefix=settings.generation_event_channel_prefix,
    )
