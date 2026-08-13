import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.errors import capability_not_implemented
from app.schemas.generation import GenerationJobResponse

presentation_router = APIRouter()
job_router = APIRouter()


@presentation_router.post("/{presentation_id}/generate", response_model=GenerationJobResponse)
async def start_generation(presentation_id: uuid.UUID) -> GenerationJobResponse:
    del presentation_id
    capability_not_implemented("Generation job service")


@job_router.get("/{job_id}", response_model=GenerationJobResponse)
async def get_generation_job(job_id: uuid.UUID) -> GenerationJobResponse:
    del job_id
    capability_not_implemented("Generation job service")


@job_router.get("/{job_id}/events", response_class=StreamingResponse)
async def generation_events(job_id: uuid.UUID) -> StreamingResponse:
    del job_id
    capability_not_implemented("Generation job service")
