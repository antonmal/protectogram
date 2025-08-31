"""Application settings and configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _is_testing() -> bool:
    """Check if we're running in a test environment."""
    import sys
    return "pytest" in sys.modules or any("test" in arg for arg in sys.argv)


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env" if not _is_testing() else None,  # Don't load .env in tests
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_env: Literal["local", "staging", "prod", "test"] = Field(
        default="local", description="Application environment"
    )
    log_level: str = Field(default="INFO", description="Logging level")

    # Database URLs
    app_database_url: str | None = Field(
        default=None, description="Async database connection URL"
    )
    app_database_url_sync: str | None = Field(
        default=None, description="Sync database connection URL"
    )
    alembic_database_url: str | None = Field(
        default=None, description="Alembic database URL override"
    )

    # Metrics
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics")

    # Scheduler
    scheduler_enabled: bool = Field(default=False, description="Enable APScheduler")
    scheduler_jobstore_table_name: str = Field(
        default="apscheduler_jobs", description="Scheduler jobstore table name"
    )
    startup_heartbeat_job_cron: str | None = Field(
        default="*/1 * * * *", description="Heartbeat job cron schedule"
    )
    readiness_db_timeout_sec: int = Field(
        default=3, description="Database connection timeout for readiness checks"
    )

    # Telegram
    telegram_bot_token: str | None = Field(default=None, description="Telegram bot token")
    telegram_webhook_secret: str | None = Field(
        default=None, description="Telegram webhook secret token"
    )
    telegram_api_base: str = Field(
        default="https://api.telegram.org", description="Telegram API base URL"
    )
    telegram_allowlist_chat_ids: str | None = Field(
        default=None, description="Comma-separated list of allowed chat IDs"
    )

    # Telnyx
    telnyx_api_key: str | None = Field(default=None, description="Telnyx API key")
    telnyx_webhook_secret: str | None = Field(
        default=None, description="Telnyx webhook secret"
    )

    @model_validator(mode="after")
    def validate_scheduler_config(self) -> "Settings":
        """Validate scheduler configuration."""
        if self.scheduler_enabled and not self.app_database_url_sync:
            raise ValueError("APP_DATABASE_URL_SYNC is required when scheduler is enabled")
        return self

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables."""
        return cls()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings.from_env()


# Legacy compatibility - will be removed
settings = get_settings()
