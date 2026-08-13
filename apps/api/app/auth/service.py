from dataclasses import dataclass
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_identity import UserIdentity

NEON_IDENTITY_PROVIDER = "neon"


class InactiveUserError(Exception):
    pass


@dataclass(frozen=True)
class VerifiedIdentity:
    subject: str
    email: str
    display_name: str | None
    roles: list[str]


class IdentityService:
    """Maps a verified Neon identity to the app's provider-neutral user."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _find_by_subject(self, subject: str) -> User | None:
        statement = (
            select(User)
            .join(UserIdentity, UserIdentity.user_id == User.id)
            .where(
                UserIdentity.provider == NEON_IDENTITY_PROVIDER,
                UserIdentity.subject == subject,
            )
        )
        return cast(User | None, await self.session.scalar(statement))

    @staticmethod
    def _require_active(user: User) -> User:
        if not user.is_active:
            raise InactiveUserError
        return user

    async def resolve(self, identity: VerifiedIdentity) -> User:
        user = await self._find_by_subject(identity.subject)
        if user is not None:
            self._require_active(user)
            changed = False
            if user.email != identity.email:
                user.email = identity.email
                changed = True
            if identity.display_name and user.display_name != identity.display_name:
                user.display_name = identity.display_name
                changed = True
            if changed:
                await self.session.commit()
            return user

        # Reuse a legacy local profile with the same verified email, if one exists.
        user = cast(
            User | None,
            await self.session.scalar(select(User).where(User.email == identity.email)),
        )
        if user is None:
            user = User(
                email=identity.email,
                display_name=identity.display_name,
            )
            self.session.add(user)
            await self.session.flush()
        else:
            self._require_active(user)

        self.session.add(
            UserIdentity(
                provider=NEON_IDENTITY_PROVIDER,
                subject=identity.subject,
                user_id=user.id,
            )
        )
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            concurrent_user = await self._find_by_subject(identity.subject)
            if concurrent_user is None:
                raise
            return self._require_active(concurrent_user)
        await self.session.refresh(user)
        return user


def identity_from_claims(claims: dict[str, Any]) -> VerifiedIdentity:
    subject = claims.get("sub")
    email = claims.get("email")
    if not isinstance(subject, str) or not subject:
        raise ValueError("Token is missing subject")
    if not isinstance(email, str) or not email:
        raise ValueError("Token is missing email")

    name = claims.get("name")
    raw_roles = claims.get("roles", claims.get("role", []))
    if isinstance(raw_roles, str):
        roles = [raw_roles]
    elif isinstance(raw_roles, list):
        roles = [role for role in raw_roles if isinstance(role, str)]
    else:
        roles = []

    return VerifiedIdentity(
        subject=subject,
        email=email.strip().casefold(),
        display_name=name if isinstance(name, str) and name.strip() else None,
        roles=roles,
    )
