from __future__ import annotations

from uuid import UUID

from ..models import GenerationCheckpoint, GenerationCheckpointStatus
from .checkpoint_repository import CheckpointUpsert, GenerationCheckpointRepository
from .events import SLIDE_COMPLETED, GenerationEvent
from .models import SlideContent


class InvalidGenerationCheckpoint(ValueError):
    pass


def _validate_canonical_slide(
    slide: dict[str, object] | None,
    *,
    slide_id: str,
) -> None:
    if slide is None:
        return
    if slide.get("id") != slide_id or not isinstance(slide.get("elements"), list):
        raise InvalidGenerationCheckpoint(
            "Validated canonical slide must match the event slide and contain elements"
        )


class GenerationCheckpointService:
    """Translate durable semantic completion events into reconnect checkpoints."""

    def __init__(self, repository: GenerationCheckpointRepository) -> None:
        self.repository = repository

    def list_for_job(self, job_id: UUID) -> list[GenerationCheckpoint]:
        return self.repository.list_for_job(job_id)

    def record_event(
        self,
        event: GenerationEvent,
        *,
        validated_canonical_slide: dict[str, object] | None = None,
    ) -> GenerationCheckpoint | None:
        if event.type != SLIDE_COMPLETED:
            return None

        content = event.data.get("content")
        if not isinstance(content, SlideContent) or content.slide_id != event.slide_id:
            raise InvalidGenerationCheckpoint(
                "Completed events require matching SlideContent"
            )
        _validate_canonical_slide(
            validated_canonical_slide,
            slide_id=event.slide_id,
        )
        try:
            job_id = UUID(event.job_id)
        except ValueError as error:
            raise InvalidGenerationCheckpoint(
                "Checkpoint events require a UUID job id"
            ) from error

        completed_slots = [{"slot": "title", "value": content.title}]
        completed_slots.extend(
            {"slot": slot, "value": value}
            for slot, value in content.slots.items()
        )
        return self.repository.upsert(
            CheckpointUpsert(
                job_id=job_id,
                slide_id=event.slide_id,
                attempt=event.attempt,
                sequence=event.sequence,
                completed_slots=completed_slots,
                canonical_slide=validated_canonical_slide,
                status=GenerationCheckpointStatus.COMPLETED,
            )
        )
