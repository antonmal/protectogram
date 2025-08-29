"""Unit tests for settings module."""

from app.core.settings import Settings


def test_settings_defaults() -> None:
    """Test settings default values."""
    settings = Settings()
    assert settings.app_env == "local"
    assert settings.log_level == "INFO"
    assert settings.database_url is None
    assert settings.telegram_bot_token is None
    assert settings.telnyx_api_key is None
    assert settings.telnyx_webhook_secret is None


def test_settings_from_env() -> None:
    """Test settings creation from environment."""
    settings = Settings.from_env()
    assert isinstance(settings, Settings)
    assert settings.app_env == "local"
    assert settings.log_level == "INFO"
