from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.schemas.auth import CurrentUser

router = APIRouter()
CurrentUserDependency = Annotated[CurrentUser, Depends(get_current_user)]


@router.get("/me", response_model=CurrentUser)
async def me(current_user: CurrentUserDependency) -> CurrentUser:
    return current_user
