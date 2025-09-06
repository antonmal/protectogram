#!/usr/bin/env python3
"""Local testing script for panic button functionality."""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config.settings import get_settings
from app.models import User, Guardian, UserGuardian, PanicAlert
from app.models.user import Gender
from app.services.panic_service import PanicAlertService


async def setup_test_data(db: AsyncSession):
    """Create test user and guardian data."""
    print("🔧 Setting up test data...")

    # Create test user
    test_user = User(
        telegram_user_id=12345678,
        telegram_username="testuser",
        first_name="Test",
        last_name="User",
        phone_number="+34722450504",  # Your number
        gender=Gender.MALE,
        preferred_language="en",
    )

    db.add(test_user)
    await db.flush()

    # Create test guardian (using your number for testing)
    test_guardian = Guardian(
        name="Test Guardian",
        phone_number="+34722450504",  # Your number for testing
        gender=Gender.MALE,
        # Note: No telegram_chat_id - will test graceful failure
    )

    db.add(test_guardian)
    await db.flush()

    # Link user and guardian
    user_guardian = UserGuardian(
        user_id=test_user.id, guardian_id=test_guardian.id, priority_order=1
    )

    db.add(user_guardian)
    await db.commit()

    print(f"✅ Created test user: {test_user.id}")
    print(f"✅ Created test guardian: {test_guardian.id}")

    return test_user, test_guardian


async def test_panic_trigger(db: AsyncSession, user: User):
    """Test panic alert trigger."""
    print("\n🚨 Testing panic alert trigger...")

    panic_service = PanicAlertService(db)

    alert = await panic_service.trigger_panic_alert(
        user_id=user.id,
        location="Test Location - Home",
        message="This is a test emergency alert",
    )

    print(f"✅ Panic alert created: {alert.id}")
    print(f"   Status: {alert.status}")
    print(f"   Location: {alert.location}")
    print(f"   Timeout: {alert.cascade_timeout_at}")

    return alert


async def test_panic_status(db: AsyncSession, user: User):
    """Test getting panic alert status."""
    print("\n📊 Testing panic alert status...")

    panic_service = PanicAlertService(db)

    alerts = await panic_service.get_user_alerts(user.id)

    print(f"✅ Found {len(alerts)} alerts for user")

    for alert in alerts:
        print(f"   Alert {alert.id}:")
        print(f"   - Status: {alert.status}")
        print(f"   - Created: {alert.created_at}")
        print(f"   - Attempts: {len(alert.notification_attempts)}")

        for attempt in alert.notification_attempts:
            print(f"     * {attempt.method}: {attempt.status}")
            if attempt.error_message:
                print(f"       Error: {attempt.error_message}")


async def test_panic_acknowledgment(
    db: AsyncSession, alert: PanicAlert, guardian: Guardian
):
    """Test panic alert acknowledgment."""
    print("\n✅ Testing panic acknowledgment...")

    panic_service = PanicAlertService(db)

    # Test positive acknowledgment
    success = await panic_service.acknowledge_alert(
        alert_id=alert.id, guardian_id=guardian.id, response="positive"
    )

    print(f"✅ Acknowledgment result: {success}")

    # Refresh alert to see changes
    await db.refresh(alert)
    print(f"   Alert status: {alert.status}")
    print(f"   Acknowledged at: {alert.acknowledged_at}")
    print(f"   Response: {alert.acknowledged_response}")


async def test_panic_resolve(db: AsyncSession, alert_id):
    """Test panic alert resolution."""
    print("\n🔧 Testing panic resolve...")

    panic_service = PanicAlertService(db)

    success = await panic_service.resolve_alert(alert_id)
    print(f"✅ Resolve result: {success}")


async def cleanup_test_data(db: AsyncSession, user: User, guardian: Guardian):
    """Clean up test data."""
    print("\n🧹 Cleaning up test data...")

    # Delete user (cascade will delete alerts, user_guardians)
    await db.delete(user)
    await db.delete(guardian)
    await db.commit()

    print("✅ Test data cleaned up")


async def main():
    """Run all local panic tests."""
    print("🧪 Starting Local Panic Button Tests")
    print("=" * 50)

    # Setup database connection
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        try:
            # Setup test data
            user, guardian = await setup_test_data(db)

            # Run tests
            alert = await test_panic_trigger(db, user)

            # Wait a moment for cascade to process
            print("\n⏳ Waiting 5 seconds for cascade processing...")
            await asyncio.sleep(5)

            await test_panic_status(db, user)

            # Test acknowledgment (uncomment if alert is still active)
            # await test_panic_acknowledgment(db, alert, guardian)

            # Test resolve
            await test_panic_resolve(db, alert.id)

            # Final status check
            await test_panic_status(db, user)

        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback

            traceback.print_exc()

        finally:
            # Cleanup
            try:
                await cleanup_test_data(db, user, guardian)
            except Exception as e:
                print(f"⚠️ Cleanup error: {e}")

    await engine.dispose()
    print("\n🎉 Local tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
