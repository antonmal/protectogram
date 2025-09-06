#!/usr/bin/env python3
"""Test script for guardian invitation system."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import AsyncSessionLocal
from app.services.guardian import GuardianService
from app.services.telegram_onboarding import TelegramOnboardingService
from app.services.user import UserService
from app.services.user_guardian import UserGuardianService
from app.schemas.guardian import GuardianCreate
from app.schemas.user import UserCreate
from app.models.user import Gender


async def test_guardian_invitation():
    """Test the complete guardian invitation flow."""
    print("🧪 Testing Guardian Invitation System\n")

    async with AsyncSessionLocal() as db:
        # Initialize services
        guardian_service = GuardianService(db=db)
        user_service = UserService(db=db)
        user_guardian_service = UserGuardianService(db=db)
        telegram_service = TelegramOnboardingService(
            db=db,
            user_service=user_service,
            guardian_service=guardian_service,
            user_guardian_service=user_guardian_service,
        )

        try:
            # Step 1: Create a test user first
            print("1️⃣ Creating test user...")
            test_user_data = UserCreate(
                telegram_user_id=12345,
                telegram_username="testuser",
                first_name="Test",
                last_name="User",
                phone_number="+1234567890",
                gender=Gender.OTHER,
                preferred_language="en",
            )

            # Check if user exists first
            existing_user = await user_service.get_by_telegram_id(12345)
            if existing_user:
                print(f"   ✅ Using existing test user: {existing_user.first_name}")
                test_user = existing_user
            else:
                test_user = await user_service.create(test_user_data)
                print(
                    f"   ✅ Created test user: {test_user.first_name} ({test_user.id})"
                )

            # Step 2: Create guardian invitation
            print("\n2️⃣ Creating guardian invitation...")
            guardian_data = GuardianCreate(
                phone_number="+9876543210",
                name="Test Guardian",
                gender=Gender.OTHER,
            )

            guardian = await guardian_service.create_guardian_invitation(guardian_data)
            print(f"   ✅ Created guardian invitation: {guardian.name}")
            print(f"   🔑 Invitation token: {guardian.invitation_token[:20]}...")
            print(f"   📅 Expires: {guardian.invitation_expires_at}")

            # Step 3: Test Telegram registration flow
            print("\n3️⃣ Testing Telegram registration flow...")

            # Simulate starting registration
            registration_result = await telegram_service.start_guardian_registration(
                telegram_user_id=67890,
                telegram_chat_id=67890,
                telegram_username="testguardian",
                telegram_first_name="Test",
                telegram_last_name="Guardian",
                registration_token=guardian.invitation_token,
            )

            print(f"   📱 Registration start result: {registration_result['status']}")
            if registration_result["status"] == "success":
                print(f"   👤 Guardian: {registration_result['guardian']['name']}")
                print(f"   👥 Invited by: {registration_result['user']['name']}")

            # Step 4: Test acceptance
            print("\n4️⃣ Testing guardian acceptance...")
            acceptance_result = await telegram_service.accept_guardian_registration(
                registration_token=guardian.invitation_token, telegram_user_id=67890
            )

            print(f"   ✅ Acceptance result: {acceptance_result['status']}")
            if acceptance_result["status"] == "success":
                print(
                    f"   🔒 Verification status: {acceptance_result['verification_status']}"
                )

            # Step 5: Link guardian to user
            print("\n5️⃣ Linking guardian to user...")
            from app.schemas.user_guardian import UserGuardianCreate

            link_data = UserGuardianCreate(guardian_id=guardian.id, priority_order=1)

            user_guardian = await user_guardian_service.add_guardian_to_user(
                test_user.id, link_data
            )
            print(
                f"   🔗 Linked guardian to user with priority {user_guardian.priority_order}"
            )

            # Step 6: Test getting user's guardians
            print("\n6️⃣ Testing guardian retrieval...")
            guardians_list = await telegram_service.get_user_guardians_from_telegram(
                12345
            )
            print(f"   📋 User has {len(guardians_list)} guardians:")
            for g in guardians_list:
                print(f"      - {g['name']} ({g['phone']}) - Priority {g['priority']}")

            print("\n✅ Guardian invitation system test completed successfully!")
            print(
                f"🎯 Guardian {guardian.name} is now registered and linked to user {test_user.first_name}"
            )

        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            raise
        finally:
            # Cleanup: Remove test data
            print("\n🧹 Cleaning up test data...")
            try:
                if "guardian" in locals():
                    await guardian_service.delete(guardian.id)
                    print("   🗑️ Removed test guardian")
                if "test_user" in locals() and not existing_user:
                    await user_service.delete(test_user.id)
                    print("   🗑️ Removed test user")
            except Exception as cleanup_error:
                print(f"   ⚠️ Cleanup error: {cleanup_error}")


if __name__ == "__main__":
    asyncio.run(test_guardian_invitation())
