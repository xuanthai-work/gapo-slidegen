from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.auth import get_auth_service
from app.auth.security import (
    hash_password,
    hash_session_token,
    normalize_email,
    verify_password,
)
from app.auth.service import SessionGrant
from app.main import app
from app.models import User


class FakeAuthService:
    def __init__(self) -> None:
        self.user = User(
            id=uuid4(),
            email="member@example.com",
            normalized_email="member@example.com",
            password_hash="not-returned",
            is_active=True,
        )
        self.logged_out_token: str | None = None

    def register(self, email: str, password: str) -> User:
        return self.user

    def login(self, email: str, password: str) -> SessionGrant:
        return SessionGrant(
            token="opaque-test-token",
            user=self.user,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )

    def resolve(self, token: str) -> User | None:
        return self.user if token == "opaque-test-token" else None

    def logout(self, token: str) -> None:
        self.logged_out_token = token


def test_password_and_session_tokens_are_not_stored_in_plaintext() -> None:
    encoded = hash_password("correct horse battery staple")
    valid, replacement = verify_password("correct horse battery staple", encoded)

    assert valid is True
    assert replacement is None
    assert "correct horse" not in encoded
    assert hash_session_token("opaque-token") != "opaque-token"
    assert len(hash_session_token("opaque-token")) == 64


def test_email_normalization_does_not_require_mailbox_verification() -> None:
    assert normalize_email("  Member@Example.COM ") == "member@example.com"


def test_auth_http_contract_sets_and_revokes_opaque_cookie() -> None:
    service = FakeAuthService()
    app.dependency_overrides[get_auth_service] = lambda: service
    client = TestClient(app)
    try:
        registered = client.post(
            "/v1/auth/register",
            json={"email": "member@example.com", "password": "long-enough-password"},
        )
        assert registered.status_code == 201
        assert "password" not in registered.text

        logged_in = client.post(
            "/v1/auth/login",
            json={"email": "member@example.com", "password": "long-enough-password"},
        )
        assert logged_in.status_code == 200
        assert "HttpOnly" in logged_in.headers["set-cookie"]
        assert client.cookies.get("slidegen_session") == "opaque-test-token"

        current = client.get("/v1/auth/me")
        assert current.status_code == 200
        assert current.json()["email"] == "member@example.com"

        logged_out = client.post("/v1/auth/logout")
        assert logged_out.status_code == 204
        assert service.logged_out_token == "opaque-test-token"
        assert client.cookies.get("slidegen_session") is None
    finally:
        app.dependency_overrides.clear()
