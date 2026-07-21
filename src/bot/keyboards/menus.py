"""Сборка inline-клавиатур."""

from __future__ import annotations

from typing import TYPE_CHECKING

from maxapi.types import CallbackButton, ClipboardButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

if TYPE_CHECKING:
    from maxapi.types.attachments.buttons.attachment_button import AttachmentButton

# Payload-и callback-кнопок
CB_MY_ID = "my_id"
CB_CHAT_ID = "chat_id"
CB_HELP = "help"

# MAX ограничивает длину payload кнопки; ID заведомо короче, но обрезаем на всякий случай
MAX_CLIPBOARD_LENGTH = 512


def main_menu() -> AttachmentButton:
    """Собирает главное меню бота.

    Returns:
        Вложение с inline-клавиатурой.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="🙋 Мой ID", payload=CB_MY_ID),
        CallbackButton(text="💬 ID чата", payload=CB_CHAT_ID),
    )
    builder.row(CallbackButton(text="❓ Что я умею", payload=CB_HELP))
    return builder.as_markup()


def build_reply_markup(copy_value: str | None) -> list[AttachmentButton]:
    """Собирает клавиатуру для ответа с идентификатором.

    Args:
        copy_value: Значение для кнопки «Скопировать ID». Если `None`,
            кнопка копирования не добавляется.

    Returns:
        Список вложений для передачи в `attachments`.
    """
    builder = InlineKeyboardBuilder()

    if copy_value:
        builder.row(
            ClipboardButton(
                text="📋 Скопировать ID",
                payload=copy_value[:MAX_CLIPBOARD_LENGTH],
            )
        )

    builder.row(
        CallbackButton(text="🙋 Мой ID", payload=CB_MY_ID),
        CallbackButton(text="💬 ID чата", payload=CB_CHAT_ID),
    )

    return [builder.as_markup()]
