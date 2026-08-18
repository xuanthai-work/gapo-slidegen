import logging
from dataclasses import dataclass, replace
from time import sleep
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from ..config import get_settings
from ..jobs.repository import JobRepository
from ..models import GenerationJob, JobStatus, JobType, PresentationRecord, SourceRecord
from ..storage.local import LocalObjectStorage
from .factory import build_image_provider
from .provider import GenerationRequest, OutlineRequest, ProviderConfigurationError
from .stages.asset_generator import ImageAssetGenerator
from .stages.models import StoryOutline
from .stages.orchestrator import GenerationPipeline


class _StreamTracker:
    """Updates a running job's progress and streaming preview data."""

    def __init__(self, session_factory: sessionmaker[Session], job_id: UUID, language: str) -> None:
        self._session_factory = session_factory
        self._job_id = job_id
        self._language = language

    def _update(self, *, progress: int, stage: str, message: str, slides: list[dict[str, object]] | None = None) -> None:
        with self._session_factory() as session:
            job = session.get(GenerationJob, self._job_id)
            if job is not None and job.status is JobStatus.RUNNING:
                repo = JobRepository(session)
                repo.update_progress(job, progress)
                repo.update_stream(job, stage=stage, message=message, slides=slides)
                session.commit()

    def set(self, progress: int, *, stage: str, message: str | None = None) -> None:
        self._update(
            progress=progress,
            stage=stage,
            message=message or self._default_message(progress, stage),
        )

    def slide(self, progress: int, slide_index: int, slide: dict[str, object]) -> None:
        # Keep existing slides so the dashboard can render them incrementally.
        logger.info("[stream] updating slide %d for job %s", slide_index, self._job_id)
        with self._session_factory() as session:
            job = session.get(GenerationJob, self._job_id)
            if job is None:
                logger.warning("[stream] job %s not found", self._job_id)
                return
            if job.status is not JobStatus.RUNNING:
                logger.warning("[stream] job %s not running: %s", self._job_id, job.status)
                return
            repo = JobRepository(session)
            repo.update_progress(job, progress)
            slides = (job.stream_data or {}).get("slides", []) if job.stream_data else []
            slides = list(slides)
            # Extend or replace the slide at the current index.
            if len(slides) <= slide_index:
                slides.extend([{}] * (slide_index - len(slides) + 1))
            slides[slide_index] = slide
            repo.update_stream(
                job,
                stage="rendering",
                message=f"Building slide {slide_index + 1}...",
                slides=slides,
            )
            session.commit()
            logger.info("[stream] slide %d saved for job %s", slide_index, self._job_id)

    def _default_message(self, progress: int, stage: str) -> str:
        messages: dict[str, dict[str, str]] = {
            "analyzing": {"en": "Analyzing the source...", "vi": "Đang phân tích nguồn..."},
            "planning": {"en": "Planning the story...", "vi": "Đang lập dàn ý..."},
            "outlining": {"en": "Outlining slides...", "vi": "Đang tạo slide..."},
            "rendering": {"en": "Rendering slides...", "vi": "Đang render slide..."},
            "finalizing": {"en": "Finalizing presentation...", "vi": "Đang hoàn thiện bài thuyết trình..."},
        }
        return messages.get(stage, {}).get(self._language, messages.get(stage, {}).get("en", "Working..."))

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ClaimedGeneration:
    job_id: UUID
    owner_id: UUID
    source_id: UUID | None
    outline_id: UUID | None
    title: str
    text: str
    sections: list[dict[str, object]]
    outline: list[dict[str, object]]
    slide_count: int | None
    language: str
    source_kind: str
    theme_id: str


class GenerationWorker:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        pipeline: GenerationPipeline,
    ) -> None:
        self.session_factory = session_factory
        self.pipeline = pipeline

    def _claim(self) -> ClaimedGeneration | None:
        with self.session_factory() as session:
            job = JobRepository(session).claim_next(JobType.GENERATE)
            if job is None:
                session.commit()
                return None
            source = session.get(SourceRecord, job.source_id) if job.source_id else None
            outline = job.payload.get("outline")
            has_outline = isinstance(outline, list) and bool(outline)
            if (source is None or source.owner_id != job.owner_id) and not has_outline:
                JobRepository(session).fail(
                    job,
                    code="source_not_found",
                    message="The source was deleted or does not belong to the job owner.",
                )
                session.commit()
                return None
            requested_slide_count = job.payload.get("slide_count")
            claimed = ClaimedGeneration(
                job_id=job.id,
                owner_id=job.owner_id,
                source_id=source.id if source else None,
                outline_id=UUID(str(job.payload["outline_id"])) if job.payload.get("outline_id") else None,
                title=str(job.payload.get("title") or (source.title if source else "Untitled presentation")),
                text=source.extracted_text if source else " ".join(str(item.get("content", "")) for item in outline if isinstance(item, dict)),
                sections=source.sections if source else [],
                outline=outline if isinstance(outline, list) else [],
                slide_count=(
                    int(requested_slide_count)
                    if requested_slide_count is not None
                    else None
                ),
                language=str(job.payload.get("language", "en")),
                source_kind=source.kind if source else "outline",
                theme_id=str(job.payload.get("theme_id", "modern-blue")),
            )
            session.commit()
            return claimed

    def _generate_assets(self, asset_plan) -> dict[tuple[int, str], str]:
        if not asset_plan.requests:
            return {}
        try:
            image_provider = build_image_provider()
        except ProviderConfigurationError:
            return {}
        generator = ImageAssetGenerator(
            image_provider=image_provider,
            session_factory=self.session_factory,
            storage=LocalObjectStorage(get_settings().storage_root),
        )
        generated = generator.generate(asset_plan)
        return {
            (asset.slot.slide_index, asset.slot.name): asset.asset_id
            for asset in generated
            if asset.asset_id is not None
        }

    def process_once(self) -> bool:
        claimed = self._claim()
        if claimed is None:
            return False

        logger.info("[worker] claimed job %s", claimed.job_id)
        tracker = _StreamTracker(self.session_factory, claimed.job_id, claimed.language)
        tracker.set(10, stage="analyzing")
        presentation_id = uuid4()
        base_request = GenerationRequest(
            presentation_id=presentation_id,
            title=claimed.title,
            text=claimed.text,
            sections=claimed.sections,
            outline=claimed.outline,
            language=claimed.language,
            slide_count=claimed.slide_count,
            source_kind=claimed.source_kind,
            theme_id=claimed.theme_id,
        )
        try:
            logger.info("[worker] generating outline for job %s", claimed.job_id)
            outline_items = claimed.outline
            if not outline_items:
                tracker.set(15, stage="planning")
                outline_items = self.pipeline.generate_outline(
                    OutlineRequest(
                        title=claimed.title,
                        text=claimed.text,
                        sections=claimed.sections,
                        language=claimed.language,
                        slide_count=claimed.slide_count,
                        source_kind=claimed.source_kind,
                    )
                )
            outline = StoryOutline.from_dicts(outline_items)
            tracker.set(40, stage="outlining", message=f"Outline ready: {len(outline.items)} slides")
            logger.info("[worker] outline ready for job %s (%d slides)", claimed.job_id, len(outline.items))
            asset_plan = self.pipeline.plan_assets(outline, base_request)
            asset_plan = replace(asset_plan, owner_id=claimed.owner_id)
            tracker.set(50, stage="rendering")
            asset_map = self._generate_assets(asset_plan)
            tracker.set(60, stage="rendering")
            logger.info("[worker] rendering for job %s", claimed.job_id)
            document = self._render_slide_by_slide(base_request, outline, assets=asset_map, tracker=tracker)
            tracker.set(95, stage="finalizing")
            logger.info("[worker] render complete for job %s", claimed.job_id)
            with self.session_factory() as session:
                job = session.get(GenerationJob, claimed.job_id)
                if job is None or job.status is not JobStatus.RUNNING:
                    logger.warning("[worker] job %s is gone or not running", claimed.job_id)
                    return False
                session.add(
                    PresentationRecord(
                        id=presentation_id,
                        owner_id=claimed.owner_id,
                        source_id=claimed.source_id,
                        outline_id=claimed.outline_id,
                        title=claimed.title,
                        document=document,
                        revision=0,
                    )
                )
                JobRepository(session).succeed(
                    job,
                    {"presentation_id": str(presentation_id), "provider": self.pipeline.name},
                )
                session.commit()
                logger.info("[worker] job %s succeeded", claimed.job_id)
            return True
        except Exception as error:
            logger.exception("[worker] job %s failed", claimed.job_id)
            with self.session_factory() as session:
                job = session.get(GenerationJob, claimed.job_id)
                if job is not None and job.status is JobStatus.RUNNING:
                    JobRepository(session).fail(
                        job,
                        code="generation_failed",
                        message=str(error)[:2_000],
                    )
                    session.commit()
            return True

    def _render_slide_by_slide(
        self,
        request: GenerationRequest,
        outline: StoryOutline,
        *,
        assets: dict[tuple[int, str], str],
        tracker: _StreamTracker,
    ) -> dict[str, object]:
        """Render the presentation one slide at a time, emitting stream events."""
        slides = self.pipeline.content_generator.render_slides(request, outline, assets=assets)
        total = len(slides)
        theme: dict[str, object] | None = None
        streamed_slides: list[dict[str, object]] = []
        for index, slide in enumerate(slides):
            streamed_slides.append(slide)
            if theme is None:
                # Pull theme from the first compiled slide if available; otherwise
                # look it up directly. Native/Presenton generators both include theme
                # in the final document, but per-slide preview only needs colors.
                theme = slide.get("theme") if isinstance(slide.get("theme"), dict) else None  # type: ignore[arg-type]
            progress = 60 + int((index + 1) / max(total, 1) * 30)
            tracker.slide(progress, index, slide)
            # Delay so the dashboard can show each slide appearing one by one.
            sleep(0.8)
        document: dict[str, object] = {
            "id": str(request.presentation_id),
            "schemaVersion": 1,
            "title": request.title,
            "language": request.language,
            "revision": 0,
            "slides": streamed_slides,
        }
        if theme is not None:
            document["theme"] = theme
        else:
            from .themes import get_theme

            document["theme"] = get_theme(request.theme_id)
        return document

    def run_forever(self, poll_seconds: float = 1.0) -> None:
        while True:
            if not self.process_once():
                sleep(poll_seconds)
