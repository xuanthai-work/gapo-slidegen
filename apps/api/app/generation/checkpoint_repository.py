from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ..models import GenerationCheckpoint, GenerationCheckpointStatus


@dataclass(frozen=True, slots=True)
class CheckpointUpsert:
    job_id: UUID
    slide_id: str
    attempt: int
    sequence: int
    completed_slots: list[dict[str, object]]
    canonical_slide: dict[str, object] | None
    status: GenerationCheckpointStatus


def build_checkpoint_upsert_statement(checkpoint: CheckpointUpsert):
    """Build an atomic upsert where stale attempts cannot replace newer data."""

    statement = insert(GenerationCheckpoint).values(
        id=uuid4(),
        job_id=checkpoint.job_id,
        slide_id=checkpoint.slide_id,
        attempt=checkpoint.attempt,
        sequence=checkpoint.sequence,
        completed_slots=checkpoint.completed_slots,
        canonical_slide=checkpoint.canonical_slide,
        status=checkpoint.status,
    )
    excluded = statement.excluded
    return (
        statement.on_conflict_do_update(
            index_elements=[
                GenerationCheckpoint.job_id,
                GenerationCheckpoint.slide_id,
            ],
            set_={
                "attempt": excluded.attempt,
                "sequence": excluded.sequence,
                "completed_slots": excluded.completed_slots,
                "canonical_slide": excluded.canonical_slide,
                "status": excluded.status,
                "updated_at": func.now(),
            },
            where=or_(
                GenerationCheckpoint.attempt < excluded.attempt,
                and_(
                    GenerationCheckpoint.attempt == excluded.attempt,
                    GenerationCheckpoint.sequence <= excluded.sequence,
                ),
            ),
        )
        .returning(GenerationCheckpoint)
    )


def build_job_checkpoints_query(
    job_id: UUID,
) -> Select[tuple[GenerationCheckpoint]]:
    return (
        select(GenerationCheckpoint)
        .where(GenerationCheckpoint.job_id == job_id)
        .order_by(GenerationCheckpoint.sequence, GenerationCheckpoint.slide_id)
    )


class GenerationCheckpointRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(self, checkpoint: CheckpointUpsert) -> GenerationCheckpoint | None:
        """Return the checkpoint, or None when a newer attempt already exists."""

        record = self.session.scalar(build_checkpoint_upsert_statement(checkpoint))
        return record

    def list_for_job(self, job_id: UUID) -> list[GenerationCheckpoint]:
        return list(self.session.scalars(build_job_checkpoints_query(job_id)))
