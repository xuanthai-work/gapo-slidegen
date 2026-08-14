from datetime import timedelta
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_session
from ..models import User
from .service import AuthService

SESSION_COOKIE = "slidegen_session"


def get_auth_service(session: Annotated[Session, Depends(get_session)]) -> AuthService:
    return AuthService(session, timedelta(hours=get_settings().session_ttl_hours))


def get_current_user(
    service: Annotated[AuthService, Depends(get_auth_service)],
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User:
    user = service.resolve(token) if token else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return user
