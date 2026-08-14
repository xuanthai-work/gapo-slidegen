from google import genai
from google.genai import types

from .image_provider import GeneratedImageData, ImageGenerationRequest
from .provider import ProviderResponseError


class GoogleAIStudioImageProvider:
    name = "google-ai-studio"

    def __init__(self, *, api_key: str, model: str, client=None) -> None:
        self.api_key = api_key
        self.model = model
        self.client = client

    def generate_image(self, request: ImageGenerationRequest) -> GeneratedImageData:
        owns_client = self.client is None
        client = self.client or genai.Client(api_key=self.api_key)
        try:
            response = client.models.generate_images(
                model=self.model,
                prompt=request.prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=request.aspect_ratio,
                    output_mime_type="image/png",
                    include_rai_reason=True,
                ),
            )
            generated = response.generated_images or []
            if not generated or generated[0].image is None:
                reason = next(
                    (
                        item.rai_filtered_reason
                        for item in generated
                        if item.rai_filtered_reason
                    ),
                    None,
                )
                suffix = f" Reason: {reason[:300]}" if reason else ""
                raise ProviderResponseError(
                    "Google AI Studio did not return an image." + suffix
                )
            image = generated[0].image
            if not image.image_bytes:
                raise ProviderResponseError("Google AI Studio returned empty image data.")
            return GeneratedImageData(
                data=image.image_bytes,
                content_type=image.mime_type or "image/png",
            )
        except ProviderResponseError:
            raise
        except Exception as error:
            message = str(error).replace(self.api_key, "[redacted]")[:500]
            raise ProviderResponseError(
                f"Google AI Studio image request failed: {message}"
            ) from error
        finally:
            if owns_client:
                client.close()
