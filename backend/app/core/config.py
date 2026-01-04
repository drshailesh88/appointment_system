"""
Application configuration using Pydantic Settings.

All settings can be overridden via environment variables.
"""

from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "DocAssist Practice Manager"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # API
    api_v1_prefix: str = "/api/v1"
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Database
    database_url: PostgresDsn = "postgresql+asyncpg://postgres:postgres@localhost:5432/docassist"  # type: ignore
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT Authentication
    jwt_secret_key: str = "change-this-in-production-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # OTP
    otp_expire_minutes: int = 10
    otp_length: int = 6

    # SMS Gateway
    sms_enabled: bool = False
    sms_gateway_url: str | None = None
    sms_gateway_api_key: str | None = None

    # WhatsApp
    whatsapp_enabled: bool = False
    whatsapp_api_url: str | None = None
    whatsapp_api_token: str | None = None

    # Razorpay (UPI Payments)
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None

    # Voice Agent
    voice_enabled: bool = True
    whisper_model: str = "base.en"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"

    # Google Calendar
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None
    calendar_encryption_key: str | None = None

    # EMR Integration
    emr_database_path: str | None = None
    emr_sync_enabled: bool = True
    emr_sync_interval_seconds: int = 300  # 5 minutes

    # Rate Limiting
    rate_limit_per_minute: int = 60

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def async_database_url(self) -> str:
        """Get async database URL."""
        return str(self.database_url)

    @property
    def sync_database_url(self) -> str:
        """Get sync database URL for Alembic."""
        return str(self.database_url).replace("+asyncpg", "+psycopg2")

    @property
    def cors_origins(self) -> list[str]:
        """Get CORS origins."""
        return self.allowed_origins

    @property
    def version(self) -> str:
        """Get app version."""
        return self.app_version


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
