#!/usr/bin/env python3
"""Test Telegram bot guardian onboarding locally with ngrok."""

import asyncio
import requests
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import AsyncSessionLocal
from app.services.guardian import GuardianService
from app.services.user import UserService
from app.services.user_guardian import UserGuardianService
from app.schemas.guardian import GuardianCreate
from app.schemas.user import UserCreate
from app.schemas.user_guardian import UserGuardianCreate
from app.models.user import Gender


async def create_test_invitation():
    """Create a test guardian invitation and return the link."""
    print("🎯 Creating Guardian Invitation for Telegram Testing\n")

    async with AsyncSessionLocal() as db:
        # Initialize services
        guardian_service = GuardianService(db=db)
        user_service = UserService(db=db)
        user_guardian_service = UserGuardianService(db=db)

        try:
            # Step 1: Ensure we have a test user
            print("1️⃣ Setting up test user...")
            existing_user = await user_service.get_by_telegram_id(12345)
            if not existing_user:
                test_user_data = UserCreate(
                    telegram_user_id=12345,
                    telegram_username="testuser",
                    first_name="Test",
                    last_name="User",
                    phone_number="+1234567890",
                    gender=Gender.OTHER,
                    preferred_language="en",
                )
                test_user = await user_service.create(test_user_data)
                print(f"   ✅ Created test user: {test_user.first_name}")
            else:
                test_user = existing_user
                print(f"   ✅ Using existing test user: {test_user.first_name}")

            # Step 2: Create guardian invitation
            print("2️⃣ Creating guardian invitation...")
            guardian_data = GuardianCreate(
                phone_number="+9876543210",
                name="Mom (Test Guardian)",
                gender=Gender.OTHER,
            )

            guardian = await guardian_service.create_guardian_invitation(guardian_data)

            # Step 3: Link guardian to user (IMPORTANT: This must happen before registration)
            print("3️⃣ Linking guardian to user...")
            link_data = UserGuardianCreate(guardian_id=guardian.id, priority_order=1)
            await user_guardian_service.add_guardian_to_user(test_user.id, link_data)

            print("✅ Guardian invitation created successfully!\n")
            print("📱 **TEST INVITATION LINK:**")
            print(
                f"https://t.me/protectogram_bot?start=guardian_{guardian.invitation_token}"
            )
            print(f"\n🔑 **Token:** {guardian.invitation_token}")
            print(f"⏰ **Expires:** {guardian.invitation_expires_at}")
            print(f"👤 **Guardian:** {guardian.name} ({guardian.phone_number})")
            print(
                f"👥 **Invited by:** {test_user.first_name} {test_user.last_name or ''}"
            )

            return guardian.invitation_token, guardian.id

        except Exception as e:
            print(f"❌ Error creating invitation: {e}")
            return None, None


async def cleanup_test_guardian(guardian_id):
    """Clean up test guardian."""
    if not guardian_id:
        return

    async with AsyncSessionLocal() as db:
        guardian_service = GuardianService(db=db)
        try:
            await guardian_service.delete(guardian_id)
            print("🧹 Cleaned up test guardian")
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")


def test_webhook_endpoints():
    """Test webhook endpoints are working."""
    print("\n🔧 Testing webhook endpoints...")

    base_url = "http://localhost:8000"

    # Test health check
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ Health check endpoint working")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        return False

    # Test Telegram webhook health
    try:
        response = requests.get(f"{base_url}/webhooks/telegram/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ Telegram webhook endpoint working")
            return True
        else:
            print(f"   ❌ Telegram webhook failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Telegram webhook error: {e}")
        return False


def show_testing_instructions(token):
    """Show step-by-step testing instructions."""
    print("\n" + "=" * 60)
    print("📋 **TELEGRAM BOT TESTING INSTRUCTIONS**")
    print("=" * 60)

    print("\n**PREREQUISITES:**")
    print("1. Your Telegram bot must be running (check console for bot initialization)")
    print("2. You need the bot's @username (check .env file)")
    print("3. If testing locally, you need ngrok or webhook setup")

    print("\n**TEST STEPS:**")
    print("1. Open Telegram and click this link:")
    print(f"   https://t.me/your_bot_username?start=guardian_{token}")
    print("\n2. You should see:")
    print("   🛡️ Guardian Registration")
    print("   Test User has added you as their emergency contact...")
    print("   [✅ Yes, I accept] [❌ No, decline]")
    print("\n3. Click 'Yes, I accept' to test acceptance flow")
    print("4. Click 'No, decline' to test decline flow")

    print("\n**WEBHOOK SETUP (if testing locally):**")
    print("1. Install ngrok: https://ngrok.com/")
    print("2. Run: ngrok http 8000")
    print("3. Set webhook: POST http://localhost:8000/webhooks/telegram/set-webhook")
    print(
        '   {"webhook_url": "https://your-ngrok-url.ngrok-free.app/webhooks/telegram/webhook"}'
    )

    print("\n**DEBUGGING:**")
    print("• Check app console for Telegram bot initialization messages")
    print("• Check webhook logs for incoming updates")
    print("• Use /webhooks/telegram/test-start-command for handler testing")

    print("\n**CLEANUP:**")
    print("• This script will automatically clean up the test guardian when done")
    print("=" * 60)


async def main():
    """Main test orchestration."""
    print("🧪 **TELEGRAM BOT GUARDIAN ONBOARDING TESTER**\n")

    # Step 1: Test if server is running
    if not test_webhook_endpoints():
        print("❌ Server not running or webhook endpoints not working")
        print(
            "💡 Start the server first: ./venv/bin/python -m uvicorn app.main:app --reload"
        )
        return

    # Step 2: Create test invitation
    token, guardian_id = await create_test_invitation()
    if not token:
        print("❌ Failed to create test invitation")
        return

    # Step 3: Show testing instructions
    show_testing_instructions(token)

    # Step 4: Wait for user input
    print("\n⏳ **READY FOR TESTING**")
    print("Press Enter when you're done testing (this will clean up the test data)...")
    input()

    # Step 5: Cleanup
    await cleanup_test_guardian(guardian_id)
    print("✅ Testing session complete!")


if __name__ == "__main__":
    asyncio.run(main())
