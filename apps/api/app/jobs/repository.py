from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from ..models import GenerationJob, JobStatus, JobType


class InvalidJobTransition(ValueError):
    pass


ALLOWED_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.QUEUED: frozenset({JobStatus.RUNNING, JobStatus.CANCELED}),
    JobStatus.RUNNING: frozenset({JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED}),
    JobStatus.SUCCEEDED: frozenset(),
    JobStatus.FAILED: frozenset(),
    JobStatus.CANCELED: frozenset(),
}


def transition(job: GenerationJob, target: JobStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[job.status]:
        raise InvalidJobTransition(f"Cannot transition job from {job.status} to {target}.")
    now = datetime.now(UTC)
    job.status = target
    if target is JobStatus.RUNNING:
        job.claimed_at = now
        job.attempt = (job.attempt or 0) + 1
    if target in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED}:
        job.finished_at = now


def build_claim_query(job_type: JobType | None = None) -> Select[tuple[GenerationJob]]:
    statement = (
        select(GenerationJob)
        .where(GenerationJob.status == JobStatus.QUEUED)
        .order_by(GenerationJob.created_at, GenerationJob.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    return statement.where(GenerationJob.job_type == job_type) if job_type else statement


def build_owned_job_query(job_id: UUID, owner_id: UUID) -> Select[tuple[GenerationJob]]:
    return select(GenerationJob).where(
        GenerationJob.id == job_id,
        GenerationJob.owner_id == owner_id,
    )


def build_owned_jobs_query(
    owner_id: UUID,
    *,
    job_type: JobType | None = None,
    limit: int = 20,
) -> Select[tuple[GenerationJob]]:
    statement = (
        select(GenerationJob)
        .where(GenerationJob.owner_id == owner_id)
        .order_by(GenerationJob.created_at.desc(), GenerationJob.id.desc())
        .limit(limit)
    )
    return statement.where(GenerationJob.job_type == job_type) if job_type else statement


class JobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def enqueue(
        self,
        *,
        owner_id: UUID,
        job_type: JobType,
        payload: dict[str, object],
        source_id: UUID | None = None,
    ) -> GenerationJob:
        job = GenerationJob(
            id=uuid4(),
            owner_id=owner_id,
            source_id=source_id,
            job_type=job_type,
            status=JobStatus.QUEUED,
            progress=0,
            attempt=0,
            payload=payload,
        )
        self.session.add(job)
        self.session.flush()
        return job

    def get_owned(self, job_id: UUID, owner_id: UUID) -> GenerationJob | None:
        return self.session.scalar(build_owned_job_query(job_id, owner_id))

    def list_owned(
        self,
        owner_id: UUID,
        *,
        job_type: JobType | None = None,
        limit: int = 20,
    ) -> list[GenerationJob]:
        return list(
            self.session.scalars(
                build_owned_jobs_query(owner_id, job_type=job_type, limit=limit)
            )
        )

    def claim_next(self, job_type: JobType | None = None) -> GenerationJob | None:
        job = self.session.scalar(build_claim_query(job_type))
        if job is None:
            return None
        transition(job, JobStatus.RUNNING)
        job.progress = 10
        self.session.flush()
        return job

    def update_progress(self, job: GenerationJob, progress: int) -> None:
        if job.status is not JobStatus.RUNNING:
            raise InvalidJobTransition("Only running jobs can report progress.")
        if not 0 <= progress <= 100:
            raise ValueError("Job progress must be between 0 and 100.")
        job.progress = progress
        self.session.flush()

    def succeed(self, job: GenerationJob, result: dict[str, object]) -> None:
        transition(job, JobStatus.SUCCEEDED)
        job.progress = 100
        job.result = result
        self.session.flush()

    def fail(self, job: GenerationJob, *, code: str, message: str) -> None:
        transition(job, JobStatus.FAILED)
        job.error_code = code
        job.error_message = message
        self.session.flush()
