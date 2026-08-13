import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.presentation import PresentationStatus


class OutlineSlide(BaseModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str = Field(min_length=1, max_length=180)
    objective: str = Field(min_length=1, max_length=500)
    key_points: Annotated[list[str], Field(min_length=1, max_length=6)]


class Outline(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    slides: Annotated[list[OutlineSlide], Field(min_length=1, max_length=30)]


class PresentationCreate(BaseModel):
    prompt: str = Field(min_length=10, max_length=4000)
    language: Literal["vi", "en"] = "vi"
    slide_count: int = Field(default=7, ge=5, le=10)
    theme_key: Literal["gapo-light", "gapo-dark"] = "gapo-light"


class PresentationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    theme_key: Literal["gapo-light", "gapo-dark"] | None = None
    updated_at: datetime | None = None


class PresentationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    status: PresentationStatus
    slide_count: int
    updated_at: datetime


class PresentationDetail(PresentationSummary):
    prompt: str
    language: str
    theme_key: str
    outline: Outline | None = None
