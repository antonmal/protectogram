"""Global test configuration."""

import pytest
from app.core.settings import get_settings


def reset_settings_cache():
    """Reset the settings cache to pick up new environment variables."""
    get_settings.cache_clear()


@pytest.fixture(scope="session", autouse=True)
def _ensure_test_environment():
    """Ensure we're in a test environment."""
    import os
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("SCHEDULER_ENABLED", "false")
