import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from app.api.routes.outlines import get_outline_service
from app.api.routes.presentations import get_presentation_service
from app.auth.dependencies import get_current_user
from app.main import app
from app.schemas.auth import CurrentUser
from app.services.presentations import PresentationNotFoundError

OWNER_ID = uuid.UUID("10000000-0000-0000-0000-000000000001")
OTHER_ID = uuid.UUID("20000000-0000-0000-0000-000000000002")
PRESENTATION_ID = uuid.UUID("30000000-0000-0000-0000-000000000003")
OUTLINE = {
    "title": "Owned deck",
    "slides": [
        {
            "id": f"slide-{index}",
            "title": f"Slide {index}",
            "objective": f"Objective {index}",
            "key_points": [f"Point {index}"],
        }
        for index in range(1, 6)
    ],
}


def current_user(user_id: uuid.UUID) -> CurrentUser:
    return CurrentUser(id=user_id, email=f"{user_id}@example.com")


class OwnedPresentationService:
    def __init__(self) -> None:
        self.created_owner_ids: list[uuid.UUID] = []
        self.item = SimpleNamespace(
            id=PRESENTATION_ID,
            owner_id=OWNER_ID,
            title="Owned deck",
            prompt="Create an owned presentation",
            language="en",
            slide_count=5,
            theme_key="gapo-light",
            status="draft",
            outline=OUTLINE,
            updated_at=datetime.now(UTC),
        )

    async def list_owned(self, owner_id: uuid.UUID) -> list[Any]:
        return [self.item] if owner_id == OWNER_ID else []

    async def create(self, owner_id: uuid.UUID, payload: Any) -> Any:
        self.created_owner_ids.append(owner_id)
        return SimpleNamespace(
            **{
                **vars(self.item),
                "owner_id": owner_id,
                "prompt": payload.prompt,
                "language": payload.language,
                "slide_count": payload.slide_count,
                "theme_key": payload.theme_key,
                "outline": None,
            }
        )

    async def require_owned(self, presentation_id: uuid.UUID, owner_id: uuid.UUID) -> Any:
        if presentation_id != PRESENTATION_ID or owner_id != OWNER_ID:
            raise PresentationNotFoundError
        return self.item

    async def update(self, presentation_id: uuid.UUID, owner_id: uuid.UUID, payload: Any) -> Any:
        await self.require_owned(presentation_id, owner_id)
        if payload.title:
            self.item.title = payload.title
        return self.item

    async def delete(self, presentation_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        await self.require_owned(presentation_id, owner_id)


class OwnedOutlineService:
    async def generate(self, presentation_id: uuid.UUID, owner_id: uuid.UUID) -> dict[str, Any]:
        if presentation_id != PRESENTATION_ID or owner_id != OWNER_ID:
            raise PresentationNotFoundError
        return OUTLINE

    async def update(self, presentation_id: uuid.UUID, owner_id: uuid.UUID, outline: Any) -> Any:
        if presentation_id != PRESENTATION_ID or owner_id != OWNER_ID:
            raise PresentationNotFoundError
        return outline


def request_as(user_id: uuid.UUID, method: str, path: str, **kwargs: Any) -> Any:
    app.dependency_overrides[get_current_user] = lambda: current_user(user_id)
    try:
        with TestClient(app) as client:
            return client.request(method, path, **kwargs)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_get_presentation_hides_resource_from_another_user() -> None:
    service = OwnedPresentationService()
    app.dependency_overrides[get_presentation_service] = lambda: service
    owner_response = request_as(OWNER_ID, "GET", f"/api/v1/presentations/{PRESENTATION_ID}")
    other_response = request_as(OTHER_ID, "GET", f"/api/v1/presentations/{PRESENTATION_ID}")
    assert owner_response.status_code == 200
    assert other_response.status_code == 404


def test_list_and_create_always_use_current_owner() -> None:
    service = OwnedPresentationService()
    app.dependency_overrides[get_presentation_service] = lambda: service
    owner_list = request_as(OWNER_ID, "GET", "/api/v1/presentations")
    other_list = request_as(OTHER_ID, "GET", "/api/v1/presentations")
    payload = {
        "prompt": "Create a secure presentation",
        "language": "en",
        "slide_count": 5,
        "theme_key": "gapo-light",
    }
    owner_create = request_as(OWNER_ID, "POST", "/api/v1/presentations", json=payload)
    other_create = request_as(OTHER_ID, "POST", "/api/v1/presentations", json=payload)
    assert len(owner_list.json()) == 1
    assert other_list.json() == []
    assert owner_create.status_code == 201
    assert other_create.status_code == 201
    assert service.created_owner_ids == [OWNER_ID, OTHER_ID]


def test_update_presentation_hides_resource_from_another_user() -> None:
    service = OwnedPresentationService()
    app.dependency_overrides[get_presentation_service] = lambda: service
    path = f"/api/v1/presentations/{PRESENTATION_ID}"
    owner_response = request_as(OWNER_ID, "PATCH", path, json={"title": "Updated"})
    other_response = request_as(OTHER_ID, "PATCH", path, json={"title": "Stolen"})
    assert owner_response.status_code == 200
    assert other_response.status_code == 404


def test_delete_presentation_hides_resource_from_another_user() -> None:
    service = OwnedPresentationService()
    app.dependency_overrides[get_presentation_service] = lambda: service
    owner_response = request_as(OWNER_ID, "DELETE", f"/api/v1/presentations/{PRESENTATION_ID}")
    other_response = request_as(OTHER_ID, "DELETE", f"/api/v1/presentations/{PRESENTATION_ID}")
    assert owner_response.status_code == 204
    assert other_response.status_code == 404


def test_outline_endpoints_hide_resource_from_another_user() -> None:
    service = OwnedOutlineService()
    app.dependency_overrides[get_outline_service] = lambda: service
    for suffix, method, body in [
        ("outline/generate", "POST", None),
        ("outline", "PUT", OUTLINE),
    ]:
        path = f"/api/v1/presentations/{PRESENTATION_ID}/{suffix}"
        owner_response = request_as(OWNER_ID, method, path, json=body)
        other_response = request_as(OTHER_ID, method, path, json=body)
        assert owner_response.status_code == 200
        assert other_response.status_code == 404
