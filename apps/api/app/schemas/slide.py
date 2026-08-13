import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class TitleBody(BaseModel):
    subtitle: str | None = Field(default=None, max_length=300)


class BulletsBody(BaseModel):
    bullets: Annotated[list[str], Field(min_length=1, max_length=6)]


class ColumnsBody(BaseModel):
    left_title: str
    left_points: Annotated[list[str], Field(max_length=4)]
    right_title: str
    right_points: Annotated[list[str], Field(max_length=4)]


class QuoteBody(BaseModel):
    quote: str = Field(max_length=400)
    attribution: str | None = Field(default=None, max_length=160)


class StatisticBody(BaseModel):
    value: str = Field(max_length=40)
    label: str = Field(max_length=180)
    context: str | None = Field(default=None, max_length=300)


class SlideContent(BaseModel):
    layout: Literal["title", "title_bullets", "two_column", "statistic", "quote"]
    title: str = Field(min_length=1, max_length=180)
    body: TitleBody | BulletsBody | ColumnsBody | StatisticBody | QuoteBody
    speaker_notes: str | None = Field(default=None, max_length=2000)
    image_prompt: str | None = Field(default=None, max_length=1000)


class SlideUpdate(BaseModel):
    content: SlideContent
    updated_at: str | None = None


class SlideReorderItem(BaseModel):
    slide_id: uuid.UUID
    position: int = Field(ge=0)


class SlideReorderRequest(BaseModel):
    slides: Annotated[list[SlideReorderItem], Field(min_length=1, max_length=30)]
