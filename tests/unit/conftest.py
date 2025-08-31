"""Unit test configuration."""

import os

import pytest
from fastapi import FastAPI

# Set minimal env so Settings validation passes for unit tests
# (These are safe dummy values; unit tests won't call external services.)
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "dummy-token")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "dummy-secret")
os.environ.setdefault("TELNYX_API_KEY", "dummy-telnyx-key")
os.environ.setdefault("TELNYX_CONNECTION_ID", "dummy-conn-id")

# Unit tests don't need database URLs - they don't hit the database
# Each test that needs DB access should set up its own environment

# Import and create the app AFTER env is set
from app.main import create_app as _create_app  # noqa: E402


@pytest.fixture
def app() -> FastAPI:
    """Return a fresh app instance for unit tests."""
    from tests.conftest import reset_settings_cache

    reset_settings_cache()
    return _create_app()
