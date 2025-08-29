"""Application settings and configuration."""

from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_env: Literal["local", "staging", "prod"] = Field(
        default="local", description="Application environment"
    )
    log_level: str = Field(default="INFO", description="Logging level")

    # Database URLs
    # Runtime (web app / async ORM)
    app_database_url: str | None = Field(default=None, description="Async database connection URL")
    # Sync consumers (Alembic + APScheduler jobstore)
    app_database_url_sync: str | None = Field(
        default=None, description="Sync database connection URL"
    )
    # Alembic override (optional)
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

    # Telnyx
    telnyx_api_key: str | None = Field(default=None, description="Telnyx API key")
    telnyx_webhook_secret: str | None = Field(default=None, description="Telnyx webhook secret")

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


# Global settings instance
settings = Settings.from_env()
