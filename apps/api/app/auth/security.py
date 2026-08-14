from hashlib import sha256
from secrets import token_urlsafe

from email_validator import EmailNotValidError, validate_email
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

password_hash = PasswordHash.recommended()


class InvalidEmail(ValueError):
    pass


def normalize_email(value: str) -> str:
    try:
        result = validate_email(value.strip(), check_deliverability=False)
    except EmailNotValidError as error:
        raise InvalidEmail(str(error)) from error
    return result.normalized.lower()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> tuple[bool, str | None]:
    try:
        return password_hash.verify_and_update(password, encoded)
    except UnknownHashError:
        return False, None


def create_session_token() -> str:
    return token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()
