from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass

from .events import (
    SLOT_SNAPSHOT,
    GenerationEvent,
    coalesce_slot_snapshots,
    serialize_generation_event,
)

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = {"succeeded", "failed", "canceled"}
MAX_SSE_STREAMS_PER_USER = 4
_active_streams_by_user: dict[str, int] = {}


def acquire_sse_slot(user_id: str, *, limit: int = MAX_SSE_STREAMS_PER_USER) -> bool:
    current = _active_streams_by_user.get(user_id, 0)
    if current >= limit:
        return False
    _active_streams_by_user[user_id] = current + 1
    return True


def release_sse_slot(user_id: str) -> None:
    current = _active_streams_by_user.get(user_id, 0)
    if current <= 1:
        _active_streams_by_user.pop(user_id, None)
        return
    _active_streams_by_user[user_id] = current - 1


def format_sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


def generation_event_sse(event: GenerationEvent) -> str:
    return format_sse("generation", serialize_generation_event(event))


def progress_sse(payload: str) -> str:
    return format_sse("progress", payload)


def checkpoint_slide_sse(slide: dict[str, object], *, index: int, total: int) -> str:
    return format_sse(
        "slide",
        json.dumps(
            {
                "stage": "rendering",
                "message": f"Building slide {index + 1}...",
                "slide_count": total,
                "latest_slide": slide,
                "slides": None,
            },
            ensure_ascii=False,
        ),
    )


@dataclass(slots=True)
class BoundedLiveBuffer:
    maxsize: int = 32
    _pending: list[GenerationEvent] | None = None

    def __post_init__(self) -> None:
        self._pending = []

    def push(self, event: GenerationEvent) -> None:
        assert self._pending is not None
        self._pending.append(event)
        self._pending = coalesce_slot_snapshots(self._pending)
        while len(self._pending) > self.maxsize:
            drop_at = next(
                (
                    index
                    for index, item in enumerate(self._pending)
                    if item.type == SLOT_SNAPSHOT
                ),
                0,
            )
            self._pending.pop(drop_at)

    def drain(self) -> list[GenerationEvent]:
        assert self._pending is not None
        drained = self._pending
        self._pending = []
        return drained


async def iterate_generation_sse(
    *,
    initial_progress: str,
    checkpoint_slides: list[dict[str, object]],
    live_events: AsyncIterator[GenerationEvent] | None,
    poll_terminal: Callable[[], Awaitable[tuple[str | None, bool]]],
    heartbeat_seconds: float = 25,
    queue_size: int = 32,
) -> AsyncIterator[str]:
    yield progress_sse(initial_progress)
    total = len(checkpoint_slides)
    for index, slide in enumerate(checkpoint_slides):
        yield checkpoint_slide_sse(slide, index=index, total=total)

    if live_events is None:
        while True:
            payload, done = await poll_terminal()
            if payload is not None:
                yield progress_sse(payload)
            if done:
                return
            yield ":heartbeat\n\n"
            await asyncio.sleep(heartbeat_seconds)
        return

    buffer = BoundedLiveBuffer(maxsize=queue_size)
    queue: asyncio.Queue[GenerationEvent | None] = asyncio.Queue(maxsize=queue_size)

    async def pump() -> None:
        try:
            async for event in live_events:
                buffer.push(event)
                for outgoing in buffer.drain():
                    try:
                        queue.put_nowait(outgoing)
                    except asyncio.QueueFull:
                        dropped = True
                        while dropped:
                            try:
                                queue.get_nowait()
                            except asyncio.QueueEmpty:
                                dropped = False
                                break
                            try:
                                queue.put_nowait(outgoing)
                                dropped = False
                            except asyncio.QueueFull:
                                continue
        except Exception as error:
            logger.warning("generation live events ended: %s", error)
        finally:
            aclose = getattr(live_events, "aclose", None)
            if aclose is not None:
                try:
                    await aclose()
                except Exception:
                    pass
            await queue.put(None)

    async def poll_until_done(*, emit_heartbeat: bool) -> AsyncIterator[str]:
        while True:
            payload, done = await poll_terminal()
            if payload is not None:
                yield progress_sse(payload)
            if done:
                return
            if emit_heartbeat:
                yield ":heartbeat\n\n"
            await asyncio.sleep(heartbeat_seconds)

    pump_task = asyncio.create_task(pump())
    try:
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=heartbeat_seconds)
            except TimeoutError:
                payload, done = await poll_terminal()
                if payload is not None:
                    yield progress_sse(payload)
                yield ":heartbeat\n\n"
                if done:
                    return
                continue
            if item is None:
                async for chunk in poll_until_done(emit_heartbeat=True):
                    yield chunk
                return
            yield generation_event_sse(item)
    finally:
        pump_task.cancel()
        try:
            await pump_task
        except asyncio.CancelledError:
            pass
