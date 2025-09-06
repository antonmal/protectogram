"""Telegram bot onboarding service that integrates with existing User and Guardian APIs."""

import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guardian import Guardian
from app.models.user import Gender, User
from app.models.user_guardian import UserGuardian
from app.schemas.user import UserCreate, UserResponse
from app.schemas.guardian import GuardianCreate, GuardianResponse
from app.schemas.user_guardian import UserGuardianCreate
from app.services.user import UserService
from app.services.guardian import GuardianService
from app.services.user_guardian import UserGuardianService

logger = logging.getLogger(__name__)


class TelegramOnboardingService:
    """Service for handling Telegram bot user onboarding and account management."""

    def __init__(
        self,
        db: AsyncSession,
        user_service: UserService,
        guardian_service: GuardianService,
        user_guardian_service: UserGuardianService,
    ):
        self.db = db
        self.user_service = user_service
        self.guardian_service = guardian_service
        self.user_guardian_service = user_guardian_service

    async def register_user_from_telegram(
        self,
        telegram_user_id: int,
        first_name: str,
        last_name: Optional[str],
        username: Optional[str],
        phone_number: str,
        gender: str,
        language: str = "en",
    ) -> UserResponse:
        """
        Register a new user from Telegram bot interaction.

        Args:
            telegram_user_id: Telegram user ID
            first_name: User's first name from Telegram
            last_name: User's last name from Telegram (optional)
            username: Telegram username (optional)
            phone_number: Phone number (validated)
            gender: User's gender (male, female, other)
            language: Preferred language code

        Returns:
            UserResponse: Created user data

        Raises:
            ValueError: If user already exists or validation fails
        """
        try:
            # Check if user already exists
            existing_user = await self.user_service.get_by_telegram_id(telegram_user_id)
            if existing_user:
                raise ValueError(
                    f"User with Telegram ID {telegram_user_id} already registered"
                )

            # Validate gender
            try:
                gender_enum = Gender(gender.lower())
            except ValueError:
                raise ValueError(
                    f"Invalid gender: {gender}. Must be 'male', 'female', or 'other'"
                )

            # Create user data
            user_data = UserCreate(
                telegram_user_id=telegram_user_id,
                telegram_username=username,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                gender=gender_enum,
                preferred_language=language,
            )

            # Create user account
            user = await self.user_service.create(user_data)
            logger.info(
                f"Created new user from Telegram: {user.id} (telegram_id: {telegram_user_id})"
            )

            return UserResponse.model_validate(user)

        except Exception as e:
            logger.error(
                f"Failed to register user from Telegram {telegram_user_id}: {e}"
            )
            raise

    async def get_user_by_telegram_id(
        self, telegram_user_id: int
    ) -> Optional[UserResponse]:
        """Get user by Telegram ID."""
        try:
            user = await self.user_service.get_by_telegram_id(telegram_user_id)
            if user:
                return UserResponse.model_validate(user)
            return None
        except Exception as e:
            logger.error(f"Failed to get user by telegram ID {telegram_user_id}: {e}")
            return None

    async def create_guardian_from_telegram(
        self,
        user_telegram_id: int,
        guardian_name: str,
        guardian_phone: str,
        guardian_telegram_id: Optional[int] = None,
        guardian_gender: str = "other",
        priority_order: int = 1,
    ) -> Dict[str, Any]:
        """
        Create a guardian and link to user from Telegram bot interaction.

        Args:
            user_telegram_id: Telegram ID of the user adding guardian
            guardian_name: Guardian's full name
            guardian_phone: Guardian's phone number
            guardian_telegram_id: Guardian's Telegram ID (optional)
            guardian_gender: Guardian's gender
            priority_order: Priority order for alerts

        Returns:
            Dict with guardian and linking information
        """
        try:
            # Get the user
            user = await self.user_service.get_by_telegram_id(user_telegram_id)
            if not user:
                raise ValueError(f"User with Telegram ID {user_telegram_id} not found")

            # Validate gender
            try:
                gender_enum = Gender(guardian_gender.lower())
            except ValueError:
                gender_enum = Gender.other  # Default fallback

            # Generate invitation token and expiration (7 days from now)
            invitation_token = secrets.token_urlsafe(32)
            invitation_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            invited_at = datetime.now(timezone.utc)

            # Create guardian data with invitation fields
            guardian_data = GuardianCreate(
                telegram_user_id=guardian_telegram_id,
                phone_number=guardian_phone,
                name=guardian_name,
                gender=gender_enum,
                invitation_token=invitation_token,
                invited_at=invited_at,
                invitation_expires_at=invitation_expires_at,
                verification_status="pending",
                consent_given=False,
            )

            # Create guardian
            guardian = await self.guardian_service.create(guardian_data)
            logger.info(f"Created guardian: {guardian.id} for user {user.id}")

            # Link guardian to user with priority
            link_data = UserGuardianCreate(
                guardian_id=guardian.id, priority_order=priority_order
            )

            user_guardian = await self.user_guardian_service.add_guardian_to_user(
                user.id, link_data
            )

            logger.info(
                f"Linked guardian {guardian.id} to user {user.id} with priority {priority_order}"
            )

            return {
                "guardian": GuardianResponse.model_validate(guardian),
                "user_guardian_id": user_guardian.id,
                "priority_order": user_guardian.priority_order,
                "success": True,
                "message": f"Guardian '{guardian_name}' added successfully with priority {priority_order}",
            }

        except Exception as e:
            logger.error(f"Failed to create guardian for user {user_telegram_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to add guardian: {str(e)}",
            }

    async def get_user_guardians_from_telegram(
        self, telegram_user_id: int
    ) -> List[Dict[str, Any]]:
        """Get user's guardians for display in Telegram bot."""
        try:
            user = await self.user_service.get_by_telegram_id(telegram_user_id)
            if not user:
                return []

            user_guardians = await self.user_guardian_service.get_user_guardians(
                user.id
            )

            guardian_list = []
            for ug in user_guardians:
                guardian_list.append(
                    {
                        "id": str(ug.guardian.id),
                        "name": ug.guardian.name,
                        "phone": ug.guardian.phone_number,
                        "telegram_id": ug.guardian.telegram_user_id,
                        "priority": ug.priority_order,
                        "created_at": ug.created_at.isoformat(),
                    }
                )

            return guardian_list

        except Exception as e:
            logger.error(f"Failed to get guardians for user {telegram_user_id}: {e}")
            return []

    async def remove_guardian_from_telegram(
        self, user_telegram_id: int, guardian_id: str
    ) -> Dict[str, Any]:
        """Remove a guardian from user's list via Telegram bot."""
        try:
            user = await self.user_service.get_by_telegram_id(user_telegram_id)
            if not user:
                raise ValueError("User not found")

            guardian_uuid = UUID(guardian_id)
            success = await self.user_guardian_service.remove_guardian_from_user(
                user.id, guardian_uuid
            )

            if success:
                logger.info(f"Removed guardian {guardian_id} from user {user.id}")
                return {"success": True, "message": "Guardian removed successfully"}
            else:
                return {
                    "success": False,
                    "message": "Guardian not found or already removed",
                }

        except Exception as e:
            logger.error(
                f"Failed to remove guardian {guardian_id} for user {user_telegram_id}: {e}"
            )
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to remove guardian: {str(e)}",
            }

    async def get_user_profile_for_telegram(
        self, telegram_user_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get user profile data formatted for Telegram display."""
        try:
            user = await self.user_service.get_by_telegram_id(telegram_user_id)
            if not user:
                return None

            guardian_count = await self.user_guardian_service.count_user_guardians(
                user.id
            )

            return {
                "id": str(user.id),
                "name": f"{user.first_name} {user.last_name or ''}".strip(),
                "telegram_id": user.telegram_user_id,
                "telegram_username": user.telegram_username,
                "phone": user.phone_number,
                "gender": user.gender.value,
                "language": user.preferred_language,
                "guardian_count": guardian_count,
                "created_at": user.created_at.isoformat(),
                "status": "active",
            }

        except Exception as e:
            logger.error(f"Failed to get profile for user {telegram_user_id}: {e}")
            return None

    async def update_user_language_from_telegram(
        self, telegram_user_id: int, language: str
    ) -> Dict[str, Any]:
        """Update user's preferred language from Telegram bot."""
        try:
            user = await self.user_service.get_by_telegram_id(telegram_user_id)
            if not user:
                raise ValueError("User not found")

            # Update language
            from app.schemas.user import UserUpdate

            update_data = UserUpdate(preferred_language=language)

            updated_user = await self.user_service.update(user.id, update_data)
            if updated_user:
                logger.info(f"Updated language to {language} for user {user.id}")
                return {
                    "success": True,
                    "language": language,
                    "message": f"Language updated to {language}",
                }
            else:
                return {"success": False, "message": "Failed to update language"}

        except Exception as e:
            logger.error(f"Failed to update language for user {telegram_user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to update language: {str(e)}",
            }

    def validate_phone_number(self, phone: str) -> str:
        """Validate and format phone number."""
        # Remove spaces and special characters
        phone = (
            phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        )

        # Ensure it starts with +
        if not phone.startswith("+"):
            # Try to add + if it looks like an international number
            if phone.startswith("00"):
                phone = "+" + phone[2:]
            elif phone.isdigit() and len(phone) >= 8:
                # If it's just digits, we can't determine country code safely
                raise ValueError(
                    "Phone number must include country code (start with +)"
                )
            else:
                phone = "+" + phone

        # Basic validation
        if len(phone) < 8 or len(phone) > 20:
            raise ValueError("Phone number must be between 8-20 characters")

        if not phone[1:].isdigit():
            raise ValueError("Phone number can only contain digits after the +")

        return phone

    # Guardian Registration Methods

    async def start_guardian_registration(
        self,
        telegram_user_id: int,
        telegram_chat_id: int,
        telegram_username: Optional[str],
        telegram_first_name: str,
        telegram_last_name: Optional[str],
        registration_token: str,
    ) -> Dict[str, Any]:
        """Start guardian registration process via Telegram."""
        try:
            # Find guardian by registration token
            query = select(Guardian).where(
                Guardian.invitation_token == registration_token
            )
            result = await self.db.execute(query)
            guardian = result.scalar_one_or_none()

            if not guardian:
                return {"status": "not_found", "message": "Invalid registration token"}

            # Check if token is expired
            if (
                guardian.invitation_expires_at
                and datetime.now(timezone.utc) > guardian.invitation_expires_at
            ):
                return {
                    "status": "expired",
                    "message": "Registration token has expired",
                }

            # Check if already registered
            if guardian.consent_given and guardian.verification_status in [
                "fully_verified",
                "telegram_verified",
            ]:
                return {
                    "status": "already_registered",
                    "message": "Guardian already registered",
                }

            # Get the user who invited this guardian
            user_guardian_query = (
                select(User)
                .join(UserGuardian, UserGuardian.user_id == User.id)
                .where(UserGuardian.guardian_id == guardian.id)
            )
            result = await self.db.execute(user_guardian_query)
            inviting_user = result.scalar_one_or_none()

            if not inviting_user:
                return {"status": "error", "message": "Inviting user not found"}

            # Update guardian with Telegram info (don't commit yet - waiting for consent)
            guardian.telegram_user_id = telegram_user_id
            guardian.telegram_chat_id = telegram_chat_id
            guardian.telegram_username = telegram_username

            return {
                "status": "success",
                "guardian": {
                    "id": str(guardian.id),
                    "name": guardian.name,
                    "phone_number": guardian.phone_number,
                    "verification_status": guardian.verification_status,
                },
                "user": {
                    "id": str(inviting_user.id),
                    "name": f"{inviting_user.first_name} {inviting_user.last_name or ''}".strip(),
                    "phone_number": inviting_user.phone_number,
                },
            }

        except Exception as e:
            logger.error(
                f"Error starting guardian registration for token {registration_token}: {e}"
            )
            return {"status": "error", "message": f"Registration error: {str(e)}"}

    async def accept_guardian_registration(
        self,
        registration_token: str,
        telegram_user_id: int,
    ) -> Dict[str, Any]:
        """Accept guardian registration and complete setup."""
        try:
            # Find guardian by registration token
            query = select(Guardian).where(
                Guardian.invitation_token == registration_token
            )
            result = await self.db.execute(query)
            guardian = result.scalar_one_or_none()

            if not guardian:
                return {"status": "error", "message": "Invalid registration token"}

            # Verify this is the same Telegram user (or if not set yet, accept and set it)
            if (
                guardian.telegram_user_id
                and guardian.telegram_user_id != telegram_user_id
            ):
                return {"status": "error", "message": "Telegram user mismatch"}

            # Set telegram user ID if not already set
            if not guardian.telegram_user_id:
                guardian.telegram_user_id = telegram_user_id

            # Update guardian registration
            guardian.consent_given = True
            guardian.registered_at = datetime.now(timezone.utc)
            guardian.verification_status = "telegram_verified"

            # TODO: Implement phone verification logic
            # For now, assume Telegram verification is sufficient
            phone_verified = await self._check_phone_verification(guardian)

            if phone_verified:
                guardian.verification_status = "fully_verified"
                verification_status = "fully_verified"
            else:
                # Send SMS verification
                await self._send_phone_verification(guardian)
                verification_status = "phone_verification_needed"

            await self.db.commit()

            logger.info(
                f"Guardian {guardian.id} accepted registration, status: {verification_status}"
            )

            return {
                "status": "success",
                "verification_status": verification_status,
                "guardian_id": str(guardian.id),
            }

        except Exception as e:
            logger.error(
                f"Error accepting guardian registration for token {registration_token}: {e}"
            )
            await self.db.rollback()
            return {
                "status": "error",
                "message": f"Failed to accept registration: {str(e)}",
            }

    async def decline_guardian_registration(
        self,
        registration_token: str,
        telegram_user_id: int,
    ) -> Dict[str, Any]:
        """Decline guardian registration and clean up."""
        try:
            # Find guardian by registration token
            query = select(Guardian).where(
                Guardian.invitation_token == registration_token
            )
            result = await self.db.execute(query)
            guardian = result.scalar_one_or_none()

            if not guardian:
                return {"status": "error", "message": "Invalid registration token"}

            # Mark as declined
            guardian.verification_status = "declined"
            guardian.consent_given = False

            # TODO: Notify the user who invited them
            # For now, just log it
            logger.info(f"Guardian {guardian.id} declined registration")

            await self.db.commit()

            return {
                "status": "success",
                "message": "Registration declined successfully",
            }

        except Exception as e:
            logger.error(
                f"Error declining guardian registration for token {registration_token}: {e}"
            )
            await self.db.rollback()
            return {
                "status": "error",
                "message": f"Failed to decline registration: {str(e)}",
            }

    async def _check_phone_verification(self, guardian: Guardian) -> bool:
        """Check if guardian's phone is already verified (e.g., via Telegram)."""
        # TODO: Implement logic to check if phone is verified via Telegram API
        # For testing purposes, consider Telegram verification as sufficient
        return True  # Accept Telegram verification as sufficient for now

    async def _send_phone_verification(self, guardian: Guardian):
        """Send SMS verification code to guardian's phone."""
        # TODO: Implement SMS verification code sending
        # This should integrate with your SMS provider (Twilio)
        logger.info(
            f"SMS verification needed for guardian {guardian.id} phone {guardian.phone_number}"
        )
        pass
