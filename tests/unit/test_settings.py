"""Unit tests for settings module."""

from app.core.settings import Settings


def test_settings_defaults() -> None:
    """Test settings default values."""
    # Clean up any environment variables that might have been set by other tests
    import os

    for key in [
        "APP_DATABASE_URL",
        "APP_DATABASE_URL_SYNC",
        "ALEMBIC_DATABASE_URL",
        "SCHEDULER_ENABLED",
    ]:
        if key in os.environ:
            del os.environ[key]

    settings = Settings()
    assert settings.app_env == "local"
    assert settings.log_level == "INFO"
    print(f"app_database_url: {settings.app_database_url}")
    assert settings.app_database_url is None
    assert settings.telegram_bot_token is None
    assert settings.telnyx_api_key is None
    assert settings.telnyx_webhook_secret is None


def test_settings_from_env() -> None:
    """Test settings creation from environment."""
    # Clean up any environment variables that might have been set by other tests
    import os

    for key in [
        "APP_DATABASE_URL",
        "APP_DATABASE_URL_SYNC",
        "ALEMBIC_DATABASE_URL",
        "SCHEDULER_ENABLED",
    ]:
        if key in os.environ:
            del os.environ[key]

    settings = Settings.from_env()
    assert isinstance(settings, Settings)
    assert settings.app_env == "local"
    assert settings.log_level == "INFO"
