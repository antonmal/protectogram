"""Contract tests for Telegram webhook."""

import pytest
from fastapi.testclient import TestClient

from tests.contract.conftest import (
    SAMPLE_CALLBACK_UPDATE,
    SAMPLE_MESSAGE_UPDATE,
)


@pytest.mark.contract
class TestTelegramWebhookContract:
    """Contract tests for Telegram webhook endpoint."""

    def test_telegram_webhook_missing_secret(self, contract_client: TestClient) -> None:
        """Test webhook without secret parameter."""
        response = contract_client.post("/telegram/webhook")
        assert response.status_code == 422  # Validation error

    def test_telegram_webhook_invalid_secret(self, contract_client: TestClient) -> None:
        """Test webhook with invalid secret."""
        response = contract_client.post("/telegram/webhook?secret=invalid")
        assert response.status_code == 403

    def test_telegram_webhook_invalid_json(self, contract_client: TestClient) -> None:
        """Test webhook with invalid JSON body."""
        response = contract_client.post(
            "/telegram/webhook?secret=test_secret",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400

    def test_telegram_webhook_missing_update_id(
        self, contract_client: TestClient
    ) -> None:
        """Test webhook with missing update_id."""
        payload = {"message": {"text": "test"}}
        response = contract_client.post(
            "/telegram/webhook?secret=test_secret",
            json=payload,
        )
        assert response.status_code == 400

    def test_telegram_webhook_valid_message(self, contract_client: TestClient) -> None:
        """Test webhook with valid message update."""
        response = contract_client.post(
            "/telegram/webhook?secret=test_secret",
            json=SAMPLE_MESSAGE_UPDATE,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_telegram_webhook_valid_callback_query(
        self, contract_client: TestClient
    ) -> None:
        """Test webhook with valid callback query."""
        response = contract_client.post(
            "/telegram/webhook?secret=test_secret",
            json=SAMPLE_CALLBACK_UPDATE,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_telegram_webhook_duplicate_update_id(
        self, contract_client: TestClient
    ) -> None:
        """Test webhook with duplicate update_id."""
        # First request
        response1 = contract_client.post(
            "/telegram/webhook?secret=test_secret",
            json=SAMPLE_MESSAGE_UPDATE,
        )
        assert response1.status_code == 200

        # Second request with same update_id
        response2 = contract_client.post(
            "/telegram/webhook?secret=test_secret",
            json=SAMPLE_MESSAGE_UPDATE,
        )
        assert response2.status_code == 200
        data = response2.json()
        assert data["message"] == "Duplicate update ignored"


# Contract tests use fixtures from conftest_contract.py
