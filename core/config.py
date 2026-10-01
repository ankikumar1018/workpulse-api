"""Core configuration and settings management."""

from __future__ import annotations

from functools import cached_property, lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment variables.

    Field defaults double as local-development fallbacks; pydantic-settings
    reads matching environment variables and `.env` automatically, so no
    manual `os.getenv()` calls are needed here.
    """

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # App settings
    APP_NAME: str = "WorkPulse API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database settings
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "workpulse"
    SQL_ECHO: bool = False

    # Security settings
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # WhatsApp Business Cloud API settings
    WHATSAPP_ACCESS_TOKEN: str | None = None
    WHATSAPP_PHONE_NUMBER_ID: str | None = None
    WHATSAPP_API_VERSION: str = "v24.0"
    WHATSAPP_APP_SECRET: str | None = None
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str | None = None

    # CORS settings
    CORS_ORIGINS: list[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    @field_validator("CORS_ORIGINS", "CORS_ALLOW_METHODS", "CORS_ALLOW_HEADERS", mode="before")
    @classmethod
    def _split_comma_separated(cls, value: object) -> object:
        """Accept `.env`-friendly comma-separated strings for list fields."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def _disable_credentials_for_wildcard_origins(self) -> Settings:
        """Browsers reject credentialed requests with a wildcard origin; mirror that here."""
        if self.CORS_ORIGINS == ["*"] and self.CORS_ALLOW_CREDENTIALS:
            self.CORS_ALLOW_CREDENTIALS = False
        return self

    @cached_property
    def DATABASE_URL(self) -> str:
        """Build database connection URL."""
        return (
            f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings, injectable via `Depends(get_settings)`."""
    return Settings()


# Module-level singleton kept for existing call sites; prefer `get_settings()` in new code.
settings = get_settings()

__all__ = ["Settings", "get_settings", "settings"]
