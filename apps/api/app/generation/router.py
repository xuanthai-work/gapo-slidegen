from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_session
from ..models import GenerationJob, JobStatus, JobType, PresentationRecord, User
from .service import GenerationService, SourceNotFound

router = APIRouter(tags=["generation"])


class GenerationInput(BaseModel):
    source_id: UUID
    slide_count: int = Field(default=10, ge=1, le=30)
    language: str = Field(default="en", min_length=2, max_length=32)


class JobView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID | None
    job_type: JobType
    status: JobStatus
    progress: int
    result: dict[str, object] | None
    error_code: str | None
    error_message: str | None


class PresentationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    document: dict[str, object]
    revision: int


def get_generation_service(session: Annotated[Session, Depends(get_session)]) -> GenerationService:
    return GenerationService(session)


@router.post("/v1/generations", response_model=JobView, status_code=status.HTTP_202_ACCEPTED)
def request_generation(
    payload: GenerationInput,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
) -> GenerationJob:
    try:
        return service.enqueue(
            user=user,
            source_id=payload.source_id,
            slide_count=payload.slide_count,
            language=payload.language,
        )
    except SourceNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/v1/jobs/{job_id}", response_model=JobView)
def get_job(
    job_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
) -> GenerationJob:
    job = service.get_job(job_id, user)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return job


@router.get("/v1/presentations/{presentation_id}", response_model=PresentationView)
def get_presentation(
    presentation_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
) -> PresentationRecord:
    presentation = service.get_presentation(presentation_id, user)
    if presentation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation not found.")
    return presentation
