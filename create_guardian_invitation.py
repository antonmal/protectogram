#!/usr/bin/env python3
"""Create a guardian invitation for your account."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from app.database import AsyncSessionLocal
from app.services.guardian import GuardianService
from app.services.user import UserService
from app.services.user_guardian import UserGuardianService
from app.schemas.guardian import GuardianCreate
from app.schemas.user_guardian import UserGuardianCreate
from app.models.user import Gender


async def create_invitation():
    print("🛡️ **CREATE GUARDIAN INVITATION**\n")

    # Get guardian info
    guardian_name = input("Enter guardian's name (e.g., 'Mom', 'John Smith'): ")
    guardian_phone = input("Enter guardian's phone number (with +): ")

    print("\n🔍 Looking for your user account...")

    async with AsyncSessionLocal() as db:
        user_service = UserService(db=db)
        guardian_service = GuardianService(db=db)
        user_guardian_service = UserGuardianService(db=db)

        # Find your user (we'll get the latest one)
        users = await user_service.list_users(limit=10)
        if not users:
            print("❌ No users found! Please register first.")
            return

        user = users[-1]  # Get the most recent user
        print(f"✅ Found user: {user.first_name} {user.last_name or ''}")
        print(f"   📱 Telegram: @{user.telegram_username} ({user.telegram_user_id})")

        # Create guardian invitation
        guardian_data = GuardianCreate(
            phone_number=guardian_phone,
            name=guardian_name,
            gender=Gender.OTHER,  # Default
        )

        print(f"\n🎯 Creating invitation for {guardian_name}...")
        guardian = await guardian_service.create_guardian_invitation(guardian_data)

        # Link to your user
        link_data = UserGuardianCreate(guardian_id=guardian.id, priority_order=1)
        await user_guardian_service.add_guardian_to_user(user.id, link_data)

        # Generate invitation link
        invitation_link = f"https://t.me/ProtectogramDevBot?start=guardian_{guardian.invitation_token}"

        print("✅ Guardian invitation created!")
        print("\n📱 **SEND THIS LINK TO YOUR GUARDIAN:**")
        print(f"🔗 {invitation_link}")
        print(f"\n🔑 Token: {guardian.invitation_token}")
        print(f"⏰ Expires: {guardian.invitation_expires_at}")
        print(f"👤 Guardian: {guardian.name} ({guardian.phone_number})")

        return guardian.invitation_token


if __name__ == "__main__":
    asyncio.run(create_invitation())
