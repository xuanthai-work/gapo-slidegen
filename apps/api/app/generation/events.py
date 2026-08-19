from __future__ import annotations

import json
import math
from collections.abc import Iterable
from dataclasses import dataclass, is_dataclass
from typing import Any

from .models import SlideContent

SLOT_SNAPSHOT = "slot.snapshot"
SLIDE_COMPLETED = "slide.completed"
EVENT_VERSION = 1


class GenerationEventValidationError(ValueError):
    """A generation event cannot safely cross the transport boundary."""


@dataclass(frozen=True, slots=True)
class GenerationEvent:
    """Versioned domain event emitted while generating one deck attempt."""

    version: int
    type: str
    job_id: str
    attempt: int
    sequence: int
    slide_id: str
    slot: str | None
    data: dict[str, object]


def _json_safe(value: object, *, path: str) -> object:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        raise GenerationEventValidationError(f"{path} must contain finite JSON numbers")
    if isinstance(value, SlideContent):
        return {
            "slide_id": value.slide_id,
            "title": value.title,
            "layout_id": value.layout_id,
            "slots": _json_safe(value.slots, path=f"{path}.slots"),
        }
    if isinstance(value, dict):
        converted: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise GenerationEventValidationError(f"{path} must use string JSON keys")
            if key in {"raw_frame", "provider_frame", "provider_raw_frame"}:
                raise GenerationEventValidationError(
                    f"{path}.{key} is provider-private and is not JSON-safe event data"
                )
            converted[key] = _json_safe(item, path=f"{path}.{key}")
        return converted
    if isinstance(value, (list, tuple)):
        return [_json_safe(item, path=f"{path}[{index}]") for index, item in enumerate(value)]
    kind = "dataclass" if is_dataclass(value) else type(value).__name__
    raise GenerationEventValidationError(f"{path} contains non-JSON-safe {kind} data")


def _required_text(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise GenerationEventValidationError(f"{field} must be a non-empty string")
    return value


def _required_positive_int(payload: dict[str, Any], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise GenerationEventValidationError(f"{field} must be a positive integer")
    return value


def _validate_envelope(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise GenerationEventValidationError("Generation event payload must be a JSON object")
    required = {
        "version",
        "type",
        "job_id",
        "attempt",
        "sequence",
        "slide_id",
        "slot",
        "data",
    }
    if set(payload) != required:
        raise GenerationEventValidationError("Generation event fields are missing or unsupported")
    version = payload.get("version")
    if isinstance(version, bool) or not isinstance(version, int):
        raise GenerationEventValidationError("version must be an integer")
    if version != EVENT_VERSION:
        raise GenerationEventValidationError(
            f"Unsupported generation event version {version!r}"
        )
    _required_text(payload, "type")
    _required_text(payload, "job_id")
    _required_positive_int(payload, "attempt")
    _required_positive_int(payload, "sequence")
    _required_text(payload, "slide_id")
    if payload["slot"] is not None and (
        not isinstance(payload["slot"], str) or not payload["slot"]
    ):
        raise GenerationEventValidationError("slot must be null or a non-empty string")
    if not isinstance(payload["data"], dict):
        raise GenerationEventValidationError("data must be a JSON object")
    return payload


def _validate_known_event(payload: dict[str, Any]) -> None:
    if payload["type"] == SLOT_SNAPSHOT:
        if payload["slot"] is None:
            raise GenerationEventValidationError("slot.snapshot requires a slot")
        if not isinstance(payload["data"].get("value"), str):
            raise GenerationEventValidationError("slot.snapshot requires a string value")
    if payload["type"] == SLIDE_COMPLETED:
        if payload["slot"] is not None:
            raise GenerationEventValidationError("slide.completed cannot identify one slot")
        content = payload["data"].get("content")
        if not isinstance(content, dict):
            raise GenerationEventValidationError(
                "slide.completed requires canonical content"
            )
        if content.get("slide_id") != payload["slide_id"]:
            raise GenerationEventValidationError(
                "Completed content slide_id must match the event"
            )
        _required_text(content, "title")
        if not isinstance(content.get("layout_id"), str) or not isinstance(
            content.get("slots"), dict
        ):
            raise GenerationEventValidationError(
                "Completed content requires layout_id and slots"
            )


def serialize_generation_event(event: GenerationEvent) -> str:
    """Serialize a domain event to the stable, versioned JSON wire contract."""

    payload = _validate_envelope(
        {
            "version": event.version,
            "type": event.type,
            "job_id": event.job_id,
            "attempt": event.attempt,
            "sequence": event.sequence,
            "slide_id": event.slide_id,
            "slot": event.slot,
            "data": _json_safe(event.data, path="data"),
        }
    )
    _validate_known_event(payload)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def deserialize_generation_event(payload: str | bytes) -> GenerationEvent:
    """Validate and deserialize one generation event from the wire."""

    try:
        decoded = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as error:
        raise GenerationEventValidationError("Generation event is not valid JSON") from error
    values = _validate_envelope(decoded)
    data = _json_safe(values["data"], path="data")
    values = {**values, "data": data}
    _validate_known_event(values)
    if values["type"] == SLIDE_COMPLETED and isinstance(data, dict):
        content = data.get("content")
        if isinstance(content, dict):
            try:
                slide_id = _required_text(content, "slide_id")
                title = _required_text(content, "title")
                layout_id = content.get("layout_id", "")
                slots = content.get("slots")
                if not isinstance(layout_id, str) or not isinstance(slots, dict):
                    raise GenerationEventValidationError(
                        "Completed slide content has invalid layout_id or slots"
                    )
                data = dict(data)
                data["content"] = SlideContent(
                    slide_id=slide_id,
                    title=title,
                    layout_id=layout_id,
                    slots=slots,
                )
            except GenerationEventValidationError:
                raise
            except (KeyError, TypeError) as error:
                raise GenerationEventValidationError(
                    "Completed slide content is invalid"
                ) from error
    return GenerationEvent(
        version=values["version"],
        type=values["type"],
        job_id=values["job_id"],
        attempt=values["attempt"],
        sequence=values["sequence"],
        slide_id=values["slide_id"],
        slot=values["slot"],
        data=data,
    )


def coalesce_slot_snapshots(
    events: Iterable[GenerationEvent],
) -> list[GenerationEvent]:
    """Drop superseded cumulative snapshots without disturbing retained events."""

    materialized = list(events)
    latest_snapshot_index: dict[tuple[str, int, str, str], int] = {}
    for index, event in enumerate(materialized):
        if event.type == SLOT_SNAPSHOT and event.slot is not None:
            identity = (
                event.job_id,
                event.attempt,
                event.slide_id,
                event.slot,
            )
            current_index = latest_snapshot_index.get(identity)
            if (
                current_index is None
                or event.sequence > materialized[current_index].sequence
            ):
                latest_snapshot_index[identity] = index

    return [
        event
        for index, event in enumerate(materialized)
        if event.type != SLOT_SNAPSHOT
        or event.slot is None
        or latest_snapshot_index[
            (event.job_id, event.attempt, event.slide_id, event.slot)
        ]
        == index
    ]
