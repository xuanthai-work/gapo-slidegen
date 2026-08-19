import asyncio
import json

from app.generation.event_sse import (
    BoundedLiveBuffer,
    generation_event_sse,
    iterate_generation_sse,
)
from app.generation.events import SLOT_SNAPSHOT, GenerationEvent


def _snapshot(sequence: int, text: str) -> GenerationEvent:
    return GenerationEvent(
        version=1,
        type=SLOT_SNAPSHOT,
        job_id="job-1",
        attempt=1,
        sequence=sequence,
        slide_id="slide-1",
        slot="title",
        data={"value": text},
    )


def test_generation_sse_uses_versioned_domain_payload() -> None:
    event = _snapshot(3, "Hello")
    encoded = generation_event_sse(event)
    assert encoded.startswith("event: generation\n")
    payload = json.loads(encoded.split("data: ", 1)[1].strip())
    assert payload["type"] == SLOT_SNAPSHOT
    assert payload["data"]["value"] == "Hello"
    assert "choices" not in payload


def test_bounded_buffer_keeps_latest_snapshot_and_drops_oldest() -> None:
    buffer = BoundedLiveBuffer(maxsize=2)
    buffer.push(_snapshot(1, "A"))
    buffer.push(_snapshot(2, "AB"))
    completed = GenerationEvent(
        version=1,
        type="slide.completed",
        job_id="job-1",
        attempt=1,
        sequence=3,
        slide_id="slide-1",
        slot=None,
        data={"content": {"slide_id": "slide-1", "title": "AB", "layout_id": "x", "slots": {}}},
    )
    buffer.push(_snapshot(4, "other"))
    buffer.push(completed)
    drained = buffer.drain()
    assert [event.type for event in drained][-1] == "slide.completed"
    assert any(event.type == SLOT_SNAPSHOT and event.data["value"] == "other" for event in drained)
    assert not any(event.data.get("value") == "A" for event in drained)


def test_iterate_generation_sse_emits_checkpoints_then_live_events() -> None:
    async def live():
        yield _snapshot(1, "Hi")

    async def poll():
        return ('{"id":"job","status":"succeeded"}', True)

    async def collect() -> list[str]:
        chunks = [
            chunk
            async for chunk in iterate_generation_sse(
                initial_progress='{"id":"job","status":"running"}',
                checkpoint_slides=[{"id": "cover", "elements": []}],
                live_events=live(),
                poll_terminal=poll,
                heartbeat_seconds=10,
            )
        ]
        return chunks

    chunks = asyncio.run(collect())
    assert chunks[0].startswith("event: progress\n")
    assert chunks[1].startswith("event: slide\n")
    assert '"slides": null' in chunks[1]
    assert any(chunk.startswith("event: generation\n") for chunk in chunks)
    assert chunks[-1].startswith("event: progress\n")
    assert "succeeded" in chunks[-1]


def test_iterate_generation_sse_polls_until_terminal_after_live_disconnect() -> None:
    polls = {"n": 0}

    async def live():
        yield _snapshot(1, "Hi")

    async def poll():
        polls["n"] += 1
        if polls["n"] < 2:
            return '{"id":"job","status":"running"}', False
        return '{"id":"job","status":"succeeded"}', True

    async def collect() -> list[str]:
        return [
            chunk
            async for chunk in iterate_generation_sse(
                initial_progress='{"id":"job","status":"running"}',
                checkpoint_slides=[],
                live_events=live(),
                poll_terminal=poll,
                heartbeat_seconds=0.01,
            )
        ]

    chunks = asyncio.run(collect())
    assert any("running" in chunk for chunk in chunks)
    assert chunks[-1].startswith("event: progress\n")
    assert "succeeded" in chunks[-1]
    assert polls["n"] >= 2


def test_sse_connection_limit_is_per_user() -> None:
    from app.generation.event_sse import acquire_sse_slot, release_sse_slot

    assert acquire_sse_slot("user-a", limit=1) is True
    assert acquire_sse_slot("user-a", limit=1) is False
    assert acquire_sse_slot("user-b", limit=1) is True
    release_sse_slot("user-a")
    assert acquire_sse_slot("user-a", limit=1) is True
    release_sse_slot("user-a")
    release_sse_slot("user-b")
