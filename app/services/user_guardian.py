from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.guardian import Guardian
from app.models.user import User
from app.models.user_guardian import UserGuardian
from app.schemas.user_guardian import UserGuardianCreate, UserGuardianUpdate


class UserGuardianService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_guardian_to_user(
        self, user_id: UUID, guardian_data: UserGuardianCreate
    ) -> UserGuardian:
        # Check if user exists
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        if not user_result.scalar_one_or_none():
            raise ValueError("User not found")

        # Check if guardian exists
        guardian_result = await self.db.execute(
            select(Guardian).where(Guardian.id == guardian_data.guardian_id)
        )
        if not guardian_result.scalar_one_or_none():
            raise ValueError("Guardian not found")

        # Check if relationship already exists
        existing_result = await self.db.execute(
            select(UserGuardian).where(
                and_(
                    UserGuardian.user_id == user_id,
                    UserGuardian.guardian_id == guardian_data.guardian_id,
                )
            )
        )
        if existing_result.scalar_one_or_none():
            raise ValueError("Guardian already linked to this user")

        # Check for priority conflicts and adjust if needed
        await self._ensure_unique_priority(user_id, guardian_data.priority_order)

        # Create the relationship
        user_guardian = UserGuardian(
            user_id=user_id,
            guardian_id=guardian_data.guardian_id,
            priority_order=guardian_data.priority_order,
        )

        self.db.add(user_guardian)
        await self.db.commit()
        await self.db.refresh(user_guardian)
        return user_guardian

    async def remove_guardian_from_user(self, user_id: UUID, guardian_id: UUID) -> bool:
        # Find the relationship
        result = await self.db.execute(
            select(UserGuardian).where(
                and_(
                    UserGuardian.user_id == user_id,
                    UserGuardian.guardian_id == guardian_id,
                )
            )
        )
        user_guardian = result.scalar_one_or_none()

        if not user_guardian:
            return False

        await self.db.delete(user_guardian)
        await self.db.commit()

        # Reorder remaining guardians
        await self._reorder_priorities(user_id)
        return True

    async def update_guardian_priority(
        self, user_id: UUID, guardian_id: UUID, update_data: UserGuardianUpdate
    ) -> Optional[UserGuardian]:
        # Find the relationship
        result = await self.db.execute(
            select(UserGuardian).where(
                and_(
                    UserGuardian.user_id == user_id,
                    UserGuardian.guardian_id == guardian_id,
                )
            )
        )
        user_guardian = result.scalar_one_or_none()

        if not user_guardian:
            return None

        # Ensure unique priority by adjusting others
        await self._ensure_unique_priority(
            user_id, update_data.priority_order, exclude_id=user_guardian.id
        )

        # Update the priority
        user_guardian.priority_order = update_data.priority_order
        await self.db.commit()
        await self.db.refresh(user_guardian)
        return user_guardian

    async def get_user_guardians(self, user_id: UUID) -> List[UserGuardian]:
        """Get all guardians for a user, ordered by priority."""
        result = await self.db.execute(
            select(UserGuardian)
            .options(selectinload(UserGuardian.guardian))
            .where(UserGuardian.user_id == user_id)
            .order_by(UserGuardian.priority_order)
        )
        return list(result.scalars().all())

    async def count_user_guardians(self, user_id: UUID) -> int:
        from sqlalchemy import func

        result = await self.db.execute(
            select(func.count(UserGuardian.id)).where(UserGuardian.user_id == user_id)
        )
        return result.scalar() or 0

    async def get_guardian_users(self, guardian_id: UUID) -> List[UserGuardian]:
        """Get all users linked to a guardian."""
        result = await self.db.execute(
            select(UserGuardian)
            .options(selectinload(UserGuardian.user))
            .where(UserGuardian.guardian_id == guardian_id)
            .order_by(UserGuardian.priority_order)
        )
        return list(result.scalars().all())

    async def _ensure_unique_priority(
        self, user_id: UUID, target_priority: int, exclude_id: Optional[UUID] = None
    ):
        """Ensure priority is unique by shifting conflicting guardians."""
        # Find existing guardian with same priority
        query = select(UserGuardian).where(
            and_(
                UserGuardian.user_id == user_id,
                UserGuardian.priority_order >= target_priority,
            )
        )

        if exclude_id:
            query = query.where(UserGuardian.id != exclude_id)

        result = await self.db.execute(query.order_by(UserGuardian.priority_order))
        conflicting_guardians = result.scalars().all()

        # Shift priorities up for all guardians at or above target priority
        for guardian in conflicting_guardians:
            guardian.priority_order += 1

    async def _reorder_priorities(self, user_id: UUID):
        """Reorder priorities to remove gaps (1, 2, 3, ...)."""
        result = await self.db.execute(
            select(UserGuardian)
            .where(UserGuardian.user_id == user_id)
            .order_by(UserGuardian.priority_order)
        )
        guardians = result.scalars().all()

        for i, guardian in enumerate(guardians, 1):
            guardian.priority_order = i

        await self.db.commit()
