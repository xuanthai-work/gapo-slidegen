from __future__ import annotations

import asyncio
import inspect
from collections.abc import AsyncIterator
from dataclasses import dataclass
from threading import Lock
from typing import Protocol

from .events import (
    GenerationEvent,
    deserialize_generation_event,
    serialize_generation_event,
)


@dataclass(frozen=True, slots=True)
class PublishResult:
    """Non-throwing result used by workers to degrade gracefully."""

    published: bool
    subscriber_count: int = 0
    error: str | None = None


class GenerationEventPublisher(Protocol):
    def publish(self, event: GenerationEvent) -> PublishResult: ...


class GenerationEventSubscriber(Protocol):
    def subscribe(self, job_id: str) -> AsyncIterator[GenerationEvent]: ...


def event_channel(job_id: str, *, prefix: str) -> str:
    if not job_id:
        raise ValueError("Job ID must not be empty")
    normalized = prefix.strip().strip(":")
    if not normalized:
        raise ValueError("Channel prefix must not be empty")
    return f"{normalized}:{job_id}"


class RedisGenerationEventPublisher:
    """Synchronous Redis publisher for the generation worker."""

    def __init__(self, client: object, *, channel_prefix: str) -> None:
        self._client = client
        self._channel_prefix = channel_prefix

    def publish(self, event: GenerationEvent) -> PublishResult:
        try:
            count = self._client.publish(  # type: ignore[attr-defined]
                event_channel(event.job_id, prefix=self._channel_prefix),
                serialize_generation_event(event),
            )
        except Exception as error:
            return PublishResult(published=False, error=str(error) or type(error).__name__)
        return PublishResult(published=True, subscriber_count=int(count))


class RedisGenerationEventSubscriber:
    """Async Redis Pub/Sub subscriber for FastAPI streaming responses."""

    def __init__(self, client: object, *, channel_prefix: str) -> None:
        self._client = client
        self._channel_prefix = channel_prefix

    async def subscribe(self, job_id: str) -> AsyncIterator[GenerationEvent]:
        channel = event_channel(job_id, prefix=self._channel_prefix)
        pubsub = self._client.pubsub()  # type: ignore[attr-defined]
        subscribed = False
        try:
            await pubsub.subscribe(channel)
            subscribed = True
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                yield deserialize_generation_event(message["data"])
        finally:
            try:
                if subscribed:
                    await pubsub.unsubscribe(channel)
            except Exception:
                pass
            try:
                await pubsub.aclose()
            except Exception:
                pass

    async def aclose(self) -> None:
        closer = getattr(self._client, "aclose", None)
        if closer is None:
            closer = getattr(self._client, "close", None)
        if closer is None:
            return
        result = closer()
        if inspect.isawaitable(result):
            await result


@dataclass(frozen=True, slots=True)
class _MemorySubscription:
    queue: asyncio.Queue[GenerationEvent]
    loop: asyncio.AbstractEventLoop


class InMemoryGenerationEventBus:
    """Transient, thread-aware test implementation of both boundaries."""

    def __init__(self) -> None:
        self._subscriptions: dict[str, list[_MemorySubscription]] = {}
        self._lock = Lock()

    def publish(self, event: GenerationEvent) -> PublishResult:
        with self._lock:
            subscriptions = tuple(self._subscriptions.get(event.job_id, ()))
        for subscription in subscriptions:
            subscription.loop.call_soon_threadsafe(subscription.queue.put_nowait, event)
        return PublishResult(published=True, subscriber_count=len(subscriptions))

    async def subscribe(self, job_id: str) -> AsyncIterator[GenerationEvent]:
        if not job_id:
            raise ValueError("Job ID must not be empty")
        subscription = _MemorySubscription(
            queue=asyncio.Queue(),
            loop=asyncio.get_running_loop(),
        )
        with self._lock:
            self._subscriptions.setdefault(job_id, []).append(subscription)
        try:
            while True:
                yield await subscription.queue.get()
        finally:
            with self._lock:
                subscriptions = self._subscriptions.get(job_id, [])
                if subscription in subscriptions:
                    subscriptions.remove(subscription)
                if not subscriptions:
                    self._subscriptions.pop(job_id, None)
