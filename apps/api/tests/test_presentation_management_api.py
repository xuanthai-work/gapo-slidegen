from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.generation.router import get_generation_service
from app.generation.service import PresentationConflict, PresentationNotFound
from app.main import app


def _presentation(title: str = "Renamed deck"):
    return SimpleNamespace(
        id=uuid4(),
        title=title,
        document={"title": title},
        revision=4,
    )


class FakePresentationService:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.rename_calls: list[dict[str, object]] = []
        self.delete_calls: list[dict[str, object]] = []

    def rename_presentation(self, **kwargs):
        self.rename_calls.append(kwargs)
        if self.error:
            raise self.error
        result = _presentation(str(kwargs["title"]))
        result.id = kwargs["presentation_id"]
        result.revision = int(kwargs["expected_revision"]) + 1
        return result

    def delete_presentation(self, **kwargs):
        self.delete_calls.append(kwargs)
        if self.error:
            raise self.error


def test_rename_presentation_uses_authenticated_owner_and_revision() -> None:
    user = SimpleNamespace(id=uuid4())
    service = FakePresentationService()
    presentation_id = uuid4()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_generation_service] = lambda: service
    try:
        response = TestClient(app).patch(
            f"/v1/presentations/{presentation_id}/title",
            json={"expected_revision": 3, "title": "  New name  "},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["title"] == "New name"
    assert response.json()["revision"] == 4
    assert service.rename_calls == [
        {
            "presentation_id": presentation_id,
            "user": user,
            "expected_revision": 3,
            "title": "New name",
        }
    ]


def test_delete_presentation_uses_authenticated_owner_and_revision() -> None:
    user = SimpleNamespace(id=uuid4())
    service = FakePresentationService()
    presentation_id = uuid4()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_generation_service] = lambda: service
    try:
        response = TestClient(app).delete(
            f"/v1/presentations/{presentation_id}?expected_revision=7"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204
    assert service.delete_calls == [
        {
            "presentation_id": presentation_id,
            "user": user,
            "expected_revision": 7,
        }
    ]


def test_presentation_management_hides_unowned_record() -> None:
    service = FakePresentationService(error=PresentationNotFound("Presentation not found."))
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())
    app.dependency_overrides[get_generation_service] = lambda: service
    try:
        response = TestClient(app).delete(
            f"/v1/presentations/{uuid4()}?expected_revision=0"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_presentation_management_reports_revision_conflict() -> None:
    service = FakePresentationService(
        error=PresentationConflict("Presentation changed in another session.")
    )
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())
    app.dependency_overrides[get_generation_service] = lambda: service
    try:
        response = TestClient(app).patch(
            f"/v1/presentations/{uuid4()}/title",
            json={"expected_revision": 1, "title": "New name"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
