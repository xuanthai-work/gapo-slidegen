import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.auth.dependencies import DbSession, get_current_user
from app.schemas.auth import CurrentUser
from app.schemas.presentation import (
    PresentationCreate,
    PresentationDetail,
    PresentationSummary,
    PresentationUpdate,
)
from app.services.presentations import (
    PresentationConflictError,
    PresentationNotFoundError,
    PresentationService,
)

router = APIRouter()
CurrentUserDependency = Annotated[CurrentUser, Depends(get_current_user)]


def get_presentation_service(session: DbSession) -> PresentationService:
    return PresentationService(session)


PresentationServiceDependency = Annotated[
    PresentationService, Depends(get_presentation_service)
]


def not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Presentation not found")


@router.get("", response_model=list[PresentationSummary])
async def list_presentations(
    current_user: CurrentUserDependency,
    service: PresentationServiceDependency,
) -> list[PresentationSummary]:
    return [
        PresentationSummary.model_validate(item)
        for item in await service.list_owned(current_user.id)
    ]


@router.post("", response_model=PresentationDetail, status_code=status.HTTP_201_CREATED)
async def create_presentation(
    payload: PresentationCreate,
    current_user: CurrentUserDependency,
    service: PresentationServiceDependency,
) -> PresentationDetail:
    return PresentationDetail.model_validate(await service.create(current_user.id, payload))


@router.get("/{presentation_id}", response_model=PresentationDetail)
async def get_presentation(
    presentation_id: uuid.UUID,
    current_user: CurrentUserDependency,
    service: PresentationServiceDependency,
) -> PresentationDetail:
    try:
        item = await service.require_owned(presentation_id, current_user.id)
    except PresentationNotFoundError as error:
        raise not_found() from error
    return PresentationDetail.model_validate(item)


@router.patch("/{presentation_id}", response_model=PresentationDetail)
async def update_presentation(
    presentation_id: uuid.UUID,
    payload: PresentationUpdate,
    current_user: CurrentUserDependency,
    service: PresentationServiceDependency,
) -> PresentationDetail:
    try:
        item = await service.update(presentation_id, current_user.id, payload)
    except PresentationNotFoundError as error:
        raise not_found() from error
    except PresentationConflictError as error:
        raise HTTPException(status_code=409, detail="Presentation was updated elsewhere") from error
    return PresentationDetail.model_validate(item)


@router.delete("/{presentation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_presentation(
    presentation_id: uuid.UUID,
    current_user: CurrentUserDependency,
    service: PresentationServiceDependency,
) -> Response:
    try:
        await service.delete(presentation_id, current_user.id)
    except PresentationNotFoundError as error:
        raise not_found() from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
