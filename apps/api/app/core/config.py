from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_ENV: Literal["development", "test", "production"] = "development"
    SQL_ECHO: bool = False
    WEB_ORIGIN: AnyHttpUrl = AnyHttpUrl("http://localhost:3000")
    NEON_AUTH_JWKS_URL: AnyHttpUrl | None = None
    NEON_AUTH_ISSUER: str | None = None
    NEON_AUTH_AUDIENCE: str | None = None

    DATABASE_URL: str = "postgresql+asyncpg://gapo:gapo@localhost:5432/gapo_slidegen"

    AI_PRIMARY_PROVIDER: Literal["google", "openai"] = "google"
    GOOGLE_API_KEY: SecretStr | None = None
    GOOGLE_MODEL: str = "gemini-2.5-flash"
    OPENAI_API_KEY: SecretStr | None = None
    OPENAI_FALLBACK_MODEL: str = "gpt-4.1"
    OPENAI_FALLBACK_2_MODEL: str = "gpt-4.1-mini"

    # Persistent vectors must use one stable embedding space. Switching this
    # value requires re-embedding all stored document chunks.
    EMBEDDING_PROVIDER: Literal["google", "openai"] = "google"
    GOOGLE_EMBEDDING_MODEL: str = "gemini-embedding-2"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = Field(default=768, ge=128, le=3072)

    # OCR/vision extraction follows the existing Google -> OpenAI -> OpenAI
    # provider chain and uses the configured generation models above.
    OCR_PROVIDER: Literal["ai"] = "ai"
    OCR_LANGUAGES: str = "vie+eng"

    AI_REQUEST_TIMEOUT_SECONDS: int = Field(default=60, ge=1, le=300)
    AI_MAX_RETRIES_PER_PROVIDER: int = Field(default=1, ge=0, le=3)
    MAX_SLIDES_PER_PRESENTATION: int = Field(default=10, ge=1, le=30)

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        if value is None or not isinstance(value, str):
            return value

        normalized = value.strip().strip('"').strip("'")
        if normalized.startswith("postgresql://"):
            normalized = normalized.replace("postgresql://", "postgresql+asyncpg://", 1)

        parts = urlsplit(normalized)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        if "sslmode" in query and "ssl" not in query:
            query["ssl"] = query.pop("sslmode")
        # asyncpg does not accept libpq's channel_binding connection argument.
        query.pop("channel_binding", None)
        return urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
        )

    @field_validator(
        "NEON_AUTH_JWKS_URL",
        "NEON_AUTH_ISSUER",
        "NEON_AUTH_AUDIENCE",
        mode="before",
    )
    @classmethod
    def empty_auth_config_is_none(cls, value: object) -> object:
        return None if value == "" else value

@lru_cache
def get_settings() -> Settings:
    return Settings()
