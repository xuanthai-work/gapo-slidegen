from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.jobs.repository import InvalidJobTransition, build_claim_query, transition
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
