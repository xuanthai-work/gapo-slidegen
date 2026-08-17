from uuid import UUID

from sqlalchemy import Delete, Select, Update, delete, func, select, update
from sqlalchemy.orm import Session

from ..jobs.repository import JobRepository, transition
from ..models import AssetRecord, GenerationJob, JobStatus, JobType, PresentationRecord, User
from .outlines import build_owned_outline_query
from ..sources.service import build_owned_source_query


class SourceNotFound(ValueError):
    pass


class JobNotFound(ValueError):
    pass


class JobConflict(ValueError):
    pass


class PresentationNotFound(ValueError):
    pass


class PresentationConflict(ValueError):
    pass


class PresentationAssetNotFound(ValueError):
    pass


def collect_asset_ids(document: dict[str, object]) -> set[UUID]:
    asset_ids: set[UUID] = set()

    def visit(element: object) -> None:
        if not isinstance(element, dict):
            return
        if element.get("type") == "image":
            try:
                asset_ids.add(UUID(str(element.get("assetId"))))
            except ValueError as error:
                raise PresentationAssetNotFound("Presentation contains an invalid image asset id.") from error
        children = element.get("children")
        if isinstance(children, list):
            for child in children:
                visit(child)
        if element.get("child") is not None:
            visit(element["child"])

    slides = document.get("slides")
    if isinstance(slides, list):
        for slide in slides:
            if isinstance(slide, dict) and isinstance(slide.get("elements"), list):
                for element in slide["elements"]:
                    visit(element)
    return asset_ids


def build_update_presentation_statement(
    presentation_id: UUID,
    owner_id: UUID,
    expected_revision: int,
    document: dict[str, object],
) -> Update:
    return (
        update(PresentationRecord)
        .where(
            PresentationRecord.id == presentation_id,
            PresentationRecord.owner_id == owner_id,
            PresentationRecord.revision == expected_revision,
        )
        .values(
            title=str(document["title"]),
            document=document,
            revision=expected_revision + 1,
            updated_at=func.now(),
        )
        .returning(PresentationRecord)
    )


def build_delete_presentation_statement(
    presentation_id: UUID,
    owner_id: UUID,
    expected_revision: int,
) -> Delete:
    return (
        delete(PresentationRecord)
        .where(
            PresentationRecord.id == presentation_id,
            PresentationRecord.owner_id == owner_id,
            PresentationRecord.revision == expected_revision,
        )
        .returning(PresentationRecord.id)
    )


def build_owned_presentations_query(
    owner_id: UUID,
    limit: int = 50,
) -> Select[tuple[PresentationRecord]]:
    return (
        select(PresentationRecord)
        .where(PresentationRecord.owner_id == owner_id)
        .order_by(PresentationRecord.updated_at.desc(), PresentationRecord.id.desc())
        .limit(limit)
    )


class GenerationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def enqueue(
        self,
        *,
        user: User,
        source_id: UUID,
        language: str,
        theme_id: str,
    ) -> GenerationJob:
        source = self.session.scalar(build_owned_source_query(source_id, user.id))
        if source is None:
            raise SourceNotFound("Source not found.")
        return JobRepository(self.session).enqueue(
            owner_id=user.id,
            source_id=source.id,
            job_type=JobType.GENERATE,
            payload={"language": language, "theme_id": theme_id},
        )

    def enqueue_outline(
        self,
        *,
        user: User,
        outline_id: UUID,
        theme_id: str = "modern-blue",
    ) -> GenerationJob:
        outline = self.session.scalar(build_owned_outline_query(outline_id, user.id))
        if outline is None:
            raise SourceNotFound("Outline not found.")
        return JobRepository(self.session).enqueue(
            owner_id=user.id,
            source_id=outline.source_id,
            job_type=JobType.GENERATE,
            payload={
                "outline_id": str(outline.id),
                "outline": outline.items,
                "title": outline.title,
                "slide_count": len(outline.items),
                "language": outline.language,
                "theme_id": theme_id,
            },
        )

    def get_job(self, job_id: UUID, user: User) -> GenerationJob | None:
        return JobRepository(self.session).get_owned(job_id, user.id)

    def list_generation_jobs(self, user: User, limit: int = 20) -> list[GenerationJob]:
        return JobRepository(self.session).list_owned(
            user.id,
            job_type=JobType.GENERATE,
            limit=limit,
        )

    def cancel_job(self, job_id: UUID, user: User) -> GenerationJob:
        job = JobRepository(self.session).get_owned(job_id, user.id)
        if job is None:
            raise JobNotFound("Job not found.")
        if job.status is JobStatus.CANCELED:
            return job
        if job.status not in {JobStatus.QUEUED, JobStatus.RUNNING}:
            raise JobConflict("Only a queued or running job can be canceled.")
        transition(job, JobStatus.CANCELED)
        self.session.flush()
        return job

    def get_presentation(self, presentation_id: UUID, user: User) -> PresentationRecord | None:
        return self.session.scalar(
            select(PresentationRecord).where(
                PresentationRecord.id == presentation_id,
                PresentationRecord.owner_id == user.id,
            )
        )

    def list_presentations(self, user: User, limit: int = 50) -> list[PresentationRecord]:
        return list(self.session.scalars(build_owned_presentations_query(user.id, limit)))

    def update_presentation(
        self,
        *,
        presentation_id: UUID,
        user: User,
        expected_revision: int,
        document: dict[str, object],
    ) -> PresentationRecord:
        asset_ids = collect_asset_ids(document)
        if asset_ids:
            owned_asset_count = self.session.scalar(
                select(func.count())
                .select_from(AssetRecord)
                .where(AssetRecord.owner_id == user.id, AssetRecord.id.in_(asset_ids))
            )
            if owned_asset_count != len(asset_ids):
                raise PresentationAssetNotFound("One or more image assets are unavailable.")
        record = self.session.scalar(
            build_update_presentation_statement(
                presentation_id,
                user.id,
                expected_revision,
                document,
            )
        )
        if record is not None:
            return record
        exists = self.session.scalar(
            select(PresentationRecord.id).where(
                PresentationRecord.id == presentation_id,
                PresentationRecord.owner_id == user.id,
            )
        )
        if exists is None:
            raise PresentationNotFound("Presentation not found.")
        raise PresentationConflict("Presentation changed in another session. Reload before saving again.")

    def rename_presentation(
        self,
        *,
        presentation_id: UUID,
        user: User,
        expected_revision: int,
        title: str,
    ) -> PresentationRecord:
        record = self.get_presentation(presentation_id, user)
        if record is None:
            raise PresentationNotFound("Presentation not found.")
        if record.revision != expected_revision:
            raise PresentationConflict(
                "Presentation changed in another session. Reload before renaming."
            )
        document = dict(record.document)
        document["title"] = title
        renamed = self.session.scalar(
            build_update_presentation_statement(
                presentation_id,
                user.id,
                expected_revision,
                document,
            )
        )
        if renamed is None:
            raise PresentationConflict(
                "Presentation changed in another session. Reload before renaming."
            )
        return renamed

    def delete_presentation(
        self,
        *,
        presentation_id: UUID,
        user: User,
        expected_revision: int,
    ) -> None:
        deleted_id = self.session.scalar(
            build_delete_presentation_statement(
                presentation_id,
                user.id,
                expected_revision,
            )
        )
        if deleted_id is not None:
            return
        exists = self.session.scalar(
            select(PresentationRecord.id).where(
                PresentationRecord.id == presentation_id,
                PresentationRecord.owner_id == user.id,
            )
        )
        if exists is None:
            raise PresentationNotFound("Presentation not found.")
        raise PresentationConflict(
            "Presentation changed in another session. Reload before deleting."
        )
