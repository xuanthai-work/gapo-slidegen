from datetime import UTC, datetime

from sqlalchemy import Select, exists, select
from sqlalchemy.orm import Session

from ..models import GenerationJob, JobStatus, SourceRecord
from ..storage import ObjectStorage


def build_expired_sources_query(
    *,
    now: datetime,
    limit: int,
) -> Select[tuple[SourceRecord]]:
    active_job_exists = exists().where(
        GenerationJob.source_id == SourceRecord.id,
        GenerationJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]),
    )
    return (
        select(SourceRecord)
        .where(
            SourceRecord.delete_after.is_not(None),
            SourceRecord.delete_after <= now,
            ~active_job_exists,
        )
        .order_by(SourceRecord.delete_after.asc(), SourceRecord.id.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    )


def delete_expired_sources(
    session: Session,
    storage: ObjectStorage,
    *,
    now: datetime | None = None,
    limit: int = 100,
) -> int:
    effective_now = now or datetime.now(UTC)
    records = list(
        session.scalars(build_expired_sources_query(now=effective_now, limit=limit))
    )
    for record in records:
        if record.storage_key:
            storage.delete(record.storage_key)
        session.delete(record)
    session.flush()
    return len(records)
