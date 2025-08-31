"""Unit tests for settings."""

import os

import pytest

from app.core.settings import Settings, get_settings


@pytest.mark.unit
def test_settings_defaults():
    """Test settings with default values."""
    # Clean up environment to test defaults
    env_vars = [
        "APP_ENV",
        "LOG_LEVEL",
        "APP_DATABASE_URL",
        "APP_DATABASE_URL_SYNC",
        "ALEMBIC_DATABASE_URL",
        "METRICS_ENABLED",
        "SCHEDULER_ENABLED",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_WEBHOOK_SECRET",
        "TELEGRAM_API_BASE",
        "TELEGRAM_ALLOWLIST_CHAT_IDS",
        "TELNYX_API_KEY",
        "TELNYX_WEBHOOK_SECRET",
    ]

    original_values = {}
    for var in env_vars:
        original_values[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]

    try:
        settings = Settings()
        assert settings.app_env == "local"
        assert settings.log_level == "INFO"
        assert settings.metrics_enabled is True
        assert settings.scheduler_enabled is False
        assert settings.telegram_api_base == "https://api.telegram.org"
    finally:
        # Restore original values
        for var, value in original_values.items():
            if value is not None:
                os.environ[var] = value


@pytest.mark.unit
def test_settings_from_env():
    """Test settings from environment variables."""
    # Set test environment variables
    os.environ["APP_ENV"] = "staging"
    os.environ["LOG_LEVEL"] = "DEBUG"
    os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
    os.environ["TELEGRAM_WEBHOOK_SECRET"] = "test_secret"

    try:
        settings = Settings.from_env()
        assert settings.app_env == "staging"
        assert settings.log_level == "DEBUG"
        assert settings.telegram_bot_token == "test_token"
        assert settings.telegram_webhook_secret == "test_secret"
    finally:
        # Clean up
        for var in ["APP_ENV", "LOG_LEVEL", "TELEGRAM_BOT_TOKEN", "TELEGRAM_WEBHOOK_SECRET"]:
            os.environ.pop(var, None)


@pytest.mark.unit
def test_get_settings_cache():
    """Test that get_settings uses caching."""
    # Clear cache first
    get_settings.cache_clear()

    # Get settings twice
    settings1 = get_settings()
    settings2 = get_settings()

    # Should be the same instance (cached)
    assert settings1 is settings2
