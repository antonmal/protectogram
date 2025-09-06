#!/usr/bin/env python3
"""Clean up existing panic alerts for testing."""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import delete

from app.config.settings import get_settings
from app.models import PanicAlert, PanicNotificationAttempt


async def cleanup_panic_alerts():
    """Clean up all existing panic alerts and attempts."""
    print("🧹 Cleaning up existing panic alerts...")

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

            await db.commit()
            print("✅ All panic alert data cleaned up successfully")

        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            await db.rollback()
            raise

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(cleanup_panic_alerts())
