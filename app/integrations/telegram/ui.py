"""Telegram UI management for menus and Russian interface."""

from typing import Any

from app.core.logging import get_logger
from app.core.ui_strings import get_telegram_string

logger = get_logger(__name__)


class TelegramMenuManager:
    """Manages Telegram menu state and transitions."""

    def __init__(self) -> None:
        self.user_menus: dict[int, dict[str, Any]] = {}  # chat_id -> menu state

    def get_user_menu_state(self, chat_id: int) -> dict[str, Any]:
        """Get menu state for a user."""
        if chat_id not in self.user_menus:
            self.user_menus[chat_id] = {
                "last_menu_message_id": None,
                "current_menu": None,
                "incident_id": None,
            }
        return self.user_menus[chat_id]

    def update_menu_state(self, chat_id: int, **kwargs: Any) -> None:
        """Update menu state for a user."""
        state = self.get_user_menu_state(chat_id)
        state.update(kwargs)

    def clear_menu_state(self, chat_id: int) -> None:
        """Clear menu state for a user."""
        if chat_id in self.user_menus:
            del self.user_menus[chat_id]


# Global menu manager instance
menu_manager = TelegramMenuManager()


def create_welcome_message(user_name: str) -> dict[str, Any]:
    """Create welcome message for new users."""
    message = get_telegram_string("welcome_message", name=user_name)

    keyboard = [
        [{"text": get_telegram_string("panic_button"), "callback_data": "panic"}],
        [
            {
                "text": get_telegram_string("guardians_button"),
                "callback_data": "guardians",
            }
        ],
    ]

    return {"text": message, "reply_markup": {"inline_keyboard": keyboard}}


def create_guardians_menu() -> dict[str, Any]:
    """Create guardians menu."""
    message = get_telegram_string("guardians_menu_title")

    keyboard = [
        [
            {
                "text": get_telegram_string("add_guardian_button"),
                "callback_data": "add_guardian",
            }
        ],
        [{"text": get_telegram_string("back_button"), "callback_data": "main_menu"}],
        [{"text": get_telegram_string("panic_button"), "callback_data": "panic"}],
    ]

    return {"text": message, "reply_markup": {"inline_keyboard": keyboard}}


def create_active_incident_menu(incident_id: int) -> dict[str, Any]:
    """Create menu for active incident."""
    message = get_telegram_string("active_incident_message")

    keyboard = [
        [
            {
                "text": get_telegram_string("cancel_panic_button"),
                "callback_data": f"cancel_panic:{incident_id}",
            }
        ],
    ]

    return {"text": message, "reply_markup": {"inline_keyboard": keyboard}}


def create_confirmation_message(message_type: str, **kwargs: Any) -> str:
    """Create confirmation message."""
    if message_type == "panic_started":
        return get_telegram_string("panic_started_confirmation", **kwargs)
    elif message_type == "panic_acknowledged":
        return get_telegram_string("panic_acknowledged_confirmation", **kwargs)
    elif message_type == "panic_canceled":
        return get_telegram_string("panic_canceled_confirmation", **kwargs)
    elif message_type == "incident_exhausted":
        return get_telegram_string("incident_exhausted_message", **kwargs)
    else:
        return get_telegram_string("generic_confirmation")


def create_separator_message() -> str:
    """Create separator message between menu transitions."""
    return "----------"


def create_guardian_alert_message(ward_name: str) -> dict[str, Any]:
    """Create alert message for guardians."""
    message = get_telegram_string("guardian_alert", name=ward_name)

    keyboard = [
        [{"text": get_telegram_string("ack_button"), "callback_data": "ack_incident"}],
    ]

    return {"text": message, "reply_markup": {"inline_keyboard": keyboard}}


def create_acknowledgment_notification(guardian_name: str) -> str:
    """Create notification when incident is acknowledged."""
    return get_telegram_string(
        "acknowledgment_notification", guardian_name=guardian_name
    )


def create_cancel_notification(ward_name: str) -> str:
    """Create notification when incident is canceled."""
    return get_telegram_string("cancel_notification", name=ward_name)


def create_reminder_message() -> str:
    """Create reminder message for active incidents."""
    return get_telegram_string("reminder_message")


def create_onboarding_step_message(step: str, **kwargs: Any) -> dict[str, Any]:
    """Create message for onboarding steps."""
    if step == "welcome":
        message = get_telegram_string("onboarding_welcome")
        keyboard = [
            [
                {
                    "text": get_telegram_string("start_onboarding_button"),
                    "callback_data": "start_onboarding",
                }
            ],
        ]
    elif step == "name":
        message = get_telegram_string("onboarding_name_prompt")
        keyboard = []
    elif step == "gender":
        message = get_telegram_string("onboarding_gender_prompt")
        keyboard = [
            [
                {
                    "text": get_telegram_string("gender_male"),
                    "callback_data": "gender:male",
                },
                {
                    "text": get_telegram_string("gender_female"),
                    "callback_data": "gender:female",
                },
            ],
            [
                {
                    "text": get_telegram_string("gender_other"),
                    "callback_data": "gender:other",
                }
            ],
        ]
    elif step == "phone":
        message = get_telegram_string("onboarding_phone_prompt")
        keyboard = [
            [
                {
                    "text": get_telegram_string("share_phone_button"),
                    "callback_data": "share_phone",
                }
            ],
            [
                {
                    "text": get_telegram_string("skip_phone_button"),
                    "callback_data": "skip_phone",
                }
            ],
        ]
    elif step == "role":
        message = get_telegram_string("onboarding_role_prompt")
        keyboard = [
            [{"text": get_telegram_string("role_ward"), "callback_data": "role:ward"}],
            [
                {
                    "text": get_telegram_string("role_guardian"),
                    "callback_data": "role:guardian",
                }
            ],
        ]
    elif step == "linking":
        message = get_telegram_string("onboarding_linking_prompt")
        keyboard = [
            [
                {
                    "text": get_telegram_string("link_by_phone_button"),
                    "callback_data": "link_by_phone",
                }
            ],
            [
                {
                    "text": get_telegram_string("link_by_username_button"),
                    "callback_data": "link_by_username",
                }
            ],
        ]
    else:
        message = get_telegram_string("onboarding_generic")
        keyboard = []

    return {
        "text": message,
        "reply_markup": {"inline_keyboard": keyboard} if keyboard else None,
    }


def create_invitation_message(invite_token: str, invitee_name: str) -> dict[str, Any]:
    """Create invitation message with deep link."""
    deep_link = f"https://t.me/your_bot_username?start={invite_token}"
    message = get_telegram_string(
        "invitation_message", name=invitee_name, link=deep_link
    )

    keyboard = [
        [
            {
                "text": get_telegram_string("forward_invitation_button"),
                "callback_data": "forward_invitation",
            }
        ],
        [{"text": get_telegram_string("back_button"), "callback_data": "main_menu"}],
    ]

    return {"text": message, "reply_markup": {"inline_keyboard": keyboard}}


def create_access_denied_message() -> str:
    """Create access denied message for unauthorized users."""
    return get_telegram_string("access_denied_message")


def create_error_message(error_type: str) -> str:
    """Create error message."""
    if error_type == "phone_validation":
        return get_telegram_string("phone_validation_error")
    elif error_type == "invitation_failed":
        return get_telegram_string("invitation_failed_error")
    elif error_type == "linking_failed":
        return get_telegram_string("linking_failed_error")
    else:
        return get_telegram_string("generic_error")


def format_user_name(first_name: str, last_name: str | None = None) -> str:
    """Format user name for display."""
    if last_name:
        return f"{first_name} {last_name}"
    return first_name


def format_phone_number(phone: str) -> str:
    """Format phone number for display."""
    # Remove any non-digit characters except +
    cleaned = "".join(c for c in phone if c.isdigit() or c == "+")

    # Ensure it starts with +
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned

    return cleaned
