"""
Configuration management using Pydantic Settings.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden via environment variables
    or a .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = Field(default="DocAssist Practice Manager")
    app_version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)

    # Paths
    data_dir: Path = Field(default=Path("data"))
    log_dir: Path = Field(default=Path("logs"))

    # Database
    database_name: str = Field(default="practice.db")

    # EMR Integration
    emr_database_path: Optional[Path] = Field(default=None)
    emr_sync_enabled: bool = Field(default=True)

    # Ollama LLM
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="qwen2.5:3b")
    ollama_timeout: int = Field(default=120)  # seconds

    # Voice Agent
    voice_enabled: bool = Field(default=True)
    whisper_model: str = Field(default="base.en")
    wake_word: str = Field(default="hey docassist")
    voice_language: str = Field(default="en")

    # ChromaDB
    chroma_dir: str = Field(default="chroma")
    embedding_model: str = Field(default="all-MiniLM-L6-v2")

    # Notifications
    sms_gateway_enabled: bool = Field(default=False)
    sms_gateway_url: Optional[str] = Field(default=None)
    sms_gateway_api_key: Optional[str] = Field(default=None)

    whatsapp_enabled: bool = Field(default=False)
    whatsapp_api_url: Optional[str] = Field(default=None)
    whatsapp_api_token: Optional[str] = Field(default=None)

    # Security
    session_timeout_minutes: int = Field(default=30)
    max_login_attempts: int = Field(default=5)

    # UI
    theme_mode: str = Field(default="system")  # light, dark, system
    window_width: int = Field(default=1280)
    window_height: int = Field(default=800)

    @property
    def database_path(self) -> Path:
        """Get full database path."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / self.database_name

    @property
    def chroma_path(self) -> Path:
        """Get ChromaDB directory path."""
        path = self.data_dir / self.chroma_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def log_path(self) -> Path:
        """Get log directory path."""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        return self.log_dir


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings instance with values from env/file.
    """
    return Settings()


def reset_settings() -> None:
    """Reset settings cache. Useful for testing."""
    get_settings.cache_clear()
