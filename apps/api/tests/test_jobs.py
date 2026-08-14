from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.jobs.repository import (
    InvalidJobTransition,
    JobRepository,
    build_claim_query,
    build_owned_job_query,
    build_owned_jobs_query,
    transition,
)
from app.models import GenerationJob, JobStatus, JobType


def _queued_job() -> GenerationJob:
    return GenerationJob(
        id=uuid4(),
        owner_id=uuid4(),
        job_type=JobType.GENERATE,
        status=JobStatus.QUEUED,
        payload={},
    )


def test_claim_query_uses_postgres_skip_locked() -> None:
    sql = str(
        build_claim_query(JobType.GENERATE).compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "generate" in sql


def test_job_lifecycle_is_explicit_and_terminal() -> None:
    job = _queued_job()
    transition(job, JobStatus.RUNNING)
    assert job.attempt == 1
    assert job.claimed_at is not None

    transition(job, JobStatus.SUCCEEDED)
    assert job.finished_at is not None
    with pytest.raises(InvalidJobTransition):
        transition(job, JobStatus.RUNNING)


def test_job_cannot_skip_running_state() -> None:
    with pytest.raises(InvalidJobTransition):
        transition(_queued_job(), JobStatus.SUCCEEDED)


def test_job_can_be_canceled_but_not_resumed() -> None:
    job = _queued_job()
    transition(job, JobStatus.CANCELED)
    assert job.finished_at is not None
    with pytest.raises(InvalidJobTransition):
        transition(job, JobStatus.RUNNING)


def test_owned_job_query_filters_job_and_owner() -> None:
    job_id = uuid4()
    owner_id = uuid4()
    sql = str(
        build_owned_job_query(job_id, owner_id).compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert str(job_id) in sql
    assert str(owner_id) in sql
    assert "generation_jobs.owner_id" in sql


def test_owned_job_list_is_generation_only_recent_and_bounded() -> None:
    owner_id = uuid4()
    sql = str(
        build_owned_jobs_query(
            owner_id,
            job_type=JobType.GENERATE,
            limit=20,
        ).compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )
    assert str(owner_id) in sql
    assert "generation_jobs.owner_id" in sql
    assert "generation_jobs.job_type" in sql
    assert "ORDER BY generation_jobs.created_at DESC" in sql
    assert "LIMIT 20" in sql


def test_claimed_job_reports_initial_progress() -> None:
    job = _queued_job()

    class FakeSession:
        def scalar(self, statement):
            return job

        def flush(self):
            return None

    claimed = JobRepository(FakeSession()).claim_next(JobType.GENERATE)  # type: ignore[arg-type]

    assert claimed is job
    assert job.status is JobStatus.RUNNING
    assert job.progress == 10
