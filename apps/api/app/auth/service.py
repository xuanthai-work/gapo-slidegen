from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import User, UserSession
from .security import (
    create_session_token,
    hash_password,
    hash_session_token,
    normalize_email,
    verify_password,
)

DUMMY_PASSWORD_HASH = hash_password("timing-only-password-placeholder")


class DuplicateEmail(ValueError):
    pass


class InvalidCredentials(ValueError):
    pass


class InvalidPassword(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SessionGrant:
    token: str
    user: User
    expires_at: datetime


class AuthService:
    def __init__(self, session: Session, session_ttl: timedelta) -> None:
        self.session = session
        self.session_ttl = session_ttl

    def register(self, email: str, password: str) -> User:
        normalized = normalize_email(email)
        if not 10 <= len(password) <= 128:
            raise InvalidPassword("Password must contain between 10 and 128 characters.")
        if self.session.scalar(select(User.id).where(User.normalized_email == normalized)):
            raise DuplicateEmail("An account with this email already exists.")
        user = User(email=normalized, normalized_email=normalized, password_hash=hash_password(password))
        self.session.add(user)
        try:
            self.session.flush()
        except IntegrityError as error:
            self.session.rollback()
            raise DuplicateEmail("An account with this email already exists.") from error
        return user

    def login(self, email: str, password: str) -> SessionGrant:
        try:
            normalized = normalize_email(email)
        except ValueError as error:
            raise InvalidCredentials("Invalid email or password.") from error
        user = self.session.scalar(select(User).where(User.normalized_email == normalized))
        encoded = user.password_hash if user and user.is_active else DUMMY_PASSWORD_HASH
        valid, updated_hash = verify_password(password, encoded)
        if user is None or not user.is_active or not valid:
            raise InvalidCredentials("Invalid email or password.")
        if updated_hash:
            user.password_hash = updated_hash
        token = create_session_token()
        expires_at = datetime.now(UTC) + self.session_ttl
        self.session.add(
            UserSession(
                user_id=user.id,
                token_hash=hash_session_token(token),
                expires_at=expires_at,
            )
        )
        self.session.flush()
        return SessionGrant(token=token, user=user, expires_at=expires_at)

    def resolve(self, token: str) -> User | None:
        now = datetime.now(UTC)
        return self.session.scalar(
            select(User)
            .join(UserSession, UserSession.user_id == User.id)
            .where(
                UserSession.token_hash == hash_session_token(token),
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
                User.is_active.is_(True),
            )
        )

    def logout(self, token: str) -> None:
        user_session = self.session.scalar(
            select(UserSession).where(
                UserSession.token_hash == hash_session_token(token),
                UserSession.revoked_at.is_(None),
            )
        )
        if user_session:
            user_session.revoked_at = datetime.now(UTC)
            self.session.flush()
