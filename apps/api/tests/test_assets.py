from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.assets import detect_image_type, get_asset_storage, get_image_provider
from app.auth import get_current_user
from app.database import get_session
from app.main import app
from app.models import AssetRecord, User
from app.generation.image_provider import GeneratedImageData, ImageGenerationRequest
from app.storage import LocalObjectStorage


class FakeSession:
    def __init__(self, scalar_value: object | None = None) -> None:
        self.scalar_value = scalar_value
        self.added: list[object] = []

    def add(self, value: object) -> None:
        self.added.append(value)

    def flush(self) -> None:
        return None

    def delete(self, value: object) -> None:
        self.added.remove(value)

    def scalar(self, _statement):
        return self.scalar_value


def _user() -> User:
    return User(
        id=uuid4(),
        email="asset-owner@example.com",
        normalized_email="asset-owner@example.com",
        password_hash="not-used",
        is_active=True,
    )


def test_image_type_uses_magic_bytes_not_declared_mime() -> None:
    assert detect_image_type(b"\x89PNG\r\n\x1a\ncontent") == "image/png"
    assert detect_image_type(b"\xff\xd8\xffcontent") == "image/jpeg"
    assert detect_image_type(b"RIFFxxxxWEBPcontent") == "image/webp"
    assert detect_image_type(b"<svg></svg>") is None


def test_upload_is_owned_and_content_is_retrievable(tmp_path: Path) -> None:
    user = _user()
    session = FakeSession()
    storage = LocalObjectStorage(tmp_path)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_asset_storage] = lambda: storage
    client = TestClient(app)
    try:
        data = b"\x89PNG\r\n\x1a\ncontent"
        response = client.post(
            "/v1/assets",
            files={"file": ("../../diagram.png", data, "application/octet-stream")},
        )
        assert response.status_code == 201
        assert response.json()["content_type"] == "image/png"
        record = session.added[0]
        assert isinstance(record, AssetRecord)
        assert record.owner_id == user.id
        assert record.filename == "diagram.png"
        assert storage.get(record.storage_key) == data

        session.scalar_value = record
        content = client.get(f"/v1/assets/{record.id}/content")
        assert content.status_code == 200
        assert content.content == data
        assert content.headers["x-content-type-options"] == "nosniff"

        deleted = client.delete(f"/v1/assets/{record.id}")
        assert deleted.status_code == 204
        assert not storage._path(record.storage_key).exists()  # noqa: SLF001 - verifies adapter cleanup
    finally:
        app.dependency_overrides.clear()


def test_asset_content_returns_not_found_without_owned_record(tmp_path: Path) -> None:
    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_session] = lambda: FakeSession(None)
    app.dependency_overrides[get_asset_storage] = lambda: LocalObjectStorage(tmp_path)
    client = TestClient(app)
    try:
        assert client.get(f"/v1/assets/{uuid4()}/content").status_code == 404
    finally:
        app.dependency_overrides.clear()


class FakeImageProvider:
    name = "fake-image"

    def __init__(self, data: bytes = b"\x89PNG\r\n\x1a\ngenerated") -> None:
        self.data = data
        self.requests: list[ImageGenerationRequest] = []

    def generate_image(self, request: ImageGenerationRequest) -> GeneratedImageData:
        self.requests.append(request)
        return GeneratedImageData(data=self.data, content_type="image/png")


def test_generate_image_is_permanently_disabled(tmp_path: Path) -> None:
    provider = FakeImageProvider()
    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_session] = FakeSession
    app.dependency_overrides[get_asset_storage] = lambda: LocalObjectStorage(tmp_path)
    app.dependency_overrides[get_image_provider] = lambda: provider
    try:
        response = TestClient(app).post(
            "/v1/assets/generate",
            json={"prompt": "A clean editorial illustration", "aspect_ratio": "16:9"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 410
    assert response.json()["detail"] == "Text-to-image generation has been disabled."
    assert provider.requests == []


def test_generate_image_rejects_blank_prompt_before_provider_call(tmp_path: Path) -> None:
    provider = FakeImageProvider()
    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_session] = FakeSession
    app.dependency_overrides[get_asset_storage] = lambda: LocalObjectStorage(tmp_path)
    app.dependency_overrides[get_image_provider] = lambda: provider
    try:
        response = TestClient(app).post(
            "/v1/assets/generate",
            json={"prompt": "   ", "aspect_ratio": "16:9"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 410
    assert response.json()["detail"] == "Text-to-image generation has been disabled."
    assert provider.requests == []
