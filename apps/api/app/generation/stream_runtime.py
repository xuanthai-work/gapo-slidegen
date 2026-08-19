from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field, replace
from time import monotonic as monotonic_time

from .checkpoints import GenerationCheckpointService
from .event_transport import GenerationEventPublisher, PublishResult
from .events import SLIDE_COMPLETED, SLOT_SNAPSHOT, GenerationEvent
from .layouts import ContentConstraints
from .models import DeckPlan, SlideContent
from .stages.models import StoryOutline

logger = logging.getLogger(__name__)

MAX_STREAM_REMAINDER_ATTEMPTS = 3


def log_generation_metric(name: str, **fields: object) -> None:
    details = " ".join(f"{key}={value}" for key, value in fields.items())
    logger.info("generation_metric name=%s %s", name, details)


def remaining_slide_ids(slide_ids: Iterable[str], completed_ids: Iterable[str]) -> list[str]:
    completed = set(completed_ids)
    return [slide_id for slide_id in slide_ids if slide_id not in completed]


def subset_story_outline(outline: StoryOutline, slide_ids: Iterable[str]) -> StoryOutline:
    wanted = set(slide_ids)
    return replace(outline, items=[item for item in outline.items if item.id in wanted])


def subset_deck_plan(deck_plan: DeckPlan, slide_ids: Iterable[str]) -> DeckPlan:
    wanted = set(slide_ids)
    return replace(
        deck_plan,
        slides=[slide for slide in deck_plan.slides if slide.id in wanted],
    )


def stream_slots_for_constraints(constraints: ContentConstraints) -> tuple[str, ...]:
    slots = ["title", "body"]
    for index in range(constraints.max_items):
        slots.extend((f"items.{index}.heading", f"items.{index}.body"))
    return tuple(slots)


class SlotSnapshotCoalescer:
    """Buffers cumulative snapshots so workers can emit fewer live events."""

    def __init__(
        self,
        *,
        delay_seconds: float,
        monotonic: Callable[[], float],
    ) -> None:
        self._delay_seconds = delay_seconds
        self._monotonic = monotonic
        self._pending: dict[tuple[str, int, str, str], GenerationEvent] = {}
        self._due_at: float | None = None
        self.coalesced = 0

    def ingest(self, event: GenerationEvent) -> list[GenerationEvent]:
        if event.type != SLOT_SNAPSHOT or event.slot is None:
            flushed = self.flush()
            flushed.append(event)
            return flushed

        identity = (event.job_id, event.attempt, event.slide_id, event.slot)
        if identity in self._pending:
            self.coalesced += 1
        self._pending[identity] = event
        now = self._monotonic()
        if self._due_at is None:
            self._due_at = now + self._delay_seconds
        if now >= self._due_at:
            return self.flush()
        return []

    def flush(self) -> list[GenerationEvent]:
        events = list(self._pending.values())
        self._pending.clear()
        self._due_at = None
        return events


@dataclass(slots=True)
class IncrementalSlideStreamer:
    publisher: GenerationEventPublisher
    checkpoints: GenerationCheckpointService
    compile_slide: Callable[[int, Mapping[str, SlideContent]], dict[str, object]]
    validate_slide: Callable[[dict[str, object]], dict[str, object]]
    delay_seconds: float = 0.1
    monotonic: Callable[[], float] = field(default=monotonic_time)
    compiled: list[dict[str, object]] = field(default_factory=list, init=False)
    _skip_ids: set[str] = field(default_factory=set, init=False)

    def consume(
        self,
        events: Iterable[GenerationEvent],
        *,
        slide_ids: list[str],
        skip_ids: Iterable[str] = (),
    ) -> list[dict[str, object]]:
        coalescer = SlotSnapshotCoalescer(
            delay_seconds=self.delay_seconds,
            monotonic=self.monotonic,
        )
        contents: dict[str, SlideContent] = {}
        self.compiled = []
        self._skip_ids = set(skip_ids)
        index_by_id = {slide_id: index for index, slide_id in enumerate(slide_ids)}
        started_at = self.monotonic()
        first_snapshot_logged = False
        first_slide_logged = False

        for event in events:
            if not first_snapshot_logged and event.type == SLOT_SNAPSHOT:
                log_generation_metric(
                    "time_to_first_slot_ms",
                    job_id=event.job_id,
                    slide_id=event.slide_id,
                    slot=event.slot,
                    elapsed_ms=int((self.monotonic() - started_at) * 1000),
                )
                first_snapshot_logged = True
            for outgoing in coalescer.ingest(event):
                completed = self._handle(outgoing, contents, index_by_id)
                if completed and not first_slide_logged:
                    log_generation_metric(
                        "time_to_first_slide_ms",
                        job_id=outgoing.job_id,
                        slide_id=outgoing.slide_id,
                        elapsed_ms=int((self.monotonic() - started_at) * 1000),
                    )
                    first_slide_logged = True
        for outgoing in coalescer.flush():
            self._handle(outgoing, contents, index_by_id)
        if coalescer.coalesced:
            log_generation_metric("coalesced_events", count=coalescer.coalesced)
        return self.compiled

    def _handle(
        self,
        event: GenerationEvent,
        contents: dict[str, SlideContent],
        index_by_id: dict[str, int],
    ) -> bool:
        if event.slide_id in self._skip_ids:
            return False
        result = self.publisher.publish(event)
        if isinstance(result, PublishResult) and not result.published and result.error:
            log_generation_metric(
                "redis_failures",
                job_id=event.job_id,
                error=result.error,
            )
        if event.type != SLIDE_COMPLETED:
            return False
        content = event.data.get("content")
        if not isinstance(content, SlideContent):
            raise ValueError("Completed stream events require SlideContent")
        if content.slide_id not in index_by_id:
            raise ValueError(f"Completed stream event for unknown slide {content.slide_id}")
        contents[content.slide_id] = content
        slide = dict(self.validate_slide(self.compile_slide(index_by_id[content.slide_id], contents)))
        slide["id"] = event.slide_id
        self.checkpoints.record_event(event, validated_canonical_slide=slide)
        self.compiled.append(slide)
        return True
