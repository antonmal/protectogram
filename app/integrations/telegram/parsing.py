"""Telegram update parsing utilities."""


def compute_provider_event_id(update_json: dict) -> str:
    """Compute provider event ID from Telegram update.

    Args:
        update_json: Raw Telegram update JSON

    Returns:
        Provider event ID string

    Note:
        - For messages: str(update.update_id)
        - For callback queries: callback_query.id
    """
    update_id = update_json.get("update_id")
    if update_id is not None:
        return str(update_id)

    # Fallback for callback queries
    callback_query = update_json.get("callback_query", {})
    callback_id = callback_query.get("id")
    if callback_id is not None:
        return str(callback_id)

    # Last resort - use update_id if available
    return str(update_id) if update_id is not None else "unknown"


def extract_chat_id(update_json: dict) -> int | None:
    """Extract chat ID from Telegram update.

    Args:
        update_json: Raw Telegram update JSON

    Returns:
        Chat ID if found, None otherwise
    """
    # Try message first
    message = update_json.get("message")
    if message is not None:
        chat = message.get("chat", {})
        chat_id = chat.get("id")
        if chat_id is not None:
            return int(chat_id)

    # Try callback query
    callback_query = update_json.get("callback_query", {})
    message = callback_query.get("message")
    if message is not None:
        chat = message.get("chat", {})
        chat_id = chat.get("id")
        if chat_id is not None:
            return int(chat_id)

    # Try edited message
    edited_message = update_json.get("edited_message")
    if edited_message is not None:
        chat = edited_message.get("chat", {})
        chat_id = chat.get("id")
        if chat_id is not None:
            return int(chat_id)

    # Try channel post
    channel_post = update_json.get("channel_post")
    if channel_post is not None:
        chat = channel_post.get("chat", {})
        chat_id = chat.get("id")
        if chat_id is not None:
            return int(chat_id)

    return None
