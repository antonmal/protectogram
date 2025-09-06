#!/usr/bin/env python3
"""Register yourself as a user via your Telegram interaction."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from app.database import AsyncSessionLocal
from app.services.user import UserService
from app.schemas.user import UserCreate
from app.models.user import Gender


async def register_user():
    print("👤 **USER REGISTRATION**\n")

    # Get your info
    telegram_id = input("Enter your Telegram user ID (get from @userinfobot): ")
    username = input("Enter your Telegram username (without @): ")
    first_name = input("Enter your first name: ")
    last_name = input("Enter your last name (optional): ") or None
    phone = input("Enter your phone number (with +): ")

    print("\n🎯 Creating your user account...")

    async with AsyncSessionLocal() as db:
        user_service = UserService(db=db)

        user_data = UserCreate(
            telegram_user_id=int(telegram_id),
            telegram_username=username,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone,
            gender=Gender.OTHER,  # Default
            preferred_language="en",
        )

        try:
            user = await user_service.create(user_data)
            print(f"✅ User created: {user.first_name} (ID: {user.id})")
            print(f"📱 Telegram: @{user.telegram_username} ({user.telegram_user_id})")
            print("\n🎉 You can now proceed with the guardian invitation!")
            return user
        except ValueError as e:
            print(f"❌ Error: {e}")
            return None


if __name__ == "__main__":
    asyncio.run(register_user())
