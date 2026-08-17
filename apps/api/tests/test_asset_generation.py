from pathlib import Path
from uuid import uuid4

from app.generation.image_provider import GeneratedImageData, ImageGenerationRequest
from app.generation.stages.asset_generator import ImageAssetGenerator, NullAssetGenerator
from app.generation.stages.models import (
    AssetPlan,
    AssetRequest,
    AssetSlot,
    GeneratedAsset,
    StoryOutline,
    StoryOutlineItem,
)
from app.storage import LocalObjectStorage


class FakeImageProvider:
    name = "fake-image"

    def __init__(self, data: bytes = b"\x89PNG\r\n\x1a\ngenerated") -> None:
        self.data = data
        self.requests: list[ImageGenerationRequest] = []

    def generate_image(self, request: ImageGenerationRequest) -> GeneratedImageData:
        self.requests.append(request)
        return GeneratedImageData(data=self.data, content_type="image/png")


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def add(self, value: object) -> None:
        self.added.append(value)

    def flush(self) -> None:
        return None

    def commit(self) -> None:
        self.committed = True


def test_null_asset_generator_returns_empty_list() -> None:
    generator = NullAssetGenerator()
    assert generator.generate(AssetPlan()) == []


def test_image_asset_generator_stores_generated_assets(tmp_path: Path) -> None:
    owner_id = uuid4()
    storage = LocalObjectStorage(tmp_path)
    provider = FakeImageProvider()
    generator = ImageAssetGenerator(
        image_provider=provider,
        session_factory=FakeSession,
        storage=storage,
    )
    plan = AssetPlan(
        owner_id=owner_id,
        requests=[
            AssetRequest(
                slot=AssetSlot(slide_index=1, name="main_visual_panel", kind="image"),
                prompt="A hero illustration",
            )
        ],
    )

    generated = generator.generate(plan)

    assert len(generated) == 1
    asset = generated[0]
    assert asset.slot.name == "main_visual_panel"
    assert asset.asset_id is not None
    assert asset.warning is None
    assert provider.requests == [ImageGenerationRequest(prompt="A hero illustration", aspect_ratio="16:9")]


def test_image_asset_generator_skips_requests_without_owner() -> None:
    provider = FakeImageProvider()
    generator = ImageAssetGenerator(
        image_provider=provider,
        session_factory=FakeSession,
        storage=LocalObjectStorage(Path("/tmp")),
    )
    plan = AssetPlan(
        requests=[
            AssetRequest(
                slot=AssetSlot(slide_index=0, name="x", kind="image"),
                prompt="prompt",
            )
        ],
    )
    assert generator.generate(plan) == []
    assert provider.requests == []


def test_image_asset_generator_gracefully_handles_provider_failure() -> None:
    class FailingProvider:
        name = "failing"

        def generate_image(self, _request: ImageGenerationRequest) -> GeneratedImageData:
            raise RuntimeError("provider down")

    generator = ImageAssetGenerator(
        image_provider=FailingProvider(),  # type: ignore[arg-type]
        session_factory=FakeSession,
        storage=LocalObjectStorage(Path("/tmp")),
    )
    plan = AssetPlan(
        owner_id=uuid4(),
        requests=[
            AssetRequest(
                slot=AssetSlot(slide_index=0, name="x", kind="image"),
                prompt="prompt",
            )
        ],
    )
    generated = generator.generate(plan)
    assert len(generated) == 1
    assert generated[0].asset_id is None
    assert "provider down" in (generated[0].warning or "")
