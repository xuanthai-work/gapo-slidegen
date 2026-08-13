import uuid
from datetime import datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.presentation import Presentation, PresentationStatus
from app.schemas.presentation import Outline, PresentationCreate, PresentationUpdate


class PresentationNotFoundError(Exception):
    pass


class PresentationConflictError(Exception):
    pass


class PresentationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_owned(self, owner_id: uuid.UUID) -> list[Presentation]:
        statement = (
            select(Presentation)
            .where(Presentation.owner_id == owner_id)
            .order_by(Presentation.updated_at.desc())
        )
        return list((await self.session.scalars(statement)).all())

    async def create(
        self, owner_id: uuid.UUID, payload: PresentationCreate
    ) -> Presentation:
        title = payload.prompt.strip().splitlines()[0][:240]
        presentation = Presentation(
            owner_id=owner_id,
            title=title,
            prompt=payload.prompt.strip(),
            language=payload.language,
            slide_count=payload.slide_count,
            theme_key=payload.theme_key,
            status=PresentationStatus.DRAFT,
        )
        self.session.add(presentation)
        await self.session.commit()
        await self.session.refresh(presentation)
        return presentation

    async def get_owned(
        self,
        presentation_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> Presentation | None:
        statement = select(Presentation).where(
            Presentation.id == presentation_id,
            Presentation.owner_id == owner_id,
        )
        return cast(Presentation | None, await self.session.scalar(statement))

    async def require_owned(
        self, presentation_id: uuid.UUID, owner_id: uuid.UUID
    ) -> Presentation:
        presentation = await self.get_owned(presentation_id, owner_id)
        if presentation is None:
            raise PresentationNotFoundError
        return presentation

    async def update(
        self,
        presentation_id: uuid.UUID,
        owner_id: uuid.UUID,
        payload: PresentationUpdate,
    ) -> Presentation:
        presentation = await self.require_owned(presentation_id, owner_id)
        self._check_version(presentation, payload.updated_at)
        changes = payload.model_dump(exclude_unset=True, exclude={"updated_at"})
        for field, value in changes.items():
            setattr(presentation, field, value)
        await self.session.commit()
        await self.session.refresh(presentation)
        return presentation

    async def delete(self, presentation_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        presentation = await self.require_owned(presentation_id, owner_id)
        await self.session.delete(presentation)
        await self.session.commit()

    async def set_status(
        self, presentation: Presentation, status: PresentationStatus
    ) -> None:
        presentation.status = status
        await self.session.commit()

    async def save_outline(
        self,
        presentation: Presentation,
        outline: Outline,
    ) -> Presentation:
        presentation.title = outline.title
        presentation.outline = outline.model_dump(mode="json")
        presentation.status = PresentationStatus.DRAFT
        await self.session.commit()
        await self.session.refresh(presentation)
        return presentation

    @staticmethod
    def _check_version(
        presentation: Presentation, expected_updated_at: datetime | None
    ) -> None:
        if expected_updated_at is None:
            return
        if presentation.updated_at != expected_updated_at:
            raise PresentationConflictError
