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
            # Main menu
            "panic_button": "🚨 Опасность",
            "guardians_button": "🧑‍🤝‍🧑 Мои опекуны",
            "back_button": "🔙 Вернуться в главное меню",
            # Incident management
            "cancel_panic_button": "🟢 Синал опасности принял. Уведомления и звонки больше не нужны.",
            "ack_button": "✅ Ясно",
            # Guardians menu
            "guardians_menu_title": "Мои опекуны",
            "add_guardian_button": "➕ Добавить опекуна",
            # Messages
            "welcome_message": "👋 Привет, {name}! Я твой помощник безопасности. Нажми кнопку «🚨 Опасность», и я сообщу твоим опекунам, что тебе нужна помощь.",
            "active_incident_message": "ℹ️ Сигнал опасности уже активен. Я уведомляю опекунов и пытаюсь дозвониться.",
            "panic_started_confirmation": "✅ Ты нажал(а) «Опасность». Я отправил уведомления твоим опекунам. Сейчас звоню им. Скоро кто-то из них перезвонит тебе.",
            "panic_acknowledged_confirmation": "🟢 Сигнал принят опекуном {guardian_name}. Мы остановили уведомления и звонки.",
            "panic_canceled_confirmation": "✅ Ты отменил(а) сигнал опасности.",
            "incident_exhausted_message": "⚠️ Не удалось связаться с опекунами. Попробуй ещё раз или проверь номера.",
            "incident_already_active": "ℹ️ Сигнал опасности уже активен. Я уведомляю опекунов и пытаюсь дозвониться.",
            # Guardian alerts
            "guardian_alert": "🚨 {name} нажал(а) «Опасность». Пожалуйста, свяжитесь с ней/ним.",
            "acknowledgment_notification": "🟢 {guardian_name} принял(а) сигнал опасности. Уведомления и звонки остановлены.",
            "cancel_notification": "✅ {name} отменил(а) сигнал опасности.",
            "reminder_message": "⏰ Тревога всё ещё активна! Кто возьмёт ответственность?",
            # Onboarding
            "onboarding_welcome": "Добро пожаловать в Protectogram! Давайте настроим ваш профиль.",
            "start_onboarding_button": "Начать настройку",
            "onboarding_name_prompt": "Как вас зовут? (1-50 символов)",
            "onboarding_gender_prompt": "Укажите ваш пол:",
            "gender_male": "Мужской",
            "gender_female": "Женский",
            "gender_other": "Другое",
            "onboarding_phone_prompt": "Укажите ваш номер телефона:",
            "share_phone_button": "📱 Поделиться номером",
            "skip_phone_button": "Пропустить",
            "onboarding_role_prompt": "Выберите вашу роль:",
            "role_ward": "Я хочу чтобы мой родитель/опекун знал, если я попаду в опасность",
            "role_guardian": "Я — родитель/опекун и хочу знать, если мой подопечный попадёт в опасность",
            "onboarding_linking_prompt": "Как вы хотите связаться с вашим партнёром?",
            "link_by_phone_button": "По номеру телефона",
            "link_by_username_button": "По @username",
            "onboarding_generic": "Продолжайте настройку...",
            # Invitations
            "invitation_message": "Приглашение для {name}:\n{link}",
            "forward_invitation_button": "📤 Переслать приглашение",
            # Access control
            "access_denied_message": "🚫 Извини, сейчас Protectogram доступен по приглашению. Если хочешь участвовать — напиши нам, и мы включим твой номер.",
            # Errors
            "phone_validation_error": "❌ Неверный формат номера телефона. Попробуйте ещё раз.",
            "invitation_failed_error": "❌ Не удалось создать приглашение. Попробуйте ещё раз.",
            "linking_failed_error": "❌ Не удалось связать аккаунты. Попробуйте ещё раз.",
            "incident_creation_failed": "❌ Не удалось создать инцидент. Попробуйте ещё раз.",
            "cancel_failed": "❌ Не удалось отменить инцидент. Попробуйте ещё раз.",
            "ack_failed": "❌ Не удалось подтвердить инцидент. Попробуйте ещё раз.",
            "no_active_incident": "❌ Нет активного инцидента.",
            "generic_error": "❌ Произошла ошибка. Попробуйте ещё раз.",
            "generic_confirmation": "✅ Операция выполнена успешно.",
        },
        "tts": {
            "panic_message": "Нажмите кнопку 1, если вы приняли сигнал опасности и подтверждаете, что уведомления и звонки больше не нужны.",
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
