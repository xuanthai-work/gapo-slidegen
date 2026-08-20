from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
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
    retention_cleanup_interval_seconds: int = Field(default=300, ge=10, le=24 * 60 * 60)
    retention_cleanup_batch_size: int = Field(default=100, ge=1, le=1_000)
    generation_streaming_enabled: bool = False
    redis_url: SecretStr = SecretStr("")
    generation_event_channel_prefix: str = "slidegen:generation"
    generation_provider: str = "stub"
    image_provider: str = "disabled"
    google_api_key: SecretStr | None = None
    google_model: str | None = None
    google_image_model: str | None = None
    google_max_input_chars: int = Field(default=120_000, ge=1_000, le=2_000_000)
    company_gateway_url: str | None = None
    company_gateway_api_key: SecretStr | None = None
    company_gateway_model: str | None = None
    company_gateway_chat_path: str = "/v1/chat/completions"
    visual_gate_enabled: bool = False
    visual_gate_model: str | None = None
    visual_gate_max_repairs: int = Field(default=2, ge=0, le=4)
    visual_gate_rasterizer_cmd: str = "node packages/slide-rasterizer/dist/cli.js"
    visual_gate_save_screenshots: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
