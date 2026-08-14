from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.generation.router import get_generation_service
from app.generation.service import GenerationService, JobConflict, JobNotFound
from app.main import app
from app.models import JobStatus, JobType


def _job(status: JobStatus = JobStatus.CANCELED):
    return SimpleNamespace(
        id=uuid4(),
        source_id=uuid4(),
        job_type=JobType.GENERATE,
        status=status,
        progress=10,
        result=None,
        error_code=None,
        error_message=None,
    )


class FakeGenerationService:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result or _job()
        self.error = error
        self.calls: list[tuple[object, object]] = []
        self.list_calls: list[tuple[object, int]] = []

    def cancel_job(self, job_id, user):
        self.calls.append((job_id, user))
        if self.error:
            raise self.error
        self.result.id = job_id
        return self.result

    def list_generation_jobs(self, user, limit):
        self.list_calls.append((user, limit))
        return [self.result]


def test_list_jobs_route_is_owned_and_bounded() -> None:
    user = SimpleNamespace(id=uuid4())
    service = FakeGenerationService(result=_job(JobStatus.RUNNING))
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_generation_service] = lambda: service
    try:
        response = TestClient(app).get("/v1/jobs?limit=7")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["status"] == "running"
    assert service.list_calls == [(user, 7)]


def test_cancel_job_route_uses_authenticated_owner() -> None:
    user = SimpleNamespace(id=uuid4())
    service = FakeGenerationService()
    job_id = uuid4()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_generation_service] = lambda: service
    try:
        response = TestClient(app).post(f"/v1/jobs/{job_id}/cancel")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "canceled"
    assert service.calls == [(job_id, user)]


def test_cancel_job_route_hides_unowned_job() -> None:
    service = FakeGenerationService(error=JobNotFound("Job not found."))
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())
    app.dependency_overrides[get_generation_service] = lambda: service
    try:
        response = TestClient(app).post(f"/v1/jobs/{uuid4()}/cancel")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_cancel_job_route_rejects_terminal_job() -> None:
    service = FakeGenerationService(
        error=JobConflict("Only a queued or running job can be canceled.")
    )
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())
    app.dependency_overrides[get_generation_service] = lambda: service
    try:
        response = TestClient(app).post(f"/v1/jobs/{uuid4()}/cancel")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409


class FakeCancelSession:
    def __init__(self, job) -> None:
        self.job = job
        self.flush_count = 0

    def scalar(self, statement):
        return self.job

    def flush(self):
        self.flush_count += 1


def test_cancel_service_transitions_active_job_and_is_idempotent() -> None:
    job = _job(JobStatus.RUNNING)
    session = FakeCancelSession(job)
    service = GenerationService(session)  # type: ignore[arg-type]
    user = SimpleNamespace(id=uuid4())

    assert service.cancel_job(job.id, user).status is JobStatus.CANCELED  # type: ignore[arg-type]
    assert service.cancel_job(job.id, user).status is JobStatus.CANCELED  # type: ignore[arg-type]
    assert session.flush_count == 1


def test_cancel_service_rejects_completed_job() -> None:
    job = _job(JobStatus.SUCCEEDED)
    service = GenerationService(FakeCancelSession(job))  # type: ignore[arg-type]

    try:
        service.cancel_job(job.id, SimpleNamespace(id=uuid4()))  # type: ignore[arg-type]
    except JobConflict as error:
        assert "queued or running" in str(error)
    else:
        raise AssertionError("Expected a terminal job conflict")
