import uuid

from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.main import app
from app.schemas.auth import CurrentUser


def override_current_user() -> CurrentUser:
    return CurrentUser(
        id=uuid.UUID("4c855e9a-64eb-4d6d-81f7-57f5e7d512f8"),
        email="minh.anh@example.com",
        display_name="Minh Anh",
    )


def test_me_returns_normalized_current_user() -> None:
    app.dependency_overrides[get_current_user] = override_current_user
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/auth/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["email"] == "minh.anh@example.com"


def test_me_requires_bearer_token() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
