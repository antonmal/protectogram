#!/usr/bin/env python3
"""Test panic button with real Twilio voice calls."""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config.settings import get_settings
from app.models import (
    User,
    Guardian,
    UserGuardian,
    PanicAlert,
    PanicNotificationAttempt,
)
from app.models.user import Gender
from app.services.panic_service import PanicAlertService


async def cleanup_existing_test_data(db: AsyncSession):
    """Clean up any existing test data before running new test."""
    print("🧹 Cleaning up existing test data...")

    from sqlalchemy import select, delete

    try:
        # Find existing user
        user_query = select(User).where(User.telegram_user_id == 30865102)
        result = await db.execute(user_query)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            # Delete all notification attempts for this user's alerts
            attempts_query = (
                select(PanicNotificationAttempt)
                .join(PanicAlert)
                .where(PanicAlert.user_id == existing_user.id)
            )
            attempts_result = await db.execute(attempts_query)
            attempts = attempts_result.scalars().all()
            for attempt in attempts:
                await db.delete(attempt)
            print(f"✅ Deleted {len(attempts)} notification attempts")

            # Delete all panic alerts for this user
            alerts_query = select(PanicAlert).where(
                PanicAlert.user_id == existing_user.id
            )
            alerts_result = await db.execute(alerts_query)
            alerts = alerts_result.scalars().all()
            for alert in alerts:
                await db.delete(alert)
            print(f"✅ Deleted {len(alerts)} panic alerts")

            # Delete all user_guardians relationships
            user_guardians_result = await db.execute(
                delete(UserGuardian).where(UserGuardian.user_id == existing_user.id)
            )
            print(
                f"✅ Deleted {user_guardians_result.rowcount} user-guardian relationships"
            )

            # Delete test guardians (those with test phone number)
            test_guardians_result = await db.execute(
                delete(Guardian).where(Guardian.phone_number == "+34722450504")
            )
            print(f"✅ Deleted {test_guardians_result.rowcount} test guardians")

            await db.commit()
            print("✅ Cleanup completed successfully")
        else:
            print("✅ No existing test data found")

    except Exception as e:
        print(f"⚠️ Error during cleanup: {e}")
        await db.rollback()


async def setup_real_test_data(db: AsyncSession):
    """Create test user and guardian with your real phone number."""
    print("🔧 Setting up real test data...")

    from sqlalchemy import select

    # Try to find existing user first
    user_query = select(User).where(User.telegram_user_id == 30865102)
    result = await db.execute(user_query)
    test_user = result.scalar_one_or_none()

    if test_user:
        print(f"✅ Found existing user: {test_user.id} ({test_user.first_name})")
    else:
        # Create test user (you)
        test_user = User(
            telegram_user_id=30865102,  # Your actual Telegram ID
            telegram_username="amalkov",
            first_name="Anton",
            last_name="Malkov",
            phone_number="+34722450504",  # Your number
            gender=Gender.MALE,
            preferred_language="en",
        )

        db.add(test_user)
        await db.flush()
        print(f"✅ Created new user: {test_user.id} (Anton)")

    # Create test guardian (also you, for testing)
    test_guardian = Guardian(
        name="Anton Malkov (Guardian)",
        phone_number="+34722450504",  # Your number - will receive the call
        gender=Gender.MALE,
        # Note: No telegram_chat_id - will test graceful failure for Telegram
    )

    db.add(test_guardian)
    await db.flush()

    # Link user and guardian
    user_guardian = UserGuardian(
        user_id=test_user.id, guardian_id=test_guardian.id, priority_order=1
    )

    db.add(user_guardian)
    await db.commit()

    print(f"✅ Created test user: {test_user.id} (Anton)")
    print(f"✅ Created test guardian: {test_guardian.id} (Your phone: +34722450504)")
    print("📞 Guardian will receive REAL voice call!")

    return test_user, test_guardian


async def trigger_real_panic_alert(db: AsyncSession, user: User):
    """Trigger panic alert with real Twilio calls."""
    print("\n🚨 TRIGGERING REAL PANIC ALERT!")
    print("📞 You should receive a voice call on +34722450504")
    print("🎯 During the call, press:")
    print("   - Press 1 = Acknowledge emergency (positive)")
    print("   - Press 9 = False alarm (negative)")
    print("   - No response = Call will timeout")

    # Auto-proceed for testing
    print("\n⚠️  PROCEEDING WITH REAL PHONE CALL...")

    panic_service = PanicAlertService(db)

    alert = await panic_service.trigger_panic_alert(
        user_id=user.id,
        location="Test Location - Local Development",
        message="TEST: Real Twilio voice call integration test",
    )

    print(f"\n✅ Panic alert created: {alert.id}")
    print(f"   Status: {alert.status}")
    print(f"   Location: {alert.location}")
    print(f"   Timeout: {alert.cascade_timeout_at}")
    print("\n📞 Voice call should be starting now...")
    print("🔄 Cascade will continue for 15 minutes unless acknowledged")

    return alert


async def monitor_alert_progress(db: AsyncSession, alert: PanicAlert, user: User):
    """Monitor the alert and show real-time updates."""
    print(f"\n👀 Monitoring alert {alert.id}...")
    print("Press Ctrl+C to stop monitoring\n")

    panic_service = PanicAlertService(db)

    try:
        for i in range(20):  # Monitor for ~2 minutes
            alerts = await panic_service.get_user_alerts(user.id, limit=1)
            if not alerts:
                print("❌ Alert not found")
                break

            current_alert = alerts[0]
            attempts = current_alert.notification_attempts

            print(
                f"⏱️  {datetime.now().strftime('%H:%M:%S')} - Status: {current_alert.status.upper()}"
            )

            if attempts:
                latest_attempt = max(attempts, key=lambda a: a.sent_at)
                print(
                    f"   📞 Latest: {latest_attempt.method} -> {latest_attempt.status}"
                )
                if latest_attempt.error_message:
                    print(f"   ❌ Error: {latest_attempt.error_message}")

            # Check if acknowledged
            if current_alert.status == "acknowledged":
                print("\n✅ ALERT ACKNOWLEDGED!")
                print(f"   👤 Response: {current_alert.acknowledged_response}")
                print(f"   ⏰ Time: {current_alert.acknowledged_at}")
                break
            elif current_alert.status in ["resolved", "timeout"]:
                print(f"\n🔚 Alert ended with status: {current_alert.status}")
                break

            await asyncio.sleep(6)  # Check every 6 seconds

    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped by user")


async def cleanup_test_data(db: AsyncSession, user: User, guardian: Guardian):
    """Clean up test data."""
    print("\n🧹 Cleaning up test data...")

    # Delete user (cascade will delete alerts, user_guardians)
    await db.delete(user)
    await db.delete(guardian)
    await db.commit()

    print("✅ Test data cleaned up")


async def main():
    """Run real Twilio panic test."""
    print("📞 REAL TWILIO PANIC BUTTON TEST")
    print("=" * 50)
    print("⚠️  This will make REAL voice calls to +34722450504")
    print("🎯 Test DTMF responses during the call")
    print("📊 Monitor webhook callbacks in real-time")

    # Setup database connection
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        try:
            # Clean up any existing test data first
            await cleanup_existing_test_data(db)

            # Setup test data
            user, guardian = await setup_real_test_data(db)

            # Trigger real panic alert
            alert = await trigger_real_panic_alert(db, user)

            if alert:
                # Monitor progress
                await monitor_alert_progress(db, alert, user)

        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback

            traceback.print_exc()

        finally:
            # Cleanup
            try:
                if "user" in locals() and "guardian" in locals():
                    await cleanup_test_data(db, user, guardian)
            except Exception as e:
                print(f"⚠️ Cleanup error: {e}")

    await engine.dispose()
    print("\n🎉 Real Twilio test completed!")
    print("🔍 Check server logs for webhook activity")


if __name__ == "__main__":
    asyncio.run(main())
