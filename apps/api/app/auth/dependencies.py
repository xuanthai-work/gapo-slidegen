from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.neon import (
    InvalidNeonTokenError,
    NeonAuthNotConfiguredError,
    NeonTokenVerifier,
    get_neon_token_verifier,
)
from app.auth.service import (
    IdentityService,
    InactiveUserError,
    VerifiedIdentity,
    identity_from_claims,
)
from app.db.session import get_db_session
from app.schemas.auth import CurrentUser

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(HTTPBearer(auto_error=False)),
]
TokenVerifier = Annotated[NeonTokenVerifier, Depends(get_neon_token_verifier)]


async def get_verified_identity(
    credentials: BearerCredentials,
    verifier: TokenVerifier,
) -> VerifiedIdentity:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        claims = await run_in_threadpool(verifier.verify, credentials.credentials)
        return identity_from_claims(claims)
    except NeonAuthNotConfiguredError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neon Auth JWKS is not configured",
        ) from error
    except (InvalidNeonTokenError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from error


VerifiedIdentityDependency = Annotated[VerifiedIdentity, Depends(get_verified_identity)]


async def get_current_user(
    identity: VerifiedIdentityDependency,
    session: DbSession,
) -> CurrentUser:
    try:
        user = await IdentityService(session).resolve(identity)
    except InactiveUserError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        ) from error
    return CurrentUser(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        roles=identity.roles,
    )
