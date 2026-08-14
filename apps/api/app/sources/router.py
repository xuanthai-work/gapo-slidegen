from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field

from ..auth import get_current_user
from ..config import get_settings
from ..ingestion import InvalidDocumentError, SourceDocument, UnsupportedDocumentError
from ..models import SourceRecord, User
from .dependencies import get_source_service
from .service import SourceService

router = APIRouter(prefix="/v1/sources", tags=["sources"])


class SourceTextInput(BaseModel):
    kind: Literal["prompt", "manuscript"]
    title: str = Field(default="Untitled source", min_length=1, max_length=500)
    text: str = Field(min_length=1, max_length=500_000)


class StoredSourceView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: str
    title: str
    filename: str | None
    content_type: str | None
    extracted_text: str
    sections: list[dict[str, object]]
    requires_ocr: bool
    warnings: list[str]


@router.post("/text", response_model=StoredSourceView, status_code=status.HTTP_201_CREATED)
def create_text_source(
    payload: SourceTextInput,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SourceService, Depends(get_source_service)],
) -> SourceRecord:
    text = payload.text.replace("\x00", "").strip()
    document = SourceDocument(
        kind=payload.kind,
        title=payload.title.strip(),
        text=text,
        sections=[{"index": 0, "title": payload.title.strip(), "text": text}],
    )
    return service.create_text(user, document)


@router.post("/files", response_model=StoredSourceView, status_code=status.HTTP_201_CREATED)
async def create_file_source(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SourceService, Depends(get_source_service)],
    file: UploadFile = File(...),
) -> SourceRecord:
    settings = get_settings()
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_bytes} byte limit.",
        )
    try:
        return service.create_file(
            user,
            filename=file.filename or "upload",
            content_type=file.content_type,
            data=data,
        )
    except UnsupportedDocumentError as error:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(error)) from error
    except InvalidDocumentError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


@router.get("", response_model=list[StoredSourceView])
def list_sources(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SourceService, Depends(get_source_service)],
) -> list[SourceRecord]:
    return service.list_owned(user)


@router.get("/{source_id}", response_model=StoredSourceView)
def get_source(
    source_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SourceService, Depends(get_source_service)],
) -> SourceRecord:
    record = service.get_owned(source_id, user)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found.")
    return record


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    source_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SourceService, Depends(get_source_service)],
) -> None:
    if not service.delete_owned(source_id, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found.")
