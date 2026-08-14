from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field

from ..config import get_settings
from ..models import User
from .dependencies import SESSION_COOKIE, get_auth_service, get_current_user
from .security import InvalidEmail
from .service import AuthService, DuplicateEmail, InvalidCredentials, InvalidPassword

router = APIRouter(prefix="/v1/auth", tags=["auth"])


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class UserView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=settings.session_ttl_hours * 60 * 60,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        path="/",
    )


@router.post("/register", response_model=UserView, status_code=status.HTTP_201_CREATED)
def register(
    payload: Credentials,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    try:
        return service.register(payload.email, payload.password)
    except (DuplicateEmail, InvalidEmail, InvalidPassword) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


@router.post("/login", response_model=UserView)
def login(
    payload: Credentials,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    try:
        grant = service.login(payload.email, payload.password)
    except InvalidCredentials as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error
    _set_session_cookie(response, grant.token)
    return grant.user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> None:
    if token:
        service.logout(token)
    response.delete_cookie(SESSION_COOKIE, path="/", samesite="lax")


@router.get("/me", response_model=UserView)
def me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user
