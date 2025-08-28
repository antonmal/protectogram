"""Russian UI strings for Protectogram."""

import json
from pathlib import Path
from typing import Any


def load_ui_strings() -> dict[str, Any]:
    """Load Russian UI strings from JSON file."""
    # Try to load from the downloads path first, then fallback to project root
    ui_file_paths = [
        Path.home() / "Downloads" / "protectogram_ui_ru.json",
        Path(__file__).parent.parent.parent / "protectogram_ui_ru.json",
    ]

    for ui_file_path in ui_file_paths:
        if ui_file_path.exists():
            with open(ui_file_path, encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
                return data

    # Fallback to default strings if file not found
    return {
        "telegram": {
            "panic_button": "🚨 Опасность",
            "cancel_panic_button": "❌ Опасность миновала",
            "ack_button": "✅ Ясно",
            "panic_alert": "🚨 {name} нажал(а) кнопку Опасность! Нажмите «Ясно», чтобы остановить напоминания.",
            "acknowledged_alert": "✅ {name} взял(а) ответственность. Рассылка остановлена.",
            "canceled_alert": "❌ {name} отменил(а) тревогу.",
            "reminder_alert": "⏰ Тревога всё ещё активна! Кто возьмёт ответственность?",
        },
        "tts": {
            "panic_message": "Тревога! Срочно свяжитесь с {name}. Нажмите 1, чтобы подтвердить.",
            "acknowledged_message": "Ответственность взята. Спасибо.",
            "canceled_message": "Опасность миновала.",
        },
        "admin": {
            "trigger_panic_test": "Запустить тест функции Опасность",
            "health_ready": "Сервис готов",
            "health_live": "Сервис работает",
        },
    }


# Load strings at module import time
UI_STRINGS = load_ui_strings()


def get_telegram_string(key: str, **kwargs: Any) -> str:
    """Get a Telegram UI string with optional formatting."""
    template: str = UI_STRINGS["telegram"].get(key, key)
    return template.format(**kwargs)


def get_tts_string(key: str, **kwargs: Any) -> str:
    """Get a TTS UI string with optional formatting."""
    template: str = UI_STRINGS["tts"].get(key, key)
    return template.format(**kwargs)


def get_admin_string(key: str, **kwargs: Any) -> str:
    """Get an admin UI string with optional formatting."""
    template: str = UI_STRINGS["admin"].get(key, key)
    return template.format(**kwargs)
