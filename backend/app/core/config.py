"""
Application configuration using Pydantic Settings.

All settings can be overridden via environment variables.
"""

from functools import lru_cache
from typing import Literal
import os
import warnings

from pydantic import PostgresDsn, field_validator, model_validator
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
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/docassist"
    database_pool_size: int = 5
    database_max_overflow: int = 10

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL - allow SQLite in testing mode."""
        if not v:
            raise ValueError("Database URL cannot be empty")

        # Allow SQLite URLs in testing mode
        if os.environ.get("TESTING") == "1":
            if v.startswith(("sqlite", "postgresql")):
                return v
            raise ValueError(f"Invalid database URL for testing: {v}")

        # In production/development, enforce PostgreSQL
        if not v.startswith("postgresql"):
            raise ValueError(
                f"Database URL must start with 'postgresql', got: {v[:20]}..."
            )

        return v

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

    # SMS Configuration (MSG91)
    sms_enabled: bool = False
    msg91_auth_key: str = ""
    msg91_sender_id: str = "DOCAST"  # 6 char sender ID (DLT registered)
    msg91_route: str = "4"  # Route 4 = Transactional
    msg91_country: str = "91"  # India country code
    msg91_dlt_te_id: str = ""  # DLT Template Entity ID

    # Legacy SMS fields (deprecated, use MSG91 fields above)
    sms_gateway_url: str | None = None
    sms_gateway_api_key: str | None = None

    # For backward compatibility with existing code
    @property
    def sms_api_key(self) -> str:
        """Get SMS API key (MSG91 auth key)."""
        return self.msg91_auth_key

    @property
    def sms_sender_id(self) -> str:
        """Get SMS sender ID."""
        return self.msg91_sender_id

    # WhatsApp
    whatsapp_enabled: bool = False
    whatsapp_api_url: str | None = None
    whatsapp_api_token: str | None = None
    whatsapp_verify_token: str | None = None  # For webhook verification
    whatsapp_webhook_secret: str | None = None  # Optional additional security

    # Razorpay (UPI Payments)
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_webhook_secret: str | None = None

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

    # Twilio / Voice Bot
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_phone_number: str | None = None  # Your Twilio number (E.164 format)
    twilio_webhook_url: str | None = None  # Public URL for webhooks

    # Voice Bot Settings
    voice_bot_enabled: bool = False
    voice_bot_default_language: str = "hi"  # Hindi default
    voice_bot_supported_languages: list[str] = [
        "hi",  # Hindi
        "en",  # English
        "ta",  # Tamil
        "te",  # Telugu
        "bn",  # Bengali
        "mr",  # Marathi
        "gu",  # Gujarati
    ]
    voice_bot_max_call_duration_minutes: int = 10
    voice_bot_silence_timeout_seconds: int = 5

    # Jitsi/Telemedicine
    jitsi_domain: str = "meet.jit.si"  # Default to public Jitsi, should be self-hosted
    jitsi_app_id: str = "docassist_telemedicine"
    jitsi_jwt_secret: str | None = None  # Required for JWT authentication
    jitsi_recording_enabled: bool = False
    consultation_max_duration_minutes: int = 60
    waiting_room_timeout_minutes: int = 30

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # Scheduler
    scheduler_enabled: bool = True
    scheduler_timezone: str = "Asia/Kolkata"
    calendar_sync_interval_minutes: int = 5
    digest_send_hour: int = 6
    digest_send_minute: int = 0
    emr_sync_interval_minutes: int = 5
    reminder_check_interval_minutes: int = 60
    insurance_check_interval_hours: int = 6

    # Testing flag
    testing: bool = False

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        """Validate security-critical settings."""
        # Check JWT secret in production
        default_jwt_secrets = [
            "change-this-in-production-use-openssl-rand-hex-32",
            "dev-secret-key-change-in-production",
        ]

        if self.environment == "production":
            if self.jwt_secret_key in default_jwt_secrets:
                raise ValueError(
                    "CRITICAL SECURITY ERROR: Default JWT secret detected in production. "
                    "Set JWT_SECRET_KEY environment variable to a secure random value. "
                    "Generate one with: openssl rand -hex 32"
                )

            # Check JWT secret length (minimum 32 characters for security)
            if len(self.jwt_secret_key) < 32:
                raise ValueError(
                    "CRITICAL SECURITY ERROR: JWT secret must be at least 32 characters long in production. "
                    "Generate a secure secret with: openssl rand -hex 32"
                )
        else:
            # Warn in non-production environments
            if self.jwt_secret_key in default_jwt_secrets:
                warnings.warn(
                    f"WARNING: Using default JWT secret in {self.environment} environment. "
                    "This is OK for development but MUST be changed for production.",
                    UserWarning,
                    stacklevel=2
                )

        return self

    @property
    def async_database_url(self) -> str:
        """Get async database URL."""
        return self.database_url

    @property
    def sync_database_url(self) -> str:
        """Get sync database URL for Alembic."""
        # Handle SQLite URLs (no need to replace driver)
        if self.database_url.startswith("sqlite"):
            return self.database_url.replace("+aiosqlite", "")
        # Convert PostgreSQL async to sync
        return self.database_url.replace("+asyncpg", "+psycopg2")

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
