from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None,
        env_prefix="SLIDEGEN_",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str = "postgresql+psycopg://slidegen:slidegen@localhost:5432/slidegen"
    storage_root: Path = Path(".data/storage")
    max_upload_bytes: int = Field(default=25 * 1024 * 1024, ge=1)
    generation_concurrency: int = Field(default=2, ge=1, le=16)
    session_ttl_hours: int = Field(default=168, ge=1, le=24 * 90)
    source_retention_hours: int = Field(default=24, ge=1, le=24 * 365)
    generation_provider: str = "stub"


@lru_cache
def get_settings() -> Settings:
    return Settings()
