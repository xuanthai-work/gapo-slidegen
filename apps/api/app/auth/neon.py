from functools import lru_cache
from typing import Any

import jwt
from jwt.types import Options

from app.core.config import Settings, get_settings


class InvalidNeonTokenError(Exception):
    pass


class NeonAuthNotConfiguredError(Exception):
    pass


class NeonTokenVerifier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._jwks_client: jwt.PyJWKClient | None = None

    def verify(self, token: str) -> dict[str, Any]:
        if self.settings.NEON_AUTH_JWKS_URL is None:
            raise NeonAuthNotConfiguredError

        if self._jwks_client is None:
            self._jwks_client = jwt.PyJWKClient(
                str(self.settings.NEON_AUTH_JWKS_URL),
                cache_jwk_set=True,
                cache_keys=True,
                timeout=10,
            )

        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            decode_options: Options = {
                "verify_aud": self.settings.NEON_AUTH_AUDIENCE is not None,
                "verify_iss": self.settings.NEON_AUTH_ISSUER is not None,
            }
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256", "EdDSA"],
                audience=self.settings.NEON_AUTH_AUDIENCE,
                issuer=self.settings.NEON_AUTH_ISSUER,
                options=decode_options,
            )
        except (jwt.PyJWTError, ValueError) as error:
            raise InvalidNeonTokenError from error

        return dict(claims)


@lru_cache
def get_neon_token_verifier() -> NeonTokenVerifier:
    return NeonTokenVerifier(get_settings())
