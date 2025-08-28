"""Contract test fixtures and configuration."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.services import FakePanicService, FakeTelegramService, FakeTelnyxService
from app.main import create_app


@pytest.fixture
def contract_app() -> Any:
    """Create FastAPI app for contract tests with DB disabled."""
    import os

    # Set environment for contract tests
    os.environ["ENABLE_DB"] = "false"
    os.environ["SCHEDULER_ENABLED"] = "false"
    os.environ["TELEGRAM_WEBHOOK_SECRET"] = "test_secret"
    os.environ["TELNYX_API_KEY"] = "test_api_key"

    app = create_app()

    # Override dependencies with fake services
    fake_telegram_service = FakeTelegramService()
    fake_panic_service = FakePanicService()
    fake_telnyx_service = FakeTelnyxService()

    from app.core.dependencies import (
        get_panic_service,
        get_telegram_service,
        get_telnyx_service,
    )

    app.dependency_overrides[get_telegram_service] = lambda: fake_telegram_service
    app.dependency_overrides[get_panic_service] = lambda: fake_panic_service
    app.dependency_overrides[get_telnyx_service] = lambda: fake_telnyx_service

    yield app

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def contract_client(contract_app: Any) -> TestClient:
    """Create test client for contract tests."""
    return TestClient(contract_app)


@pytest.fixture
def fake_telegram_service() -> FakeTelegramService:
    """Create fake Telegram service for testing."""
    return FakeTelegramService()


@pytest.fixture
def fake_panic_service() -> FakePanicService:
    """Create fake Panic service for testing."""
    return FakePanicService()


@pytest.fixture
def fake_telnyx_service() -> FakeTelnyxService:
    """Create fake Telnyx service for testing."""
    return FakeTelnyxService()


# Sample Telegram updates for testing
SAMPLE_MESSAGE_UPDATE = {
    "update_id": 12345,
    "message": {
        "message_id": 1,
        "from": {
            "id": 123456789,
            "first_name": "Test User",
            "is_bot": False,
        },
        "chat": {
            "id": 123456789,
            "type": "private",
        },
        "text": "Hello",
    },
}

SAMPLE_CALLBACK_UPDATE = {
    "update_id": 12346,
    "callback_query": {
        "id": "callback_id",
        "from": {
            "id": 123456789,
            "first_name": "Test User",
            "is_bot": False,
        },
        "message": {
            "message_id": 1,
            "chat": {
                "id": 123456789,
                "type": "private",
            },
        },
        "data": "test_button",
    },
}


# Sample Telnyx events for testing
SAMPLE_CALL_INITIATED = {
    "data": {
        "id": "telnyx_event_123",
        "event_type": "call.initiated",
        "payload": {
            "call_control_id": "call_123",
            "to": "+1234567890",
            "from": "+0987654321",
        },
    },
}

SAMPLE_CALL_ANSWERED = {
    "data": {
        "id": "telnyx_event_124",
        "event_type": "call.answered",
        "payload": {
            "call_control_id": "call_123",
        },
    },
}

SAMPLE_CALL_HANGUP = {
    "data": {
        "id": "telnyx_event_125",
        "event_type": "call.hangup",
        "payload": {
            "call_control_id": "call_123",
            "hangup_cause": "normal_clearing",
        },
    },
}

SAMPLE_CALL_GATHER_ENDED = {
    "data": {
        "id": "telnyx_event_126",
        "event_type": "call.gather.ended",
        "payload": {
            "call_control_id": "call_123",
            "digits": "1",
        },
    },
}
