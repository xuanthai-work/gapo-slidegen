from dataclasses import dataclass
from time import sleep
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from ..jobs.repository import JobRepository
from ..models import GenerationJob, JobStatus, JobType, PresentationRecord, SourceRecord
from .provider import GenerationRequest, PresentationProvider


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
    slide_count: int
    language: str
    source_kind: str
    theme_id: str


class GenerationWorker:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        provider: PresentationProvider,
    ) -> None:
        self.session_factory = session_factory
        self.provider = provider

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
            claimed = ClaimedGeneration(
                job_id=job.id,
                owner_id=job.owner_id,
                source_id=source.id if source else None,
                outline_id=UUID(str(job.payload["outline_id"])) if job.payload.get("outline_id") else None,
                title=str(job.payload.get("title") or (source.title if source else "Untitled presentation")),
                text=source.extracted_text if source else " ".join(str(item.get("content", "")) for item in outline if isinstance(item, dict)),
                sections=source.sections if source else [],
                outline=outline if isinstance(outline, list) else [],
                slide_count=int(job.payload.get("slide_count", 10)),
                language=str(job.payload.get("language", "en")),
                source_kind=source.kind if source else "outline",
                theme_id=str(job.payload.get("theme_id", "editorial-cobalt")),
            )
            session.commit()
            return claimed

    def process_once(self) -> bool:
        claimed = self._claim()
        if claimed is None:
            return False

        presentation_id = uuid4()
        try:
            document = self.provider.generate(
                GenerationRequest(
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
            )
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
                    {"presentation_id": str(presentation_id), "provider": self.provider.name},
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
