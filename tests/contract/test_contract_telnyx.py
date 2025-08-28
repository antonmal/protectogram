"""Contract tests for Telnyx webhook."""

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from tests.contract.conftest import (
    SAMPLE_CALL_ANSWERED,
    SAMPLE_CALL_GATHER_ENDED,
    SAMPLE_CALL_HANGUP,
    SAMPLE_CALL_INITIATED,
)


@pytest.mark.contract
class TestTelnyxWebhookContract:
    """Contract tests for Telnyx webhook endpoint."""

    def test_telnyx_webhook_missing_signature(
        self, contract_client: TestClient
    ) -> None:
        """Test webhook without signature header."""
        response = contract_client.post("/telnyx/webhook")
        assert response.status_code == 422  # Validation error

    def test_telnyx_webhook_invalid_signature(
        self, contract_client: TestClient
    ) -> None:
        """Test webhook with invalid signature."""
        response = contract_client.post(
            "/telnyx/webhook",
            headers={"Telnyx-Signature-Ed25519": "invalid_signature"},
            json=SAMPLE_CALL_INITIATED,
        )
        assert response.status_code == 403

    def test_telnyx_webhook_invalid_json(self, contract_client: TestClient) -> None:
        """Test webhook with invalid JSON body."""
        # Create a valid signature for the invalid JSON
        payload = b"invalid json"
        signature = hmac.new(
            b"test_key",  # This should match the test secret
            payload,
            hashlib.sha256,
        ).hexdigest()

        response = contract_client.post(
            "/telnyx/webhook",
            headers={
                "Telnyx-Signature-Ed25519": signature,
                "Content-Type": "application/json",
            },
            content=payload,
        )
        assert response.status_code == 400

    def test_telnyx_webhook_missing_event_id(self, contract_client: TestClient) -> None:
        """Test webhook with missing event ID."""
        payload = {"data": {"event_type": "call.initiated"}}
        signature = hmac.new(
            b"test_key",
            json.dumps(payload).encode(),
            hashlib.sha256,
        ).hexdigest()

        response = contract_client.post(
            "/telnyx/webhook",
            headers={
                "Telnyx-Signature-Ed25519": signature,
                "Content-Type": "application/json",
            },
            content=json.dumps(payload),
        )
        assert response.status_code == 400

    def test_telnyx_webhook_valid_call_initiated(
        self, contract_client: TestClient
    ) -> None:
        """Test webhook with valid call.initiated event."""
        payload = json.dumps(SAMPLE_CALL_INITIATED)
        signature = hmac.new(
            b"test_key",
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        response = contract_client.post(
            "/telnyx/webhook",
            headers={
                "Telnyx-Signature-Ed25519": signature,
                "Content-Type": "application/json",
            },
            content=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_telnyx_webhook_valid_call_answered(
        self, contract_client: TestClient
    ) -> None:
        """Test webhook with valid call.answered event."""
        payload = json.dumps(SAMPLE_CALL_ANSWERED)
        signature = hmac.new(
            b"test_key",
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        response = contract_client.post(
            "/telnyx/webhook",
            headers={
                "Telnyx-Signature-Ed25519": signature,
                "Content-Type": "application/json",
            },
            content=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_telnyx_webhook_valid_call_hangup(
        self, contract_client: TestClient
    ) -> None:
        """Test webhook with valid call.hangup event."""
        payload = json.dumps(SAMPLE_CALL_HANGUP)
        signature = hmac.new(
            b"test_key",
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        response = contract_client.post(
            "/telnyx/webhook",
            headers={
                "Telnyx-Signature-Ed25519": signature,
                "Content-Type": "application/json",
            },
            content=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_telnyx_webhook_valid_call_gather_ended(
        self, contract_client: TestClient
    ) -> None:
        """Test webhook with valid call.gather.ended event."""
        payload = json.dumps(SAMPLE_CALL_GATHER_ENDED)
        signature = hmac.new(
            b"test_key",
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        response = contract_client.post(
            "/telnyx/webhook",
            headers={
                "Telnyx-Signature-Ed25519": signature,
                "Content-Type": "application/json",
            },
            content=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_telnyx_webhook_duplicate_event_id(
        self, contract_client: TestClient
    ) -> None:
        """Test webhook with duplicate event ID."""
        payload = json.dumps(SAMPLE_CALL_INITIATED)
        signature = hmac.new(
            b"test_key",
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        # First request
        response1 = contract_client.post(
            "/telnyx/webhook",
            headers={
                "Telnyx-Signature-Ed25519": signature,
                "Content-Type": "application/json",
            },
            content=payload,
        )
        assert response1.status_code == 200

        # Second request with same event ID
        response2 = contract_client.post(
            "/telnyx/webhook",
            headers={
                "Telnyx-Signature-Ed25519": signature,
                "Content-Type": "application/json",
            },
            content=payload,
        )
        assert response2.status_code == 200
        data = response2.json()
        assert data["message"] == "Duplicate event ignored"
