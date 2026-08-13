import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

GenerationEventName = Literal[
    "job.started",
    "outline.started",
    "outline.completed",
    "slide.started",
    "slide.completed",
    "slide.failed",
    "job.completed",
    "job.failed",
]


class GenerationEvent(BaseModel):
    event: GenerationEventName
    job_id: uuid.UUID
    timestamp: datetime
    progress: int = Field(ge=0, le=100)
    payload: dict[str, Any] = Field(default_factory=dict)


class GenerationJobResponse(BaseModel):
    id: uuid.UUID
    presentation_id: uuid.UUID
    status: Literal["queued", "running", "completed", "failed"]
    current_step: str | None
    progress: int = Field(ge=0, le=100)
    provider: str | None = None
    model: str | None = None
    error_code: str | None = None
    error_message: str | None = None
