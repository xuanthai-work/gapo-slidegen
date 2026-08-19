import asyncio
import json
import logging
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import get_settings
from ..database import SessionLocal, get_session
from ..models import GenerationJob, JobStatus, JobType, OutlineRecord, PresentationRecord, User
from .checkpoint_repository import GenerationCheckpointRepository
from .checkpoints import GenerationCheckpointService
from .event_factory import build_generation_event_subscriber
from .event_sse import (
    acquire_sse_slot,
    iterate_generation_sse,
    release_sse_slot,
    TERMINAL_STATUSES,
)
from .factory import build_rewrite_provider, build_story_provider
from .outlines import (
    InvalidOutline,
    OutlineConflict,
    OutlineNotFound,
    OutlineService,
)
from .service import (
    GenerationService,
    JobConflict,
    JobNotFound,
    PresentationAssetNotFound,
    PresentationConflict,
    PresentationNotFound,
    SourceNotFound,
)
from .provider import (
    ProviderConfigurationError,
    ProviderError,
    RewriteProvider,
    RewriteRequest,
    RewriteTextItem,
    SlideRewriteRequest,
)
from .validation import InvalidPresentationDocument, validate_presentation_document

router = APIRouter(tags=["generation"])
logger = logging.getLogger(__name__)


class GenerationInput(BaseModel):
    source_id: UUID | None = None
    outline_id: UUID | None = None
    language: str = Field(default="en", min_length=2, max_length=32)
    theme_id: Literal[
        "modern-blue",
        "editorial-cobalt",
        "warm-studio",
        "midnight-signal",
    ] = "modern-blue"


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


class PresentationUpdate(BaseModel):
    expected_revision: int = Field(ge=0)
    document: dict[str, object]


class PresentationTitleUpdate(BaseModel):
    expected_revision: int = Field(ge=0)
    title: str = Field(min_length=1, max_length=500)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Presentation title cannot be empty.")
        return title


class OutlineInput(BaseModel):
    source_id: UUID
    slide_count: int = Field(default=10, ge=1, le=30)
    language: str = Field(default="en", min_length=2, max_length=32)


class OutlineStoryBlock(BaseModel):
    heading: str = Field(default="", max_length=160)
    body: str = Field(default="", max_length=600)
    label: str = Field(default="", max_length=80)
    value: str = Field(default="", max_length=80)


class OutlineItem(BaseModel):
    id: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(default="", max_length=100_000)
    layout: Literal[
        "cover",
        "feature-grid",
        "feature-list",
        "split-image",
        "alternating-cards",
        "profile-cards",
        "highlight-metrics",
    ] | None = None
    blocks: list[OutlineStoryBlock] = Field(default_factory=list, max_length=6)


class OutlineView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID | None
    title: str
    language: str
    items: list[OutlineItem]
    revision: int


class OutlineUpdate(BaseModel):
    expected_revision: int = Field(ge=0)
    items: list[OutlineItem] = Field(min_length=1, max_length=30)


class RewriteInput(BaseModel):
    text: str = Field(min_length=1, max_length=100_000)
    instruction: str = Field(min_length=1, max_length=2_000)
    language: str = Field(default="en", min_length=2, max_length=32)


class RewriteOutput(BaseModel):
    text: str
    provider: str


class SlideRewriteItem(BaseModel):
    id: str = Field(min_length=1, max_length=160)
    text: str = Field(min_length=1, max_length=100_000)


class SlideRewriteInput(BaseModel):
    items: list[SlideRewriteItem] = Field(min_length=1, max_length=50)
    instruction: str = Field(min_length=1, max_length=2_000)
    language: str = Field(default="en", min_length=2, max_length=32)

    @model_validator(mode="after")
    def validate_items(self):
        ids = [item.id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Slide text block ids must be unique.")
        if sum(len(item.text) for item in self.items) > 100_000:
            raise ValueError("Slide text content is too large.")
        return self


class SlideRewriteOutput(BaseModel):
    items: list[SlideRewriteItem]
    provider: str


def get_generation_service(session: Annotated[Session, Depends(get_session)]) -> GenerationService:
    return GenerationService(session)


def get_outline_service(session: Annotated[Session, Depends(get_session)]) -> OutlineService:
    try:
        return OutlineService(session, build_story_provider())
    except ProviderConfigurationError as error:
        raise _service_unavailable_from_provider(error) from error


def get_rewrite_provider() -> RewriteProvider:
    try:
        return build_rewrite_provider()
    except ProviderConfigurationError as error:
        raise _service_unavailable_from_provider(error) from error


def _service_unavailable_from_provider(error: ProviderConfigurationError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=str(error),
    )


def _bad_gateway_from_provider(error: ProviderError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error))


def _outline_http_error(error: Exception) -> HTTPException:
    if isinstance(error, OutlineNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, InvalidOutline):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error))
    if isinstance(error, OutlineConflict):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, ProviderError):
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error))
    raise TypeError(f"Unsupported outline error: {type(error)!r}")


def _presentation_http_error(error: Exception) -> HTTPException:
    if isinstance(error, PresentationNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, PresentationConflict):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, PresentationAssetNotFound):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error))
    if isinstance(error, InvalidPresentationDocument):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error))
    raise TypeError(f"Unsupported presentation error: {type(error)!r}")


def _job_http_error(error: Exception) -> HTTPException:
    if isinstance(error, JobNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, JobConflict):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    raise TypeError(f"Unsupported job error: {type(error)!r}")


def _raise_not_found(detail: str) -> None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _resolve_generation_target(payload: GenerationInput) -> Literal["outline", "source"]:
    if payload.outline_id is not None and payload.source_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Choose either outline_id or source_id, not both.",
        )
    if payload.outline_id is not None:
        return "outline"
    if payload.source_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="outline_id or source_id is required.",
        )
    return "source"


def _sse_progress_event(job: GenerationJob) -> str:
    payload = JobView.model_validate(job).model_dump_json()
    return f"event: progress\ndata: {payload}\n\n"


def _sse_slide_event(stream: dict[str, object], stream_slides: list[object]) -> str:
    stream_payload = json.dumps(
        {
            "stage": stream.get("stage") or "rendering",
            "message": stream.get("message") or "Building slides...",
            "slide_count": len(stream_slides),
            "latest_slide": stream_slides[-1] if stream_slides else None,
            "slides": stream_slides,
        },
        ensure_ascii=False,
    )
    return f"event: slide\ndata: {stream_payload}\n\n"


@router.post("/v1/ai/rewrite", response_model=RewriteOutput)
def rewrite_text(
    payload: RewriteInput,
    user: Annotated[User, Depends(get_current_user)],
    provider: Annotated[RewriteProvider, Depends(get_rewrite_provider)],
) -> RewriteOutput:
    del user
    try:
        text = provider.rewrite_text(
            RewriteRequest(
                text=payload.text,
                instruction=payload.instruction,
                language=payload.language,
            )
        )
        return RewriteOutput(text=text, provider=provider.name)
    except ProviderConfigurationError as error:
        raise _service_unavailable_from_provider(error) from error
    except ProviderError as error:
        raise _bad_gateway_from_provider(error) from error


@router.post("/v1/ai/rewrite-slide", response_model=SlideRewriteOutput)
def rewrite_slide(
    payload: SlideRewriteInput,
    user: Annotated[User, Depends(get_current_user)],
    provider: Annotated[RewriteProvider, Depends(get_rewrite_provider)],
) -> SlideRewriteOutput:
    del user
    try:
        items = provider.rewrite_slide(
            SlideRewriteRequest(
                items=[RewriteTextItem(id=item.id, text=item.text) for item in payload.items],
                instruction=payload.instruction,
                language=payload.language,
            )
        )
        return SlideRewriteOutput(
            items=[SlideRewriteItem(id=item.id, text=item.text) for item in items],
            provider=provider.name,
        )
    except ProviderConfigurationError as error:
        raise _service_unavailable_from_provider(error) from error
    except ProviderError as error:
        raise _bad_gateway_from_provider(error) from error


@router.post("/v1/outlines", response_model=OutlineView, status_code=status.HTTP_201_CREATED)
def create_outline(
    payload: OutlineInput,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[OutlineService, Depends(get_outline_service)],
) -> OutlineRecord:
    try:
        return service.create(
            user=user,
            source_id=payload.source_id,
            slide_count=payload.slide_count,
            language=payload.language,
        )
    except (OutlineNotFound, InvalidOutline, ProviderError) as error:
        raise _outline_http_error(error) from error


@router.get("/v1/outlines/{outline_id}", response_model=OutlineView)
def get_outline(
    outline_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[OutlineService, Depends(get_outline_service)],
) -> OutlineRecord:
    outline = service.get_owned(outline_id, user)
    if outline is None:
        _raise_not_found("Outline not found.")
    return outline


@router.patch("/v1/outlines/{outline_id}", response_model=OutlineView)
def update_outline(
    outline_id: UUID,
    payload: OutlineUpdate,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[OutlineService, Depends(get_outline_service)],
) -> OutlineRecord:
    try:
        return service.update(
            outline_id=outline_id,
            user=user,
            expected_revision=payload.expected_revision,
            items=[item.model_dump() for item in payload.items],
        )
    except (InvalidOutline, OutlineNotFound, OutlineConflict) as error:
        raise _outline_http_error(error) from error


@router.post("/v1/generations", response_model=JobView, status_code=status.HTTP_202_ACCEPTED)
def request_generation(
    payload: GenerationInput,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
) -> GenerationJob:
    try:
        target = _resolve_generation_target(payload)
        if target == "outline":
            return service.enqueue_outline(
                user=user,
                outline_id=payload.outline_id,
                theme_id=payload.theme_id,
            )
        return service.enqueue(
            user=user,
            source_id=payload.source_id,
            language=payload.language,
            theme_id=payload.theme_id,
        )
    except SourceNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/v1/jobs", response_model=list[JobView])
def list_jobs(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[GenerationJob]:
    return service.list_generation_jobs(user, limit)


@router.get("/v1/jobs/{job_id}", response_model=JobView)
def get_job(
    job_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
) -> GenerationJob:
    job = service.get_job(job_id, user)
    if job is None:
        _raise_not_found("Job not found.")
    return job


@router.post("/v1/jobs/{job_id}/cancel", response_model=JobView)
def cancel_job(
    job_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
) -> GenerationJob:
    try:
        return service.cancel_job(job_id, user)
    except (JobNotFound, JobConflict) as error:
        raise _job_http_error(error) from error


def _sse_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }


@router.get("/v1/jobs/{job_id}/events")
async def stream_job_events(
    job_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    """Stream job progress without holding an ORM session for the response life."""

    with SessionLocal() as session:
        job = GenerationService(session).get_job(job_id, user)
        if job is None:
            _raise_not_found("Job not found.")
        initial_progress = JobView.model_validate(job).model_dump_json()
        checkpoint_slides = [
            row.canonical_slide
            for row in GenerationCheckpointService(
                GenerationCheckpointRepository(session)
            ).list_for_job(job_id)
            if isinstance(row.canonical_slide, dict)
        ]

    user_key = str(user.id)
    if not acquire_sse_slot(user_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many live generation streams.",
        )

    async def poll_terminal() -> tuple[str | None, bool]:
        def _read() -> tuple[str | None, bool]:
            with SessionLocal() as session:
                current = GenerationService(session).get_job(job_id, user)
                if current is None:
                    return json.dumps({"detail": "Job not found."}), True
                payload = JobView.model_validate(current).model_dump_json()
                return payload, current.status.value in TERMINAL_STATUSES

        return await asyncio.to_thread(_read)

    settings = get_settings()
    subscriber = None
    if settings.generation_streaming_enabled:
        try:
            subscriber = build_generation_event_subscriber(settings)
        except Exception as error:
            logger.warning("generation Redis subscriber unavailable: %s", error)
    live = subscriber.subscribe(str(job_id)) if subscriber else None

    async def guarded(chunks):
        try:
            async for chunk in chunks:
                yield chunk
        finally:
            release_sse_slot(user_key)
            if subscriber is not None:
                aclose = getattr(subscriber, "aclose", None)
                if aclose is not None:
                    try:
                        await aclose()
                    except Exception:
                        pass

    if live is not None or checkpoint_slides:
        return StreamingResponse(
            guarded(
                iterate_generation_sse(
                    initial_progress=initial_progress,
                    checkpoint_slides=checkpoint_slides,
                    live_events=live,
                    poll_terminal=poll_terminal,
                )
            ),
            media_type="text/event-stream",
            headers=_sse_headers(),
        )

    async def legacy_poll():
        last_payload: str | None = None
        last_stream_slide_count = 0
        elapsed_heartbeat = 0.0
        poll_seconds = 0.2
        heartbeat_seconds = 25
        while True:
            def _read_job() -> GenerationJob | None:
                with SessionLocal() as session:
                    return GenerationService(session).get_job(job_id, user)

            job = await asyncio.to_thread(_read_job)
            if job is None:
                payload = json.dumps({"detail": "Job not found."})
                if payload != last_payload:
                    yield f"event: error\ndata: {payload}\n\n"
                break
            payload = JobView.model_validate(job).model_dump_json()
            if payload != last_payload:
                last_payload = payload
                yield _sse_progress_event(job)

            stream = job.stream_data if isinstance(job.stream_data, dict) else None
            stream_slides = stream.get("slides") if stream else None
            if isinstance(stream_slides, list) and len(stream_slides) > last_stream_slide_count:
                last_stream_slide_count = len(stream_slides)
                yield _sse_slide_event(stream or {}, stream_slides)

            if job.status.value in TERMINAL_STATUSES:
                break
            await asyncio.sleep(poll_seconds)
            elapsed_heartbeat += poll_seconds
            if elapsed_heartbeat >= heartbeat_seconds:
                yield ":heartbeat\n\n"
                elapsed_heartbeat = 0.0

    return StreamingResponse(
        guarded(legacy_poll()),
        media_type="text/event-stream",
        headers=_sse_headers(),
    )


@router.get("/v1/presentations/{presentation_id}", response_model=PresentationView)
def get_presentation(
    presentation_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
) -> PresentationRecord:
    presentation = service.get_presentation(presentation_id, user)
    if presentation is None:
        _raise_not_found("Presentation not found.")
    return presentation


@router.get("/v1/presentations", response_model=list[PresentationView])
def list_presentations(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
) -> list[PresentationRecord]:
    return service.list_presentations(user)


@router.patch("/v1/presentations/{presentation_id}/title", response_model=PresentationView)
def rename_presentation(
    presentation_id: UUID,
    payload: PresentationTitleUpdate,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
) -> PresentationRecord:
    try:
        return service.rename_presentation(
            presentation_id=presentation_id,
            user=user,
            expected_revision=payload.expected_revision,
            title=payload.title,
        )
    except (PresentationNotFound, PresentationConflict) as error:
        raise _presentation_http_error(error) from error


@router.delete("/v1/presentations/{presentation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_presentation(
    presentation_id: UUID,
    expected_revision: Annotated[int, Query(ge=0)],
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
) -> None:
    try:
        service.delete_presentation(
            presentation_id=presentation_id,
            user=user,
            expected_revision=expected_revision,
        )
    except (PresentationNotFound, PresentationConflict) as error:
        raise _presentation_http_error(error) from error


@router.patch("/v1/presentations/{presentation_id}", response_model=PresentationView)
def update_presentation(
    presentation_id: UUID,
    payload: PresentationUpdate,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
) -> PresentationRecord:
    try:
        validate_presentation_document(payload.document, presentation_id)
        return service.update_presentation(
            presentation_id=presentation_id,
            user=user,
            expected_revision=payload.expected_revision,
            document=payload.document,
        )
    except (
        InvalidPresentationDocument,
        PresentationNotFound,
        PresentationConflict,
        PresentationAssetNotFound,
    ) as error:
        raise _presentation_http_error(error) from error
