import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.ai.base import ProviderFailure, ProviderFailureKind
from app.ai.factory import get_ai_orchestrator
from app.ai.orchestrator import AIOrchestrator
from app.auth.dependencies import DbSession, get_current_user
from app.schemas.auth import CurrentUser
from app.schemas.presentation import Outline
from app.services.outlines import OutlineQualityError, OutlineService
from app.services.presentations import PresentationNotFoundError, PresentationService

router = APIRouter()
CurrentUserDependency = Annotated[CurrentUser, Depends(get_current_user)]
OrchestratorDependency = Annotated[AIOrchestrator, Depends(get_ai_orchestrator)]


def get_outline_service(
    session: DbSession, orchestrator: OrchestratorDependency
) -> OutlineService:
    return OutlineService(PresentationService(session), orchestrator)


OutlineServiceDependency = Annotated[OutlineService, Depends(get_outline_service)]


@router.post("/{presentation_id}/outline/generate", response_model=Outline)
async def generate_outline(
    presentation_id: uuid.UUID,
    current_user: CurrentUserDependency,
    service: OutlineServiceDependency,
) -> Outline:
    try:
        return await service.generate(presentation_id, current_user.id)
    except PresentationNotFoundError as error:
        raise HTTPException(status_code=404, detail="Presentation not found") from error
    except ProviderFailure as error:
        if error.kind in {
            ProviderFailureKind.AUTHENTICATION,
            ProviderFailureKind.INVALID_REQUEST,
        }:
            status_code = 502
        elif error.kind == ProviderFailureKind.POLICY_REFUSAL:
            status_code = 422
        else:
            status_code = 503
        raise HTTPException(status_code=status_code, detail=str(error)) from error


@router.put("/{presentation_id}/outline", response_model=Outline)
async def update_outline(
    presentation_id: uuid.UUID,
    payload: Outline,
    current_user: CurrentUserDependency,
    service: OutlineServiceDependency,
) -> Outline:
    try:
        return await service.update(presentation_id, current_user.id, payload)
    except PresentationNotFoundError as error:
        raise HTTPException(status_code=404, detail="Presentation not found") from error
    except OutlineQualityError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
