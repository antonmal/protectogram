"""Telegram message handlers for Prompt 6 - Domain integration."""

from typing import Any

from app.core.access_control import is_phone_number_allowed
from app.core.logging import get_logger
from app.core.services import TelegramService
from app.domain.panic import (
    get_active_incident_for_user,
)
from app.integrations.telegram.ui import (
    create_access_denied_message,
    create_active_incident_menu,
    create_confirmation_message,
    create_error_message,
    create_guardians_menu,
    create_onboarding_step_message,
    create_separator_message,
    create_welcome_message,
    format_phone_number,
    menu_manager,
)
from app.integrations.telnyx.cascade import initiate_call_cascade

logger = get_logger(__name__)


async def handle_telegram_update(
    update_data: dict[str, Any],
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> bool:
    """
    Handle incoming Telegram update with deduplication.

    Returns True if update was processed, False if duplicate.
    """
    update_id = update_data.get("update_id")
    if not update_id:
        logger.warning("Update missing update_id", update_data=update_data)
        return False

    # Check for duplicate update_id
    if await telegram_service.is_duplicate_event("telegram", str(update_id)):
        logger.info("Duplicate update_id, skipping", update_id=update_id)
        return False

    # Store in inbox_events for deduplication
    await telegram_service.store_inbox_event("telegram", str(update_id), update_data)

    # Process the update
    await _process_telegram_update(update_data, telegram_service, correlation_id)

    return True


async def _process_telegram_update(
    update_data: dict[str, Any],
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> None:
    """Process Telegram update (internal function)."""
    # Handle different update types
    if "message" in update_data:
        await _handle_message(update_data["message"], telegram_service, correlation_id)
    elif "callback_query" in update_data:
        await _handle_callback_query(
            update_data["callback_query"], telegram_service, correlation_id
        )
    else:
        logger.info("Unhandled update type", update_type=list(update_data.keys()))


async def _handle_message(
    message: dict[str, Any],
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> None:
    """Handle incoming Telegram message."""
    text = message.get("text", "").strip()
    chat_id = message.get("chat", {}).get("id")
    user_data = message.get("from", {})

    if not chat_id or not user_data:
        logger.warning("Invalid message format", message=message)
        return

    # Get or create user
    user = await telegram_service.get_or_create_user(
        str(user_data.get("id")),
        user_data.get("first_name", "Unknown User"),
    )

    logger.info(
        "Received message",
        chat_id=chat_id,
        user_id=user.id,
        text=text[:50] + "..." if len(text) > 50 else text,
        correlation_id=correlation_id,
    )

    # Handle /start command
    if text == "/start":
        await _handle_start_command(chat_id, user, telegram_service, correlation_id)
        return

    # Handle deep link invitations
    if text.startswith("/start "):
        invite_token = text.split(" ", 1)[1]
        await _handle_invitation_link(
            chat_id, user, invite_token, telegram_service, correlation_id
        )
        return

    # Handle onboarding responses
    user_state = menu_manager.get_user_menu_state(chat_id)
    if user_state.get("onboarding_step"):
        await _handle_onboarding_response(
            chat_id, user, text, user_state, telegram_service, correlation_id
        )
        return

    # Handle regular messages
    await _handle_regular_message(chat_id, user, text, telegram_service, correlation_id)


async def _handle_callback_query(
    callback_query: dict[str, Any],
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> None:
    """Handle Telegram callback query (button press)."""
    data = callback_query.get("data", "")
    user_data = callback_query.get("from", {})
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")

    if not data or not user_data:
        logger.warning("Invalid callback query", callback_query=callback_query)
        return

    # Get user
    user = await telegram_service.get_or_create_user(
        str(user_data.get("id")),
        user_data.get("first_name", "Unknown User"),
    )

    logger.info(
        "Received callback query",
        data=data,
        user_id=user.id,
        chat_id=chat_id,
        correlation_id=correlation_id,
    )

    # Handle different button actions
    if data == "panic":
        await _handle_panic_button(chat_id, user, telegram_service, correlation_id)
    elif data == "guardians":
        await _handle_guardians_button(chat_id, user, telegram_service, correlation_id)
    elif data == "main_menu":
        await _handle_main_menu_button(chat_id, user, telegram_service, correlation_id)
    elif data.startswith("cancel_panic:"):
        incident_id = int(data.split(":", 1)[1])
        await _handle_cancel_panic_button(
            chat_id, user, incident_id, telegram_service, correlation_id
        )
    elif data == "ack_incident":
        await _handle_ack_incident_button(
            chat_id, user, telegram_service, correlation_id
        )
    elif data.startswith("gender:"):
        gender = data.split(":", 1)[1]
        await _handle_gender_selection(
            chat_id, user, gender, telegram_service, correlation_id
        )
    elif data.startswith("role:"):
        role = data.split(":", 1)[1]
        await _handle_role_selection(
            chat_id, user, role, telegram_service, correlation_id
        )
    elif data == "share_phone":
        await _handle_share_phone_button(
            chat_id, user, telegram_service, correlation_id
        )
    elif data == "skip_phone":
        await _handle_skip_phone_button(chat_id, user, telegram_service, correlation_id)
    elif data == "start_onboarding":
        await _handle_start_onboarding_button(
            chat_id, user, telegram_service, correlation_id
        )
    else:
        await telegram_service.send_confirmation_message(
            chat_id, f"Unknown button: {data}"
        )


# Message sending is now handled by the TelegramService


async def _handle_start_command(
    chat_id: int,
    user: Any,
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> None:
    """Handle /start command."""
    # Check if user needs onboarding
    if not user.display_name or user.display_name == "Unknown User":
        # Start onboarding
        menu_manager.update_menu_state(chat_id, onboarding_step="welcome")
        onboarding_msg = create_onboarding_step_message("welcome")
        await telegram_service.send_message(
            chat_id, onboarding_msg["text"], onboarding_msg.get("reply_markup")
        )
    else:
        # Show welcome message
        welcome_msg = create_welcome_message(user.display_name)
        await telegram_service.send_message(
            chat_id, welcome_msg["text"], welcome_msg["reply_markup"]
        )
        menu_manager.update_menu_state(chat_id, current_menu="main")


async def _handle_invitation_link(
    chat_id: int,
    user: Any,
    invite_token: str,
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> None:
    """Handle invitation deep link."""
    # TODO: Validate invite token and link users
    # For now, just start onboarding
    menu_manager.update_menu_state(
        chat_id, onboarding_step="welcome", invite_token=invite_token
    )
    onboarding_msg = create_onboarding_step_message("welcome")
    await telegram_service.send_message(
        chat_id, onboarding_msg["text"], onboarding_msg.get("reply_markup")
    )


async def _handle_onboarding_response(
    chat_id: int,
    user: Any,
    text: str,
    user_state: dict[str, Any],
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> None:
    """Handle onboarding step responses."""
    current_step = user_state.get("onboarding_step")

    if current_step == "name":
        if len(text) < 1 or len(text) > 50:
            await telegram_service.send_confirmation_message(
                chat_id, "Имя должно быть от 1 до 50 символов."
            )
            return

        # Update user name
        user.display_name = text
        await telegram_service.session.flush()

        # Move to next step
        menu_manager.update_menu_state(chat_id, onboarding_step="gender")
        gender_msg = create_onboarding_step_message("gender")
        await telegram_service.send_message(
            chat_id, gender_msg["text"], gender_msg["reply_markup"]
        )

    elif current_step == "phone":
        # Validate phone number
        phone = format_phone_number(text)
        if not is_phone_number_allowed(phone):
            await telegram_service.send_confirmation_message(
                chat_id, create_access_denied_message()
            )
            return

        # Update user phone
        user.phone_e164 = phone
        await telegram_service.session.flush()

        # Move to next step
        menu_manager.update_menu_state(chat_id, onboarding_step="role")
        role_msg = create_onboarding_step_message("role")
        await telegram_service.send_message(
            chat_id, role_msg["text"], role_msg["reply_markup"]
        )


async def _handle_regular_message(
    chat_id: int,
    user: Any,
    text: str,
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> None:
    """Handle regular text messages."""
    await telegram_service.send_confirmation_message(
        chat_id, "Используйте кнопки меню для навигации."
    )


async def _handle_panic_button(
    chat_id: int,
    user: Any,
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> None:
    """Handle panic button press."""
    # Check for existing active incident
    existing_incident = await get_active_incident_for_user(
        telegram_service.session, user.id
    )

    if existing_incident:
        # Incident already active
        confirmation_msg = create_confirmation_message("incident_already_active")
        await telegram_service.send_confirmation_message(chat_id, confirmation_msg)

        # Show active incident menu
        incident_menu = create_active_incident_menu(existing_incident.id)
        await telegram_service.send_message(
            chat_id, incident_menu["text"], incident_menu["reply_markup"]
        )
        menu_manager.update_menu_state(
            chat_id, current_menu="active_incident", incident_id=existing_incident.id
        )
        return

    # Create new incident via PanicService
    from app.core.dependencies import get_panic_service

    panic_service = get_panic_service(telegram_service.session)
    incident_id = await panic_service.create_panic_incident(
        str(user.telegram_id),
        correlation_id,
    )

    if not incident_id:
        # Failed to create incident
        error_msg = create_error_message("incident_creation_failed")
        await telegram_service.send_confirmation_message(chat_id, error_msg)
        return

    # Send confirmation
    confirmation_msg = create_confirmation_message("panic_started")
    await telegram_service.send_confirmation_message(chat_id, confirmation_msg)

    # Send separator
    separator_msg = create_separator_message()
    await telegram_service.send_confirmation_message(chat_id, separator_msg)

    # Show active incident menu
    incident_menu = create_active_incident_menu(int(incident_id))
    await telegram_service.send_message(
        chat_id, incident_menu["text"], incident_menu["reply_markup"]
    )
    menu_manager.update_menu_state(
        chat_id, current_menu="active_incident", incident_id=int(incident_id)
    )

    # Start call cascade
    await initiate_call_cascade(
        telegram_service.session, int(incident_id), correlation_id
    )


async def _handle_guardians_button(
    chat_id: int,
    user: Any,
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> None:
    """Handle guardians menu button."""
    guardians_menu = create_guardians_menu()
    await telegram_service.send_message(
        chat_id, guardians_menu["text"], guardians_menu["reply_markup"]
    )
    menu_manager.update_menu_state(chat_id, current_menu="guardians")


async def _handle_main_menu_button(
    chat_id: int,
    user: Any,
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> None:
    """Handle main menu button."""
    welcome_msg = create_welcome_message(user.display_name)
    await telegram_service.send_message(
        chat_id, welcome_msg["text"], welcome_msg["reply_markup"]
    )
    menu_manager.update_menu_state(chat_id, current_menu="main")


async def _handle_cancel_panic_button(
    chat_id: int,
    user: Any,
    incident_id: int,
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> None:
    """Handle cancel panic button."""
    from app.core.dependencies import get_panic_service

    panic_service = get_panic_service(telegram_service.session)

    success = await panic_service.cancel_panic(
        incident_id,
        user.id,
        correlation_id,
    )

    if success:
        # Send confirmation
        confirmation_msg = create_confirmation_message("panic_canceled")
        await telegram_service.send_confirmation_message(chat_id, confirmation_msg)

        # Send separator
        separator_msg = create_separator_message()
        await telegram_service.send_confirmation_message(chat_id, separator_msg)

        # Show main menu
        welcome_msg = create_welcome_message(user.display_name)
        await telegram_service.send_message(
            chat_id, welcome_msg["text"], welcome_msg["reply_markup"]
        )
        menu_manager.update_menu_state(chat_id, current_menu="main", incident_id=None)
    else:
        error_msg = create_error_message("cancel_failed")
        await telegram_service.send_confirmation_message(chat_id, error_msg)


async def _handle_ack_incident_button(
    chat_id: int,
    user: Any,
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> None:
    """Handle acknowledge incident button."""
    user_state = menu_manager.get_user_menu_state(chat_id)
    incident_id = user_state.get("incident_id")

    if not incident_id:
        error_msg = create_error_message("no_active_incident")
        await telegram_service.send_confirmation_message(chat_id, error_msg)
        return

    from app.core.dependencies import get_panic_service

    panic_service = get_panic_service(telegram_service.session)

    success = await panic_service.acknowledge_panic(
        incident_id,
        user.id,
        correlation_id,
    )

    if success:
        # Send confirmation
        confirmation_msg = create_confirmation_message(
            "panic_acknowledged", guardian_name=user.display_name
        )
        await telegram_service.send_confirmation_message(chat_id, confirmation_msg)

        # Send separator
        separator_msg = create_separator_message()
        await telegram_service.send_confirmation_message(chat_id, separator_msg)

        # Show main menu
        welcome_msg = create_welcome_message(user.display_name)
        await telegram_service.send_message(
            chat_id, welcome_msg["text"], welcome_msg["reply_markup"]
        )
        menu_manager.update_menu_state(chat_id, current_menu="main", incident_id=None)
    else:
        error_msg = create_error_message("ack_failed")
        await telegram_service.send_confirmation_message(chat_id, error_msg)


async def _handle_gender_selection(
    chat_id: int,
    user: Any,
    gender: str,
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> None:
    """Handle gender selection in onboarding."""
    # TODO: Store gender preference
    # For now, just move to next step

    # Move to phone step
    menu_manager.update_menu_state(chat_id, onboarding_step="phone")
    phone_msg = create_onboarding_step_message("phone")
    await telegram_service.send_message(
        chat_id, phone_msg["text"], phone_msg["reply_markup"]
    )


async def _handle_role_selection(
    chat_id: int,
    user: Any,
    role: str,
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> None:
    """Handle role selection in onboarding."""
    # TODO: Store role preference
    # For now, just move to next step

    # Move to linking step
    menu_manager.update_menu_state(chat_id, onboarding_step="linking")
    linking_msg = create_onboarding_step_message("linking")
    await telegram_service.send_message(
        chat_id, linking_msg["text"], linking_msg["reply_markup"]
    )


async def _handle_share_phone_button(
    chat_id: int,
    user: Any,
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> None:
    """Handle share phone button."""
    # TODO: Handle Telegram contact sharing
    # For now, just move to next step
    menu_manager.update_menu_state(chat_id, onboarding_step="role")
    role_msg = create_onboarding_step_message("role")
    await telegram_service.send_message(
        chat_id, role_msg["text"], role_msg["reply_markup"]
    )


async def _handle_skip_phone_button(
    chat_id: int,
    user: Any,
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> None:
    """Handle skip phone button."""
    # Move to role selection
    menu_manager.update_menu_state(chat_id, onboarding_step="role")
    role_msg = create_onboarding_step_message("role")
    await telegram_service.send_message(
        chat_id, role_msg["text"], role_msg["reply_markup"]
    )


async def _handle_start_onboarding_button(
    chat_id: int,
    user: Any,
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> None:
    """Handle start onboarding button."""
    # Move to name step
    menu_manager.update_menu_state(chat_id, onboarding_step="name")
    name_msg = create_onboarding_step_message("name")
    await telegram_service.send_message(
        chat_id, name_msg["text"], name_msg.get("reply_markup")
    )
