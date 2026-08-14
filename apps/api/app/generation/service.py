from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..jobs.repository import JobRepository
from ..models import GenerationJob, JobType, PresentationRecord, User
from ..sources.service import build_owned_source_query


class SourceNotFound(ValueError):
    pass


class GenerationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def enqueue(
        self,
        *,
        user: User,
        source_id: UUID,
        slide_count: int,
        language: str,
    ) -> GenerationJob:
        source = self.session.scalar(build_owned_source_query(source_id, user.id))
        if source is None:
            raise SourceNotFound("Source not found.")
        return JobRepository(self.session).enqueue(
            owner_id=user.id,
            source_id=source.id,
            job_type=JobType.GENERATE,
            payload={"slide_count": slide_count, "language": language},
        )

    def get_job(self, job_id: UUID, user: User) -> GenerationJob | None:
        return JobRepository(self.session).get_owned(job_id, user.id)

    def get_presentation(self, presentation_id: UUID, user: User) -> PresentationRecord | None:
        return self.session.scalar(
            select(PresentationRecord).where(
                PresentationRecord.id == presentation_id,
                PresentationRecord.owner_id == user.id,
            )
        )
