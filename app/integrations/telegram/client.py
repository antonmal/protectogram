"""Telegram Bot API client."""

import json
from typing import Any

import httpx


class TelegramAPIError(Exception):
    """Telegram API error."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"Telegram API error {status_code}: {message}")


class TelegramClient:
    """Lightweight Telegram Bot API client."""

    def __init__(self, bot_token: str, api_base: str = "https://api.telegram.org") -> None:
        """Initialize Telegram client."""
        self.bot_token = bot_token
        self.api_base = api_base.rstrip("/")

    def _build_url(self, method: str) -> str:
        """Build API URL for method."""
        url = f"{self.api_base}/bot{self.bot_token}/{method}"
        return url

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str | None = None,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a message to a chat."""
        payload = {
            "chat_id": chat_id,
            "text": text,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._build_url("sendMessage"),
                json=payload,
                timeout=30.0,
            )

        if not response.is_success:
            raise TelegramAPIError(response.status_code, f"Failed to send message: {response.text}")

        return response.json()

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: str | None = None,
        show_alert: bool = False,
    ) -> dict[str, Any]:
        """Answer a callback query."""
        payload = {
            "callback_query_id": callback_query_id,
            "show_alert": show_alert,
        }
        if text:
            payload["text"] = text

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._build_url("answerCallbackQuery"),
                json=payload,
                timeout=30.0,
            )

        if not response.is_success:
            raise TelegramAPIError(
                response.status_code, f"Failed to answer callback query: {response.text}"
            )

        return response.json()
