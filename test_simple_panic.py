#!/usr/bin/env python3
"""Simple panic test to debug issues."""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config.settings import get_settings
from app.providers.twilio_provider import TwilioCommunicationProvider
from app.models import Guardian, PanicAlert, User
from app.models.user import Gender


async def test_twilio_directly():
    """Test Twilio provider directly."""
    print("🧪 Testing Twilio Provider Directly")
    print("=" * 40)

    settings = get_settings()
    print(f"✅ Twilio Account SID: {settings.twilio_account_sid}")
    print(f"✅ Twilio From Number: {settings.twilio_from_number}")
    print(f"✅ Webhook Base URL: {settings.webhook_base_url}")

    # Create mock objects
    user = User(
        telegram_user_id=30865102,
        first_name="Anton",
        phone_number="+34722450504",
        gender=Gender.MALE,
    )

    guardian = Guardian(
        name="Test Guardian", phone_number="+34722450504", gender=Gender.MALE
    )

    panic_alert = PanicAlert(
        user_id=user.id, location="Test Location", message="Test panic alert"
    )
    panic_alert.user = user  # Set relationship

    # Test Twilio provider
    provider = TwilioCommunicationProvider(settings)

    print(f"\n📞 Making test voice call to {guardian.phone_number}...")

    try:
        result = await provider.make_voice_call(
            guardian, panic_alert, user.phone_number
        )
        print(f"✅ Call result: {result.result}")
        print(f"   Provider ID: {result.provider_id}")
        print(f"   Error: {result.error_message}")

        if result.result.value == "sent":
            print("🎉 SUCCESS! Voice call initiated!")
            print(f"📞 You should receive a call on {guardian.phone_number}")
        else:
            print("❌ FAILED! Call was not successful")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_twilio_directly())
