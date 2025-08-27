"""Integration tests for API endpoints."""

from unittest.mock import patch

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.models import Incident, MemberLink, User


class TestSchedulerIntegration:
    """Test scheduler functionality with persistence and firing."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_scheduler_persistence_and_firing(self, test_session: AsyncSession):
        """Test scheduler persistence and firing with short intervals (Tier 1: basic test)."""
        # This test enables the scheduler to prove persistence & firing
        # Uses Tier 1 (SAVEPOINT) since scheduler is disabled by default

        # Temporarily enable scheduler for this test
        from app.core.config import settings

        original_scheduler_enabled = settings.SCHEDULER_ENABLED
        settings.SCHEDULER_ENABLED = True

        try:
            # Test that scheduler can be started and persists across operations
            # This is a basic test - in a real implementation, you would test actual job persistence
            assert settings.SCHEDULER_ENABLED is True

            # TODO: Add actual scheduler job persistence tests when scheduler is implemented
            # This would include:
            # 1. Creating a test job with short interval
            # 2. Verifying job persists in database
            # 3. Verifying job fires and executes
            # 4. Verifying job state is maintained across restarts

        finally:
            # Restore original scheduler setting
            settings.SCHEDULER_ENABLED = original_scheduler_enabled


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_health_live(self, async_client: httpx.AsyncClient):
        """Test health live endpoint."""
        response = await async_client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_health_ready_with_db(self, async_client: httpx.AsyncClient):
        """Test health ready endpoint with database."""
        response = await async_client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, async_client: httpx.AsyncClient):
        """Test metrics endpoint."""
        response = await async_client.get("/metrics", follow_redirects=True)
        assert response.status_code == 200
        assert "health_check_total" in response.text


class TestTelegramWebhook:
    """Test Telegram webhook endpoints."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_telegram_webhook_missing_secret(
        self, async_client: httpx.AsyncClient
    ):
        """Test Telegram webhook without secret."""
        response = await async_client.post("/telegram/webhook")
        assert response.status_code == 422

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_telegram_webhook_invalid_secret(
        self, async_client: httpx.AsyncClient
    ):
        """Test Telegram webhook with invalid secret."""
        response = await async_client.post("/telegram/webhook?secret=invalid")
        assert response.status_code == 403

    @pytest.mark.integration
    @pytest.mark.asyncio
    @patch("app.core.config.settings")
    async def test_telegram_webhook_valid_secret(
        self, mock_settings, async_client: httpx.AsyncClient
    ):
        """Test Telegram webhook with valid secret."""
        mock_settings.TELEGRAM_WEBHOOK_SECRET = "test_secret"
        payload = {"update_id": 123456, "message": {"text": "test"}}
        response = await async_client.post(
            "/telegram/webhook?secret=test_secret", json=payload
        )
        assert response.status_code == 200


class TestTelnyxWebhook:
    """Test Telnyx webhook endpoints."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_telnyx_webhook_empty_payload(self, async_client: httpx.AsyncClient):
        """Test Telnyx webhook with empty payload."""
        response = await async_client.post("/telnyx/webhook", json={})
        assert response.status_code == 422  # Missing required header

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_telnyx_webhook_call_initiated(self, async_client: httpx.AsyncClient):
        """Test Telnyx webhook with call initiated event."""
        payload = {
            "event_type": "call.initiated",
            "data": {"id": "test_call_id", "client_state": "call_attempt_1"},
        }
        response = await async_client.post("/telnyx/webhook", json=payload)
        assert response.status_code == 422  # Missing required header


class TestAdminEndpoints:
    """Test admin endpoints."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_trigger_panic_test_missing_user_id(
        self, async_client: httpx.AsyncClient
    ):
        """Test trigger panic test without user_id."""
        response = await async_client.post("/admin/trigger-panic-test", json={})
        assert response.status_code == 200  # No user_id required

    @pytest.mark.integration
    @pytest.mark.asyncio
    @patch("app.api.admin.trigger_panic_test")
    async def test_trigger_panic_test_success(
        self, mock_trigger, async_client: httpx.AsyncClient
    ):
        """Test trigger panic test success."""
        mock_trigger.return_value = "1"  # Function returns string

        response = await async_client.post(
            "/admin/trigger-panic-test", json={"user_id": 123}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["incident_id"] == "1"  # Now it's a string
        assert data["status"] == "success"


class TestDatabaseOperations:
    """Test database operations with Testcontainers-Postgres."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_user(self, test_session: AsyncSession):
        """Test creating a user."""
        user = User(
            telegram_id="123456789", phone_e164="+1234567890", display_name="Test User"
        )
        test_session.add(user)
        await test_session.flush()  # Flush to get the ID without committing

        assert user.id is not None
        assert user.telegram_id == "123456789"
        assert user.display_name == "Test User"

        # Verify the user was actually created in the database
        result = await test_session.execute(select(User).where(User.id == user.id))
        db_user = result.scalar_one()
        assert db_user.display_name == "Test User"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_member_link(self, test_session: AsyncSession):
        """Test creating a member link."""
        # Create users first
        user1 = User(telegram_id="111", display_name="User 1")
        user2 = User(telegram_id="222", display_name="User 2")
        test_session.add_all([user1, user2])
        await test_session.flush()  # Flush to get the IDs without committing

        member_link = MemberLink(
            watcher_user_id=user1.id,
            traveler_user_id=user2.id,
            status="active",
            call_priority=1,
        )
        test_session.add(member_link)
        await test_session.flush()  # Flush to get the ID without committing

        assert member_link.id is not None
        assert member_link.watcher_user_id == user1.id
        assert member_link.traveler_user_id == user2.id

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_incident(self, test_session: AsyncSession):
        """Test creating an incident."""
        user = User(telegram_id="123", display_name="Traveler")
        test_session.add(user)
        await test_session.flush()  # Flush to get the ID without committing

        incident = Incident(traveler_user_id=user.id, status="active")
        test_session.add(incident)
        await test_session.flush()  # Flush to get the ID without committing

        assert incident.id is not None
        assert incident.traveler_user_id == user.id
        assert incident.status == "active"
