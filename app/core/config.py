"""Application configuration using Pydantic settings."""

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application Environment
    APP_ENV: str = Field(default="staging", description="Application environment")
    DEBUG: bool = Field(default=False, description="Debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # Database
    POSTGRES_URL: str = Field(default="", description="PostgreSQL connection URL")

    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: str = Field(default="", description="Telegram bot token")
    TELEGRAM_WEBHOOK_SECRET: str = Field(
        default="", description="Telegram webhook secret"
    )

    # Telnyx Configuration
    TELNYX_API_KEY: str = Field(default="", description="Telnyx API key")
    TELNYX_CONNECTION_ID: str = Field(default="", description="Telnyx connection ID")

    # Observability
    SENTRY_DSN: str | None = Field(default=None, description="Sentry DSN")

    # Feature Flags
    FEATURE_PANIC: bool = Field(default=True, description="Enable panic feature")

    # Scheduler Control
    SCHEDULER_ENABLED: bool = Field(default=True, description="Enable APScheduler")

    # Call Cascade Defaults
    DEFAULT_RING_TIMEOUT_SEC: int = Field(
        default=25, description="Default ring timeout"
    )
    DEFAULT_MAX_RETRIES: int = Field(default=2, description="Default max retries")
    DEFAULT_RETRY_BACKOFF_SEC: int = Field(
        default=60, description="Default retry backoff"
    )
    DEFAULT_TOTAL_RING_CAP_SEC: int = Field(
        default=180, description="Default total ring cap"
    )
    DEFAULT_REMINDER_INTERVAL_SEC: int = Field(
        default=120, description="Default reminder interval"
    )

    # CORS
    ALLOWED_ORIGINS: list[str] = Field(
        default=["*"],
        description="Allowed CORS origins",
    )

    # Application URL
    BASE_URL: str = Field(
        default="http://localhost:8000",
        description="Base URL for the application",
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.APP_ENV == "prod"

    @property
    def is_staging(self) -> bool:
        """Check if running in staging."""
        return self.APP_ENV == "staging"

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
    )


# Global settings instance
settings = Settings()
