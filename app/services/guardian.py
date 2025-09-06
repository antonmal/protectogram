from typing import Optional, List
from uuid import UUID
import secrets
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guardian import Guardian
from app.schemas.guardian import GuardianCreate, GuardianUpdate


class GuardianService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, guardian_id: UUID) -> Optional[Guardian]:
        result = await self.db.execute(
            select(Guardian).where(Guardian.id == guardian_id)
        )
        return result.scalar_one_or_none()

    async def get_by_phone_number(self, phone_number: str) -> Optional[Guardian]:
        result = await self.db.execute(
            select(Guardian).where(Guardian.phone_number == phone_number)
        )
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_user_id: int) -> Optional[Guardian]:
        result = await self.db.execute(
            select(Guardian).where(Guardian.telegram_user_id == telegram_user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, guardian_data: GuardianCreate) -> Guardian:
        # Check if guardian with same phone number already exists
        existing_guardian = await self.get_by_phone_number(guardian_data.phone_number)
        if existing_guardian:
            raise ValueError(
                f"Guardian with phone number {guardian_data.phone_number} already exists"
            )

        # Check if telegram_user_id is already in use (if provided)
        if guardian_data.telegram_user_id:
            existing_telegram_guardian = await self.get_by_telegram_id(
                guardian_data.telegram_user_id
            )
            if existing_telegram_guardian:
                raise ValueError(
                    f"Guardian with Telegram ID {guardian_data.telegram_user_id} already exists"
                )

        guardian = Guardian(**guardian_data.model_dump())
        self.db.add(guardian)
        await self.db.commit()
        await self.db.refresh(guardian)
        return guardian

    async def update(
        self, guardian_id: UUID, guardian_data: GuardianUpdate
    ) -> Optional[Guardian]:
        guardian = await self.get_by_id(guardian_id)
        if not guardian:
            return None

        # Check for phone number conflicts
        if (
            guardian_data.phone_number
            and guardian_data.phone_number != guardian.phone_number
        ):
            existing_guardian = await self.get_by_phone_number(
                guardian_data.phone_number
            )
            if existing_guardian and existing_guardian.id != guardian_id:
                raise ValueError(
                    f"Guardian with phone number {guardian_data.phone_number} already exists"
                )

        # Check for telegram_user_id conflicts
        if (
            guardian_data.telegram_user_id
            and guardian_data.telegram_user_id != guardian.telegram_user_id
        ):
            existing_telegram_guardian = await self.get_by_telegram_id(
                guardian_data.telegram_user_id
            )
            if (
                existing_telegram_guardian
                and existing_telegram_guardian.id != guardian_id
            ):
                raise ValueError(
                    f"Guardian with Telegram ID {guardian_data.telegram_user_id} already exists"
                )

        update_data = guardian_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(guardian, field, value)

        await self.db.commit()
        await self.db.refresh(guardian)
        return guardian

    async def delete(self, guardian_id: UUID) -> bool:
        guardian = await self.get_by_id(guardian_id)
        if not guardian:
            return False

        await self.db.delete(guardian)
        await self.db.commit()
        return True

    async def list_guardians(self, skip: int = 0, limit: int = 100) -> List[Guardian]:
        query = select(Guardian).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_guardians(self) -> int:
        from sqlalchemy import func

        query = select(func.count(Guardian.id))
        result = await self.db.execute(query)
        return result.scalar()

    async def search_guardians(
        self, search_term: str, skip: int = 0, limit: int = 100
    ) -> List[Guardian]:
        """Search guardians by name or phone number."""
        query = (
            select(Guardian)
            .where(
                Guardian.name.ilike(f"%{search_term}%")
                | Guardian.phone_number.ilike(f"%{search_term}%")
            )
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def create_guardian_invitation(
        self, guardian_data: GuardianCreate, expires_in_days: int = 7
    ) -> Guardian:
        """
        Create a guardian with invitation token for registration.

        Args:
            guardian_data: Guardian creation data
            expires_in_days: Days until invitation expires

        Returns:
            Guardian with invitation token
        """
        # Generate unique invitation token
        invitation_token = secrets.token_urlsafe(32)

        # Set expiration date
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        # Create guardian with invitation fields
        guardian_dict = guardian_data.model_dump()
        guardian_dict.update(
            {
                "invitation_token": invitation_token,
                "invited_at": datetime.now(timezone.utc),
                "invitation_expires_at": expires_at,
                "verification_status": "pending",
                "consent_given": False,
            }
        )

        guardian = Guardian(**guardian_dict)
        self.db.add(guardian)
        await self.db.commit()
        await self.db.refresh(guardian)
        return guardian

    async def get_by_invitation_token(self, token: str) -> Optional[Guardian]:
        """Get guardian by invitation token."""
        result = await self.db.execute(
            select(Guardian).where(Guardian.invitation_token == token)
        )
        return result.scalar_one_or_none()
