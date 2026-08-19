from pydantic import SecretStr

from app.config import Settings
from app.generation.event_factory import (
    build_generation_event_publisher,
    build_generation_event_subscriber,
)
from app.generation.event_transport import (
    RedisGenerationEventPublisher,
    RedisGenerationEventSubscriber,
)


def test_streaming_settings_are_disabled_with_empty_secret_redis_default() -> None:
    settings = Settings(_env_file=None)

    assert settings.generation_streaming_enabled is False
    assert isinstance(settings.redis_url, SecretStr)
    assert settings.redis_url.get_secret_value() == ""
    assert settings.generation_event_channel_prefix == "slidegen:generation"


def test_disabled_streaming_does_not_construct_redis_clients() -> None:
    calls: list[str] = []

    def factory(url: str) -> object:
        calls.append(url)
        return object()

    settings = Settings(_env_file=None, generation_streaming_enabled=False)

    assert build_generation_event_publisher(settings, client_factory=factory) is None
    assert build_generation_event_subscriber(settings, client_factory=factory) is None
    assert calls == []


def test_enabled_factories_inject_sync_and_async_clients_lazily() -> None:
    sync_client = object()
    async_client = object()
    urls: list[str] = []
    settings = Settings(
        _env_file=None,
        generation_streaming_enabled=True,
        redis_url="redis://redis:6379/2",
    )

    def sync_factory(url: str) -> object:
        urls.append(url)
        return sync_client

    def async_factory(url: str) -> object:
        urls.append(url)
        return async_client

    publisher = build_generation_event_publisher(
        settings,
        client_factory=sync_factory,
    )
    subscriber = build_generation_event_subscriber(
        settings,
        client_factory=async_factory,
    )

    assert isinstance(publisher, RedisGenerationEventPublisher)
    assert isinstance(subscriber, RedisGenerationEventSubscriber)
    assert urls == ["redis://redis:6379/2", "redis://redis:6379/2"]
