import asyncio
import json
from dataclasses import dataclass

import pytest

from app.generation.event_transport import (
    InMemoryGenerationEventBus,
    RedisGenerationEventPublisher,
    RedisGenerationEventSubscriber,
)
from app.generation.events import (
    GenerationEvent,
    GenerationEventValidationError,
    deserialize_generation_event,
    serialize_generation_event,
)
from app.generation.models import SlideContent


def _event(**changes: object) -> GenerationEvent:
    values: dict[str, object] = {
        "version": 1,
        "type": "slide.completed",
        "job_id": "job-1",
        "attempt": 1,
        "sequence": 4,
        "slide_id": "slide-1",
        "slot": None,
        "data": {
            "content": SlideContent(
                slide_id="slide-1",
                title="Title",
                layout_id="title-body",
                slots={"body": "Body", "items": [{"heading": "One"}]},
            )
        },
    }
    values.update(changes)
    return GenerationEvent(**values)  # type: ignore[arg-type]


def test_generation_event_round_trip_is_versioned_json_without_dataclasses() -> None:
    event = _event()

    encoded = serialize_generation_event(event)
    wire_payload = json.loads(encoded)

    assert wire_payload["version"] == 1
    assert wire_payload["data"]["content"] == {
        "slide_id": "slide-1",
        "title": "Title",
        "layout_id": "title-body",
        "slots": {"body": "Body", "items": [{"heading": "One"}]},
    }
    assert deserialize_generation_event(encoded) == event


@pytest.mark.parametrize(
    "payload",
    [
        "{}",
        '{"version":2,"type":"slide.completed","job_id":"job-1","attempt":1,'
        '"sequence":1,"slide_id":"slide-1","slot":null,"data":{}}',
        '{"version":1,"type":"","job_id":"job-1","attempt":1,'
        '"sequence":1,"slide_id":"slide-1","slot":null,"data":{}}',
    ],
)
def test_generation_event_deserialization_rejects_invalid_envelopes(payload: str) -> None:
    with pytest.raises(GenerationEventValidationError):
        deserialize_generation_event(payload)


def test_generation_event_validation_enforces_known_event_payloads() -> None:
    with pytest.raises(GenerationEventValidationError, match="content"):
        deserialize_generation_event(
            '{"version":1,"type":"slide.completed","job_id":"job-1","attempt":1,'
            '"sequence":1,"slide_id":"slide-1","slot":null,"data":{}}'
        )
    with pytest.raises(GenerationEventValidationError, match="slot"):
        serialize_generation_event(
            _event(type="slot.snapshot", slot=None, data={"value": "Body"})
        )


def test_completed_title_validation_is_symmetric() -> None:
    invalid_event = _event(
        data={
            "content": SlideContent(
                slide_id="slide-1",
                title="",
                layout_id="title-body",
                slots={"body": "Body"},
            )
        }
    )
    invalid_wire_payload = (
        '{"version":1,"type":"slide.completed","job_id":"job-1","attempt":1,'
        '"sequence":1,"slide_id":"slide-1","slot":null,"data":{"content":'
        '{"slide_id":"slide-1","title":"","layout_id":"title-body","slots":{}}}}'
    )

    with pytest.raises(GenerationEventValidationError, match="title"):
        serialize_generation_event(invalid_event)
    with pytest.raises(GenerationEventValidationError, match="title"):
        deserialize_generation_event(invalid_wire_payload)


@pytest.mark.parametrize("field", ["version", "attempt", "sequence"])
def test_event_integer_fields_reject_bool_in_both_directions(field: str) -> None:
    with pytest.raises(GenerationEventValidationError, match=field):
        serialize_generation_event(_event(**{field: True}))

    payload = json.loads(serialize_generation_event(_event()))
    payload[field] = True
    with pytest.raises(GenerationEventValidationError, match=field):
        deserialize_generation_event(json.dumps(payload))


def test_generation_event_serialization_rejects_provider_raw_frames() -> None:
    @dataclass
    class ProviderFrame:
        token: str

    with pytest.raises(GenerationEventValidationError, match="JSON-safe"):
        serialize_generation_event(
            _event(type="slot.snapshot", slot="body", data={"raw_frame": ProviderFrame("secret")})
        )


def test_redis_publisher_uses_sync_client_and_represents_failures() -> None:
    class FakeRedis:
        def __init__(self, error: Exception | None = None) -> None:
            self.error = error
            self.calls: list[tuple[str, str]] = []

        def publish(self, channel: str, payload: str) -> int:
            self.calls.append((channel, payload))
            if self.error:
                raise self.error
            return 2

    client = FakeRedis()
    success = RedisGenerationEventPublisher(client, channel_prefix="generation").publish(_event())
    assert success.published is True
    assert success.subscriber_count == 2
    assert client.calls[0][0] == "generation:job-1"

    failure = RedisGenerationEventPublisher(
        FakeRedis(ConnectionError("redis unavailable")),
        channel_prefix="generation",
    ).publish(_event())
    assert failure.published is False
    assert failure.error == "redis unavailable"


def test_in_memory_bus_is_transient_and_supports_async_subscribers() -> None:
    async def exercise() -> None:
        bus = InMemoryGenerationEventBus()
        stream = bus.subscribe("job-1")
        pending = asyncio.create_task(anext(stream))
        await asyncio.sleep(0)

        result = bus.publish(_event())

        assert result.published is True
        assert result.subscriber_count == 1
        assert await pending == _event()
        await stream.aclose()

        assert bus.publish(_event()).subscriber_count == 0

    asyncio.run(exercise())


def test_async_redis_subscriber_decodes_messages_and_closes_pubsub() -> None:
    class FakePubSub:
        def __init__(self, payload: str) -> None:
            self.payload = payload
            self.subscribed: list[str] = []
            self.unsubscribed: list[str] = []
            self.closed = False

        async def subscribe(self, channel: str) -> None:
            self.subscribed.append(channel)

        async def unsubscribe(self, channel: str) -> None:
            self.unsubscribed.append(channel)

        async def aclose(self) -> None:
            self.closed = True

        async def listen(self):
            yield {"type": "subscribe", "data": 1}
            yield {"type": "message", "data": self.payload.encode()}

    class FakeAsyncRedis:
        def __init__(self, pubsub: FakePubSub) -> None:
            self._pubsub = pubsub

        def pubsub(self) -> FakePubSub:
            return self._pubsub

    async def exercise() -> None:
        pubsub = FakePubSub(serialize_generation_event(_event()))
        subscriber = RedisGenerationEventSubscriber(
            FakeAsyncRedis(pubsub),
            channel_prefix="generation",
        )
        stream = subscriber.subscribe("job-1")

        assert await anext(stream) == _event()
        await stream.aclose()
        assert pubsub.subscribed == ["generation:job-1"]
        assert pubsub.unsubscribed == ["generation:job-1"]
        assert pubsub.closed is True

    asyncio.run(exercise())


def test_async_redis_cleanup_closes_after_unsubscribe_failure() -> None:
    class FailingUnsubscribePubSub:
        def __init__(self) -> None:
            self.closed = False

        async def subscribe(self, channel: str) -> None:
            return None

        async def unsubscribe(self, channel: str) -> None:
            raise RuntimeError("unsubscribe failed")

        async def aclose(self) -> None:
            self.closed = True

        async def listen(self):
            yield {
                "type": "message",
                "data": serialize_generation_event(_event()),
            }

    class FakeAsyncRedis:
        def __init__(self, pubsub: FailingUnsubscribePubSub) -> None:
            self._pubsub = pubsub

        def pubsub(self) -> FailingUnsubscribePubSub:
            return self._pubsub

    async def exercise() -> None:
        pubsub = FailingUnsubscribePubSub()
        stream = RedisGenerationEventSubscriber(
            FakeAsyncRedis(pubsub),
            channel_prefix="generation",
        ).subscribe("job-1")

        assert await anext(stream) == _event()
        await stream.aclose()
        assert pubsub.closed is True

    asyncio.run(exercise())


def test_async_redis_cleanup_does_not_mask_stream_error() -> None:
    class FailingPubSub:
        def __init__(self) -> None:
            self.close_attempted = False

        async def subscribe(self, channel: str) -> None:
            return None

        async def unsubscribe(self, channel: str) -> None:
            raise RuntimeError("unsubscribe failed")

        async def aclose(self) -> None:
            self.close_attempted = True
            raise RuntimeError("close failed")

        async def listen(self):
            raise ValueError("stream failed")
            yield

    class FakeAsyncRedis:
        def __init__(self, pubsub: FailingPubSub) -> None:
            self._pubsub = pubsub

        def pubsub(self) -> FailingPubSub:
            return self._pubsub

    async def exercise() -> None:
        pubsub = FailingPubSub()
        stream = RedisGenerationEventSubscriber(
            FakeAsyncRedis(pubsub),
            channel_prefix="generation",
        ).subscribe("job-1")

        with pytest.raises(ValueError, match="stream failed"):
            await anext(stream)
        assert pubsub.close_attempted is True

    asyncio.run(exercise())


def test_redis_subscriber_aclose_closes_the_client() -> None:
    class FakeAsyncRedis:
        def __init__(self) -> None:
            self.closed = False

        async def aclose(self) -> None:
            self.closed = True

    async def exercise() -> None:
        client = FakeAsyncRedis()
        subscriber = RedisGenerationEventSubscriber(client, channel_prefix="generation")
        await subscriber.aclose()
        assert client.closed is True

    asyncio.run(exercise())
