# app/config/settings.py
"""
Settings management for Protectogram application.
Uses factory pattern to create environment-specific settings.
"""

import os
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Dict, List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class BaseAppSettings(BaseSettings, ABC):
    """Base settings class with common configuration."""

    # App Configuration
    app_name: str = "protectogram"
    environment: str = Field(..., validation_alias="ENVIRONMENT")
    primary_language: str = Field("ru", validation_alias="PRIMARY_LANGUAGE")
    supported_languages: str = Field(
        default="ru,en,es", validation_alias="SUPPORTED_LANGUAGES"
    )
    timezone: str = Field("Europe/Madrid", validation_alias="TIMEZONE")

    # Database
    database_url: str = Field(..., validation_alias="DATABASE_URL")
    redis_url: str = Field(..., validation_alias="REDIS_URL")

    # Security
    secret_key: str = Field(
        default="dev-secret-key-change-in-production", validation_alias="SECRET_KEY"
    )
    webhook_secret: Optional[str] = Field(None, validation_alias="WEBHOOK_SECRET")

    # Telegram
    telegram_bot_token: str = Field(..., validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_bot_username: str = Field(..., validation_alias="TELEGRAM_BOT_USERNAME")
    webhook_base_url: str = Field(..., validation_alias="WEBHOOK_BASE_URL")

    # Communication Base Settings
    communication_providers: str = Field(
        default="twilio", validation_alias="COMMUNICATION_PROVIDERS"
    )
    max_cost_per_minute: float = Field(0.30, validation_alias="MAX_COST_PER_MINUTE")
    blocked_country_codes: str = Field(
        default="+7", validation_alias="BLOCKED_COUNTRY_CODES"
    )

    # Alert Timing Configuration (SEPARATED by context)
    voice_call_retry_interval: int = Field(
        default=180, validation_alias="VOICE_CALL_RETRY_INTERVAL"
    )  # 3 minutes
    voice_call_max_duration: int = Field(
        default=900, validation_alias="VOICE_CALL_MAX_DURATION"
    )  # 15 minutes
    voice_call_timeout: int = Field(
        default=30, validation_alias="VOICE_CALL_TIMEOUT"
    )  # 30 seconds per call

    # Trip-specific settings
    trip_reminder_intervals: str = Field(
        default="0,1,2", validation_alias="TRIP_REMINDER_INTERVALS"
    )
    trip_call_reminder: int = Field(3, validation_alias="TRIP_CALL_REMINDER")
    trip_guardian_alert: int = Field(5, validation_alias="TRIP_GUARDIAN_ALERT")

    # Monitoring
    sentry_dsn: Optional[str] = Field(None, validation_alias="SENTRY_DSN")
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")

    @property
    def supported_languages_list(self) -> List[str]:
        """Get supported languages as a list."""
        if isinstance(self.supported_languages, str):
            return [lang.strip() for lang in self.supported_languages.split(",")]
        return self.supported_languages

    @property
    def communication_providers_list(self) -> List[str]:
        """Get communication providers as a list."""
        if isinstance(self.communication_providers, str):
            return [
                provider.strip() for provider in self.communication_providers.split(",")
            ]
        return self.communication_providers

    @property
    def blocked_country_codes_list(self) -> List[str]:
        """Get blocked country codes as a list."""
        if isinstance(self.blocked_country_codes, str):
            return [code.strip() for code in self.blocked_country_codes.split(",")]
        return self.blocked_country_codes

    @property
    def trip_reminder_intervals_list(self) -> List[int]:
        """Get trip reminder intervals as a list."""
        if isinstance(self.trip_reminder_intervals, str):
            return [
                int(interval.strip())
                for interval in self.trip_reminder_intervals.split(",")
            ]
        return self.trip_reminder_intervals

    @property
    def sync_database_url(self) -> str:
        """Get synchronous database URL for migrations (without +asyncpg)."""
        return self.database_url.replace("+asyncpg", "")

    @abstractmethod
    def get_communication_config(self) -> Dict:
        """Return communication provider configuration."""
        pass

    @abstractmethod
    def get_celery_config(self) -> Dict:
        """Return Celery configuration."""
        pass

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
        env_parse_none_str="null",
    )


class DevelopmentSettings(BaseAppSettings):
    """Development environment settings."""

    # Development-specific overrides
    log_level: str = "DEBUG"

    # Twilio Test Configuration
    twilio_account_sid: str = Field(..., validation_alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(..., validation_alias="TWILIO_AUTH_TOKEN")
    twilio_from_number: str = Field(..., validation_alias="TWILIO_FROM_NUMBER")
    test_phone_numbers: str = Field(default="", validation_alias="TEST_PHONE_NUMBERS")

    @property
    def test_phone_numbers_list(self) -> List[str]:
        """Get test phone numbers as a list."""
        if isinstance(self.test_phone_numbers, str) and self.test_phone_numbers:
            return [num.strip() for num in self.test_phone_numbers.split(",")]
        return []

    def get_communication_config(self) -> Dict:
        return {
            "twilio": {
                "account_sid": self.twilio_account_sid,
                "auth_token": self.twilio_auth_token,
                "from_number": self.twilio_from_number,
                "test_mode": True,
                "test_numbers": self.test_phone_numbers_list,
                "webhook_base_url": self.webhook_base_url,
            }
        }

    def get_celery_config(self) -> Dict:
        return {
            "broker_url": self.redis_url,
            "result_backend": self.redis_url,
            "task_serializer": "json",
            "accept_content": ["json"],
            "result_serializer": "json",
            "timezone": self.timezone,
            "enable_utc": True,
            "worker_prefetch_multiplier": 1,
            "task_acks_late": True,
            "worker_disable_rate_limits": True,  # Dev convenience
        }


class TestSettings(BaseAppSettings):
    """Test environment settings."""

    # Test-specific overrides - Docker PostgreSQL on port 5433
    database_url: str = "postgresql+asyncpg://postgres:test@localhost:5433/protectogram_test"  # pragma: allowlist secret
    redis_url: str = "redis://localhost:6379/1"
    log_level: str = "WARNING"

    # Required fields with test defaults
    telegram_bot_token: str = Field(
        default="test_token", validation_alias="TELEGRAM_BOT_TOKEN"
    )
    telegram_bot_username: str = Field(
        default="@TestBot", validation_alias="TELEGRAM_BOT_USERNAME"
    )
    webhook_base_url: str = Field(
        default="http://localhost:8000", validation_alias="WEBHOOK_BASE_URL"
    )

    # Mock everything in tests
    def get_communication_config(self) -> Dict:
        return {
            "mock": {
                "enabled": True,
                "fail_rate": 0.0,  # Configurable failure rate for testing
                "webhook_base_url": self.webhook_base_url,
            }
        }

    def get_celery_config(self) -> Dict:
        return {
            "task_always_eager": True,  # Execute tasks synchronously
            "task_eager_propagates": True,
            "broker_url": self.redis_url,
            "result_backend": self.redis_url,
        }


class StagingSettings(BaseAppSettings):
    """Staging environment settings."""

    # Production-like but with test accounts
    twilio_account_sid: str = Field(..., validation_alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(..., validation_alias="TWILIO_AUTH_TOKEN")
    twilio_from_number: str = Field(..., validation_alias="TWILIO_FROM_NUMBER")

    def get_communication_config(self) -> Dict:
        return {
            "twilio": {
                "account_sid": self.twilio_account_sid,
                "auth_token": self.twilio_auth_token,
                "from_number": self.twilio_from_number,
                "test_mode": True,  # Use test account but real calls
                "webhook_base_url": self.webhook_base_url,
            }
        }

    def get_celery_config(self) -> Dict:
        return {
            "broker_url": self.redis_url,
            "result_backend": self.redis_url,
            "task_serializer": "json",
            "accept_content": ["json"],
            "result_serializer": "json",
            "timezone": self.timezone,
            "enable_utc": True,
            "task_acks_late": True,
            "worker_prefetch_multiplier": 4,
            "worker_max_tasks_per_child": 1000,
        }


class ProductionSettings(BaseAppSettings):
    """Production environment settings."""

    # Production Twilio
    twilio_account_sid: str = Field(..., validation_alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(..., validation_alias="TWILIO_AUTH_TOKEN")
    twilio_from_number: str = Field(..., validation_alias="TWILIO_FROM_NUMBER")

    # Production-specific security
    webhook_secret: str = Field(
        ..., validation_alias="WEBHOOK_SECRET"
    )  # Required in prod

    def get_communication_config(self) -> Dict:
        return {
            "twilio": {
                "account_sid": self.twilio_account_sid,
                "auth_token": self.twilio_auth_token,
                "from_number": self.twilio_from_number,
                "test_mode": False,  # Live account and calls
                "webhook_base_url": self.webhook_base_url,
                "webhook_secret": self.webhook_secret,
            }
        }

    def get_celery_config(self) -> Dict:
        return {
            "broker_url": self.redis_url,
            "result_backend": self.redis_url,
            "task_serializer": "json",
            "accept_content": ["json"],
            "result_serializer": "json",
            "timezone": self.timezone,
            "enable_utc": True,
            "task_acks_late": True,
            "worker_prefetch_multiplier": 1,
            "worker_max_tasks_per_child": 1000,
            "worker_concurrency": 4,
            "broker_connection_retry_on_startup": True,
        }


# Settings Factory
class SettingsFactory:
    """Factory for creating environment-specific settings."""

    _settings_map = {
        "development": DevelopmentSettings,
        "test": TestSettings,
        "staging": StagingSettings,
        "production": ProductionSettings,
    }

    @classmethod
    def create(cls, environment: Optional[str] = None) -> BaseAppSettings:
        """Create settings instance for the specified environment."""

        if environment is None:
            environment = os.getenv("ENVIRONMENT", "development")

        if environment not in cls._settings_map:
            raise ValueError(
                f"Unknown environment: {environment}. "
                f"Available: {list(cls._settings_map.keys())}"
            )

        settings_class = cls._settings_map[environment]

        # Load .env file based on environment
        env_file = f".env.{environment}"
        if not os.path.exists(env_file):
            env_file = ".env"

        # Create settings instance
        try:
            return settings_class(_env_file=env_file)
        except Exception as e:
            print(f"Error loading settings for {environment}: {e}")
            # If it's development, provide helpful defaults
            if environment == "development":
                return settings_class(
                    environment="development",
                    database_url="postgresql+asyncpg://postgres:localpass@localhost:5432/protectogram_dev",  # pragma: allowlist secret
                    redis_url="redis://localhost:6379/0",
                    telegram_bot_token="YOUR_DEV_BOT_TOKEN_HERE",  # nosec B106 - Fallback placeholder only
                    telegram_bot_username="@ProtectogramDevBot",
                    webhook_base_url="http://localhost:8000",
                    twilio_account_sid="AC_test_xxxxx",
                    twilio_auth_token="test_token_xxxxx",
                    twilio_from_number="+15005550006",
                )
            raise

    @classmethod
    def get_available_environments(cls) -> List[str]:
        """Get list of available environment names."""
        return list(cls._settings_map.keys())


# Cached settings instance per environment
@lru_cache(maxsize=4)
def get_cached_settings(environment: str) -> BaseAppSettings:
    """Get cached settings instance for performance."""
    return SettingsFactory.create(environment)


# Convenience function for getting current settings
def get_settings() -> BaseAppSettings:
    """Get settings for current environment."""
    environment = os.getenv("ENVIRONMENT", "development")
    return get_cached_settings(environment)
