"""Unit tests for PanicSessionService."""

import pytest
from datetime import datetime, timezone

from app.services.panic_session_service import PanicSessionService
from app.models import (
    User,
    Guardian,
    UserGuardian,
    PanicSession,
    PanicCycle,
    GuardianSessionStatus,
)
from app.models.user import Gender


@pytest.mark.asyncio
class TestPanicSessionService:
    """Test PanicSessionService functionality."""

    async def test_start_panic_session_new_session(self, async_db_session):
        """Test starting a new panic session."""
        # Create test user
        user = User(
            telegram_user_id=12345,
            first_name="John",
            phone_number="+1234567890",
            gender=Gender.MALE,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        await async_db_session.refresh(user)

        # Create test guardian and relationship
        guardian = Guardian(
            name="Test Guardian", phone_number="+0987654321", telegram_chat_id=54321
        )
        async_db_session.add(guardian)
        await async_db_session.commit()
        await async_db_session.refresh(guardian)

        user_guardian = UserGuardian(
            user_id=user.id, guardian_id=guardian.id, priority_order=1
        )
        async_db_session.add(user_guardian)
        await async_db_session.commit()

        # Create panic service
        panic_service = PanicSessionService(async_db_session)

        # Start panic session
        session = await panic_service.start_panic_session(
            user_id=user.id, message="Test emergency"
        )

        # Verify session created
        assert session is not None
        assert session.user_id == user.id
        assert session.message == "Test emergency"
        assert session.status == "active"
        assert len(session.cycles) == 1
        assert len(session.guardian_statuses) == 1

        # Verify cycle created
        cycle = session.cycles[0]
        assert cycle.cycle_number == 1
        assert cycle.status == "active"
        assert cycle.session_id == session.id

        # Verify guardian status initialized
        guardian_status = session.guardian_statuses[0]
        assert guardian_status.guardian_id == guardian.id
        assert guardian_status.status == "scheduled"
        assert guardian_status.telegram_sent is False
        assert guardian_status.voice_call_made is False
        assert guardian_status.sms_sent is False

    async def test_start_panic_session_existing_active_session(self, async_db_session):
        """Test starting panic session when one already exists."""
        # Create test user
        user = User(
            telegram_user_id=12345,
            first_name="John",
            phone_number="+1234567890",
            gender=Gender.MALE,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        await async_db_session.refresh(user)

        # Create existing active session
        existing_session = PanicSession(
            user_id=user.id, status="active", message="Existing emergency"
        )
        async_db_session.add(existing_session)
        await async_db_session.commit()

        # Create panic service
        panic_service = PanicSessionService(async_db_session)

        # Try to start new session
        session = await panic_service.start_panic_session(
            user_id=user.id, message="New emergency"
        )

        # Should return existing session
        assert session.id == existing_session.id
        assert session.message == "Existing emergency"

    async def test_handle_guardian_response_positive(self, async_db_session):
        """Test handling positive guardian response."""
        # Create test data
        user = User(
            telegram_user_id=12345,
            first_name="John",
            phone_number="+1234567890",
            gender=Gender.MALE,
        )
        async_db_session.add(user)

        guardian = Guardian(name="Test Guardian", phone_number="+0987654321")
        async_db_session.add(guardian)
        await async_db_session.commit()
        await async_db_session.refresh(user)
        await async_db_session.refresh(guardian)

        # Create panic session
        session = PanicSession(user_id=user.id, status="active")
        async_db_session.add(session)
        await async_db_session.commit()
        await async_db_session.refresh(session)

        # Create guardian status
        guardian_status = GuardianSessionStatus(
            session_id=session.id, guardian_id=guardian.id, status="contact_attempted"
        )
        async_db_session.add(guardian_status)
        await async_db_session.commit()

        # Create panic service
        panic_service = PanicSessionService(async_db_session)

        # Handle positive response
        result = await panic_service.handle_guardian_response(
            session_id=session.id,
            guardian_id=guardian.id,
            response_type="positive",
            response_method="telegram",
        )

        # Verify response
        assert result["status"] == "acknowledged"
        assert result["acknowledged_by"] == guardian.id

        # Verify session updated
        await async_db_session.refresh(session)
        assert session.status == "acknowledged"
        assert session.acknowledged_by == guardian.id
        assert session.acknowledged_at is not None

        # Verify guardian status updated
        await async_db_session.refresh(guardian_status)
        assert guardian_status.status == "acknowledged"
        assert guardian_status.response_type == "positive"
        assert guardian_status.response_method == "telegram"
        assert guardian_status.responded_at is not None

    async def test_handle_guardian_response_negative(self, async_db_session):
        """Test handling negative guardian response."""
        # Create test data
        user = User(
            telegram_user_id=12345,
            first_name="John",
            phone_number="+1234567890",
            gender=Gender.MALE,
        )
        async_db_session.add(user)

        guardian = Guardian(name="Test Guardian", phone_number="+0987654321")
        async_db_session.add(guardian)
        await async_db_session.commit()
        await async_db_session.refresh(user)
        await async_db_session.refresh(guardian)

        # Create panic session
        session = PanicSession(user_id=user.id, status="active")
        async_db_session.add(session)
        await async_db_session.commit()
        await async_db_session.refresh(session)

        # Create cycle
        cycle = PanicCycle(
            session_id=session.id,
            cycle_number=1,
            status="active",
            expires_at=datetime.now(timezone.utc),
        )
        async_db_session.add(cycle)

        # Create guardian status
        guardian_status = GuardianSessionStatus(
            session_id=session.id, guardian_id=guardian.id, status="contact_attempted"
        )
        async_db_session.add(guardian_status)
        await async_db_session.commit()

        # Create panic service
        panic_service = PanicSessionService(async_db_session)

        # Handle negative response
        result = await panic_service.handle_guardian_response(
            session_id=session.id,
            guardian_id=guardian.id,
            response_type="negative",
            response_method="voice",
        )

        # Verify response
        assert result["status"] == "declined"
        assert result["guardian_excluded"] == guardian.id

        # Verify session still active
        await async_db_session.refresh(session)
        assert session.status == "active"

        # Verify guardian status updated
        await async_db_session.refresh(guardian_status)
        assert guardian_status.status == "declined"
        assert guardian_status.response_type == "negative"
        assert guardian_status.response_method == "voice"
        assert guardian_status.excluded_from_cycle == 1

    async def test_cancel_session(self, async_db_session):
        """Test cancelling a panic session."""
        # Create test data
        user = User(
            telegram_user_id=12345,
            first_name="John",
            phone_number="+1234567890",
            gender=Gender.MALE,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        await async_db_session.refresh(user)

        # Create panic session
        session = PanicSession(user_id=user.id, status="active")
        async_db_session.add(session)
        await async_db_session.commit()
        await async_db_session.refresh(session)

        # Create panic service
        panic_service = PanicSessionService(async_db_session)

        # Cancel session
        success = await panic_service.cancel_session(
            session_id=session.id, user_id=user.id
        )

        # Verify cancellation
        assert success is True

        # Verify session updated
        await async_db_session.refresh(session)
        assert session.status == "cancelled"
        assert session.cancelled_at is not None

    async def test_cancel_session_wrong_user(self, async_db_session):
        """Test cancelling session with wrong user."""
        # Create test users
        user1 = User(
            telegram_user_id=12345,
            first_name="John",
            phone_number="+1234567890",
            gender=Gender.MALE,
        )
        user2 = User(
            telegram_user_id=54321,
            first_name="Jane",
            phone_number="+0987654321",
            gender=Gender.FEMALE,
        )
        async_db_session.add_all([user1, user2])
        await async_db_session.commit()
        await async_db_session.refresh(user1)
        await async_db_session.refresh(user2)

        # Create panic session for user1
        session = PanicSession(user_id=user1.id, status="active")
        async_db_session.add(session)
        await async_db_session.commit()
        await async_db_session.refresh(session)

        # Create panic service
        panic_service = PanicSessionService(async_db_session)

        # Try to cancel with user2
        success = await panic_service.cancel_session(
            session_id=session.id, user_id=user2.id
        )

        # Should fail
        assert success is False

        # Verify session unchanged
        await async_db_session.refresh(session)
        assert session.status == "active"
        assert session.cancelled_at is None
