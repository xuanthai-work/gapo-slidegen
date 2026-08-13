import uuid

from app.ai.base import AIProvider, ProviderFailure, ProviderFailureKind
from app.ai.orchestrator import AIOrchestrator
from app.models.presentation import PresentationStatus
from app.schemas.presentation import Outline
from app.services.presentations import PresentationService


class OutlineQualityError(Exception):
    pass


class OutlineService:
    def __init__(
        self,
        presentations: PresentationService,
        orchestrator: AIOrchestrator,
    ) -> None:
        self.presentations = presentations
        self.orchestrator = orchestrator

    async def generate(self, presentation_id: uuid.UUID, owner_id: uuid.UUID) -> Outline:
        presentation = await self.presentations.require_owned(presentation_id, owner_id)
        await self.presentations.set_status(presentation, PresentationStatus.OUTLINING)

        async def operation(provider: AIProvider) -> Outline:
            outline = await provider.generate_outline(
                prompt=presentation.prompt,
                language=presentation.language,
                slide_count=presentation.slide_count,
            )
            try:
                validate_outline(outline, presentation.slide_count)
            except OutlineQualityError as error:
                raise ProviderFailure(
                    ProviderFailureKind.INVALID_RESPONSE, str(error)
                ) from error
            return outline

        try:
            outline = await self.orchestrator.run_with_failover(
                operation,
                request_id=str(uuid.uuid4()),
                job_id=str(presentation.id),
            )
        except Exception:
            await self.presentations.set_status(presentation, PresentationStatus.FAILED)
            raise

        await self.presentations.save_outline(presentation, outline)
        return outline

    async def update(
        self, presentation_id: uuid.UUID, owner_id: uuid.UUID, outline: Outline
    ) -> Outline:
        presentation = await self.presentations.require_owned(presentation_id, owner_id)
        validate_outline(outline, presentation.slide_count)
        await self.presentations.save_outline(presentation, outline)
        return outline


def validate_outline(outline: Outline, expected_slide_count: int) -> None:
    if len(outline.slides) != expected_slide_count:
        raise OutlineQualityError(
            f"Outline must contain exactly {expected_slide_count} slides"
        )
    ids = [slide.id.casefold() for slide in outline.slides]
    titles = [slide.title.strip().casefold() for slide in outline.slides]
    if len(ids) != len(set(ids)):
        raise OutlineQualityError("Slide IDs must be unique")
    if len(titles) != len(set(titles)):
        raise OutlineQualityError("Slide titles must be unique")
