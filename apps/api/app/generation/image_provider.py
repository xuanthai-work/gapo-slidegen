from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ImageGenerationRequest:
    prompt: str
    aspect_ratio: str


@dataclass(frozen=True, slots=True)
class GeneratedImageData:
    data: bytes
    content_type: str


class ImageGenerationProvider(Protocol):
    name: str

    def generate_image(self, request: ImageGenerationRequest) -> GeneratedImageData: ...
