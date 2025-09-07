"""Integration tests for panic workflow."""

import pytest
from unittest.mock import patch

from app.services.panic_session_service import PanicSessionService
from app.models import User, Guardian, UserGuardian
from app.models.user import Gender


@pytest.mark.asyncio
class TestPanicWorkflowIntegration:
    """Test complete panic workflow integration."""

    @pytest.fixture
    async def test_data(self, async_db_session):
        """Create test user and guardians."""
        # Create user
        user = User(
            telegram_user_id=12345,
            first_name="Emergency User",
            phone_number="+1234567890",
            gender=Gender.MALE,
        )
        async_db_session.add(user)

        # Create guardians
        guardian1 = Guardian(
            name="Guardian One", phone_number="+1111111111", telegram_chat_id=11111
        )
        guardian2 = Guardian(
            name="Guardian Two", phone_number="+2222222222", telegram_chat_id=22222
        )
        guardian3 = Guardian(
            name="Guardian Three", phone_number="+3333333333", telegram_chat_id=33333
        )

        async_db_session.add_all([guardian1, guardian2, guardian3])
        await async_db_session.commit()
        await async_db_session.refresh(user)
        await async_db_session.refresh(guardian1)
        await async_db_session.refresh(guardian2)
        await async_db_session.refresh(guardian3)

        # Create user-guardian relationships
        relationships = [
            UserGuardian(user_id=user.id, guardian_id=guardian1.id, priority_order=1),
            UserGuardian(user_id=user.id, guardian_id=guardian2.id, priority_order=2),
            UserGuardian(user_id=user.id, guardian_id=guardian3.id, priority_order=3),
        ]
        async_db_session.add_all(relationships)
        await async_db_session.commit()

        return {"user": user, "guardians": [guardian1, guardian2, guardian3]}

    @patch("app.tasks.panic_notifications.notify_guardian_telegram.apply_async")
    @patch("app.tasks.panic_notifications.notify_guardian_voice.apply_async")
    @patch("app.tasks.panic_notifications.notify_guardian_sms.apply_async")
    @patch("app.tasks.panic_notifications.check_cycle_completion.apply_async")
    async def test_complete_panic_workflow_with_acknowledgment(
        self,
        mock_cycle_completion,
        mock_sms,
        mock_voice,
        mock_telegram,
        async_db_session,
        test_data,
    ):
        """Test complete panic workflow with guardian acknowledgment."""

        # Setup mocks to return task IDs
        mock_telegram.return_value.id = "telegram_task_1"
        mock_voice.return_value.id = "voice_task_1"
        mock_sms.return_value.id = "sms_task_1"
        mock_cycle_completion.return_value.id = "completion_task_1"

        user = test_data["user"]
        guardians = test_data["guardians"]

        # Create panic service
        panic_service = PanicSessionService(async_db_session)

        # Start panic session
        session = await panic_service.start_panic_session(
            user_id=user.id, message="Help! Emergency situation!"
        )

        # Verify session created
        assert session is not None
        assert session.status == "active"
        assert len(session.cycles) == 1
        assert len(session.guardian_statuses) == 3

        # Verify Celery tasks were scheduled
        assert mock_telegram.call_count >= 1
        assert mock_voice.call_count >= 1
        assert mock_sms.call_count >= 1
        assert mock_cycle_completion.call_count == 1

        # Simulate first guardian acknowledgment
        result = await panic_service.handle_guardian_response(
            session_id=session.id,
            guardian_id=guardians[0].id,
            response_type="positive",
            response_method="telegram",
        )

        # Verify acknowledgment processed
        assert result["status"] == "acknowledged"
        assert result["acknowledged_by"] == guardians[0].id

        # Verify session updated
        await async_db_session.refresh(session)
        assert session.status == "acknowledged"
        assert session.acknowledged_by == guardians[0].id
        assert session.acknowledged_at is not None

        # Verify guardian status updated
        guardian_status = next(
            gs for gs in session.guardian_statuses if gs.guardian_id == guardians[0].id
        )
        assert guardian_status.status == "acknowledged"
        assert guardian_status.response_type == "positive"
        assert guardian_status.response_method == "telegram"

    @patch("app.tasks.panic_notifications.notify_guardian_telegram.apply_async")
    @patch("app.tasks.panic_notifications.notify_guardian_voice.apply_async")
    @patch("app.tasks.panic_notifications.notify_guardian_sms.apply_async")
    @patch("app.tasks.panic_notifications.check_cycle_completion.apply_async")
    async def test_panic_workflow_with_guardian_decline(
        self,
        mock_cycle_completion,
        mock_sms,
        mock_voice,
        mock_telegram,
        async_db_session,
        test_data,
    ):
        """Test panic workflow when guardian declines."""

        # Setup mocks
        mock_telegram.return_value.id = "telegram_task_1"
        mock_voice.return_value.id = "voice_task_1"
        mock_sms.return_value.id = "sms_task_1"
        mock_cycle_completion.return_value.id = "completion_task_1"

        user = test_data["user"]
        guardians = test_data["guardians"]

        # Create panic service
        panic_service = PanicSessionService(async_db_session)

        # Start panic session
        session = await panic_service.start_panic_session(
            user_id=user.id, message="Emergency situation"
        )

        # First guardian declines
        result1 = await panic_service.handle_guardian_response(
            session_id=session.id,
            guardian_id=guardians[0].id,
            response_type="negative",
            response_method="voice",
        )

        # Verify decline processed
        assert result1["status"] == "declined"
        assert result1["guardian_excluded"] == guardians[0].id

        # Verify session still active
        await async_db_session.refresh(session)
        assert session.status == "active"

        # Second guardian acknowledges
        result2 = await panic_service.handle_guardian_response(
            session_id=session.id,
            guardian_id=guardians[1].id,
            response_type="positive",
            response_method="sms",
        )

        # Verify acknowledgment processed
        assert result2["status"] == "acknowledged"

        # Verify session now acknowledged
        await async_db_session.refresh(session)
        assert session.status == "acknowledged"
        assert session.acknowledged_by == guardians[1].id

    @patch("app.tasks.panic_notifications.notify_guardian_telegram.apply_async")
    @patch("app.tasks.panic_notifications.notify_guardian_voice.apply_async")
    @patch("app.tasks.panic_notifications.notify_guardian_sms.apply_async")
    @patch("app.tasks.panic_notifications.check_cycle_completion.apply_async")
    async def test_panic_session_cancellation_by_user(
        self,
        mock_cycle_completion,
        mock_sms,
        mock_voice,
        mock_telegram,
        async_db_session,
        test_data,
    ):
        """Test user cancelling their own panic session."""

        # Setup mocks
        mock_telegram.return_value.id = "telegram_task_1"
        mock_voice.return_value.id = "voice_task_1"
        mock_sms.return_value.id = "sms_task_1"
        mock_cycle_completion.return_value.id = "completion_task_1"

        user = test_data["user"]

        # Create panic service
        panic_service = PanicSessionService(async_db_session)

        # Start panic session
        session = await panic_service.start_panic_session(
            user_id=user.id, message="False alarm"
        )

        # Verify session active
        assert session.status == "active"

        # User cancels session
        success = await panic_service.cancel_session(
            session_id=session.id, user_id=user.id
        )

        # Verify cancellation successful
        assert success is True

        # Verify session status updated
        await async_db_session.refresh(session)
        assert session.status == "cancelled"
        assert session.cancelled_at is not None

    @patch("app.tasks.panic_notifications.notify_guardian_telegram.apply_async")
    @patch("app.tasks.panic_notifications.notify_guardian_voice.apply_async")
    @patch("app.tasks.panic_notifications.notify_guardian_sms.apply_async")
    @patch("app.tasks.panic_notifications.check_cycle_completion.apply_async")
    async def test_multiple_guardian_acknowledgments(
        self,
        mock_cycle_completion,
        mock_sms,
        mock_voice,
        mock_telegram,
        async_db_session,
        test_data,
    ):
        """Test handling multiple guardian acknowledgments."""

        # Setup mocks
        mock_telegram.return_value.id = "telegram_task_1"
        mock_voice.return_value.id = "voice_task_1"
        mock_sms.return_value.id = "sms_task_1"
        mock_cycle_completion.return_value.id = "completion_task_1"

        user = test_data["user"]
        guardians = test_data["guardians"]

        # Create panic service
        panic_service = PanicSessionService(async_db_session)

        # Start panic session
        session = await panic_service.start_panic_session(
            user_id=user.id, message="Multiple responders test"
        )

        # First guardian acknowledges
        result1 = await panic_service.handle_guardian_response(
            session_id=session.id,
            guardian_id=guardians[0].id,
            response_type="positive",
            response_method="telegram",
        )

        assert result1["status"] == "acknowledged"

        # Session should now be acknowledged
        await async_db_session.refresh(session)
        assert session.status == "acknowledged"
        assert session.acknowledged_by == guardians[0].id

        # Second guardian also tries to acknowledge (should still work but session already acknowledged)
        result2 = await panic_service.handle_guardian_response(
            session_id=session.id,
            guardian_id=guardians[1].id,
            response_type="positive",
            response_method="voice",
        )

        # Should handle gracefully (no double acknowledgment protection per requirements)
        assert result2["status"] == "acknowledged"

        # Verify both guardians recorded as acknowledged
        guardian1_status = next(
            gs for gs in session.guardian_statuses if gs.guardian_id == guardians[0].id
        )
        guardian2_status = next(
            gs for gs in session.guardian_statuses if gs.guardian_id == guardians[1].id
        )

        assert guardian1_status.status == "acknowledged"
        assert guardian2_status.status == "acknowledged"
