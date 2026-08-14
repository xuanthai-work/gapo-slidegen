from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    presentation_id: UUID
    title: str
    text: str
    sections: list[dict[str, object]]
    language: str
    slide_count: int


class PresentationProvider(Protocol):
    name: str

    def generate(self, request: GenerationRequest) -> dict[str, object]: ...
