from typing import Literal

from pydantic import BaseModel, Field


SourceKind = Literal["prompt", "manuscript", "docx", "pptx", "pdf"]


class SourceSection(BaseModel):
    index: int = Field(ge=0)
    title: str
    text: str


class SourceDocument(BaseModel):
    kind: SourceKind
    title: str
    text: str
    sections: list[SourceSection]
    requires_ocr: bool = False
    warnings: list[str] = Field(default_factory=list)
