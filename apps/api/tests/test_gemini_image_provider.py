from types import SimpleNamespace

import pytest

from app.generation.gemini_image_provider import GoogleAIStudioImageProvider
from app.generation.image_provider import ImageGenerationRequest
from app.generation.provider import ProviderResponseError


class FakeImageModels:
    def __init__(self, data: bytes | None) -> None:
        self.data = data
        self.calls: list[dict[str, object]] = []

    def generate_images(self, **kwargs):
        self.calls.append(kwargs)
        image = (
            SimpleNamespace(image_bytes=self.data, mime_type="image/png")
            if self.data is not None
            else None
        )
        return SimpleNamespace(
            generated_images=[
                SimpleNamespace(
                    image=image,
                    rai_filtered_reason="Safety filter" if image is None else None,
                )
            ]
        )


def test_google_image_provider_returns_bytes_without_network() -> None:
    models = FakeImageModels(b"\x89PNG\r\n\x1a\ngenerated")
    provider = GoogleAIStudioImageProvider(
        api_key="secret",
        model="chosen-image-model",
        client=SimpleNamespace(models=models),
    )

    result = provider.generate_image(
        ImageGenerationRequest(prompt="Editorial landscape", aspect_ratio="16:9")
    )

    assert result.data.startswith(b"\x89PNG")
    assert result.content_type == "image/png"
    assert models.calls[0]["model"] == "chosen-image-model"
    assert models.calls[0]["prompt"] == "Editorial landscape"
    assert models.calls[0]["config"].aspect_ratio == "16:9"
    assert models.calls[0]["config"].number_of_images == 1


def test_google_image_provider_surfaces_filtered_response_safely() -> None:
    provider = GoogleAIStudioImageProvider(
        api_key="secret",
        model="chosen-image-model",
        client=SimpleNamespace(models=FakeImageModels(None)),
    )

    with pytest.raises(ProviderResponseError, match="Safety filter"):
        provider.generate_image(
            ImageGenerationRequest(prompt="Filtered", aspect_ratio="1:1")
        )


def test_google_image_provider_redacts_key_from_errors() -> None:
    class FailingModels:
        def generate_images(self, **kwargs):
            raise RuntimeError("request rejected for secret")

    provider = GoogleAIStudioImageProvider(
        api_key="secret",
        model="chosen-image-model",
        client=SimpleNamespace(models=FailingModels()),
    )

    with pytest.raises(ProviderResponseError) as caught:
        provider.generate_image(
            ImageGenerationRequest(prompt="Image", aspect_ratio="16:9")
        )
    assert "secret" not in str(caught.value)
    assert "[redacted]" in str(caught.value)
