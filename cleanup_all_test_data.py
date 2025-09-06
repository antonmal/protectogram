#!/usr/bin/env python3
"""Clean up all test data including guardians and user_guardians."""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import delete

from app.config.settings import get_settings
from app.models import PanicAlert, PanicNotificationAttempt, Guardian, UserGuardian


async def cleanup_all_test_data():
    """Clean up all test data."""
    print("🧹 Cleaning up ALL test data...")

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        try:
            # Delete all notification attempts first (foreign key constraint)
            attempts_result = await db.execute(delete(PanicNotificationAttempt))
            print(f"✅ Deleted {attempts_result.rowcount} notification attempts")

            # Delete all panic alerts
            alerts_result = await db.execute(delete(PanicAlert))
            print(f"✅ Deleted {alerts_result.rowcount} panic alerts")

            # Delete all user_guardians relationships
            user_guardians_result = await db.execute(delete(UserGuardian))
            print(
                f"✅ Deleted {user_guardians_result.rowcount} user-guardian relationships"
            )

            # Delete test guardians (those with test phone number)
            test_guardians_result = await db.execute(
                delete(Guardian).where(Guardian.phone_number == "+34722450504")
            )
            print(f"✅ Deleted {test_guardians_result.rowcount} test guardians")

            await db.commit()
            print("✅ All test data cleaned up successfully")

        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            await db.rollback()
            raise

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(cleanup_all_test_data())
