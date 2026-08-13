import pytest

from app.auth.service import IdentityService, InactiveUserError, identity_from_claims
from app.models.user import User


def test_identity_is_normalized_from_neon_claims() -> None:
    identity = identity_from_claims(
        {
            "sub": "neon-user-123",
            "email": " Minh.Anh@Example.com ",
            "name": "Minh Anh",
            "roles": ["member", 42],
        }
    )

    assert identity.subject == "neon-user-123"
    assert identity.email == "minh.anh@example.com"
    assert identity.display_name == "Minh Anh"
    assert identity.roles == ["member"]


def test_identity_requires_subject_and_email() -> None:
    with pytest.raises(ValueError):
        identity_from_claims({"email": "minh.anh@example.com"})


def test_inactive_local_user_is_rejected() -> None:
    user = User(
        email="disabled@example.com",
        display_name="Disabled",
        is_active=False,
    )

    with pytest.raises(InactiveUserError):
        IdentityService._require_active(user)
