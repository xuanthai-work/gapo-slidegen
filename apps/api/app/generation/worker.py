from dataclasses import dataclass
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
            outline = StoryOutline.from_dicts(
                claimed.outline or self.pipeline.generate_outline(
                    OutlineRequest(
                        title=claimed.title,
                        text=claimed.text,
                        sections=claimed.sections,
                        language=claimed.language,
                        slide_count=claimed.slide_count,
                        source_kind=claimed.source_kind,
                    )
                )
            )
            asset_plan = self.pipeline.plan_assets(outline, base_request)
            asset_plan.owner_id = claimed.owner_id
            asset_map = self._generate_assets(asset_plan)
            document = self.pipeline.render(base_request, outline, assets=asset_map)
            with self.session_factory() as session:
                job = session.get(GenerationJob, claimed.job_id)
                if job is None or job.status is not JobStatus.RUNNING:
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
            return True
        except Exception as error:
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

    def run_forever(self, poll_seconds: float = 1.0) -> None:
        while True:
            if not self.process_once():
                sleep(poll_seconds)
