"""Application settings and configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_env: str = Field(default="local", description="Application environment")
    log_level: str = Field(default="INFO", description="Logging level")

    # Database
    database_url: str | None = Field(default=None, description="Database connection URL")

    # Telegram
    telegram_bot_token: str | None = Field(default=None, description="Telegram bot token")

    # Telnyx
    telnyx_api_key: str | None = Field(default=None, description="Telnyx API key")
    telnyx_webhook_secret: str | None = Field(default=None, description="Telnyx webhook secret")

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables."""
        return cls()


# Global settings instance
settings = Settings.from_env()
