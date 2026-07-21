"""Обработка нажатий inline-кнопок.

Каждое нажатие обязано быть подтверждено (`edit` или `ack`), иначе кнопка
в клиенте останется в состоянии загрузки.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from maxapi.dispatcher import Router
from maxapi.enums.parse_mode import ParseMode

from bot.formatters import HELP_TEXT, IdCard, format_chat, format_user
from bot.keyboards import CB_CHAT_ID, CB_HELP, CB_MY_ID, build_reply_markup, main_menu

if TYPE_CHECKING:
    from maxapi.types import MessageCallback

logger = logging.getLogger(__name__)

callbacks_router = Router(router_id="callbacks")


async def edit_with_card(event: MessageCallback, card: IdCard) -> None:
    """Заменяет текст сообщения карточкой и подтверждает нажатие.

    Args:
        event: Событие нажатия кнопки.
        card: Готовая карточка.
    """
    await event.edit(
        text=card.text,
        attachments=build_reply_markup(card.copy_value),
        format=ParseMode.HTML,
    )


@callbacks_router.message_callback()
async def on_callback(event: MessageCallback) -> None:
    """Маршрутизирует нажатия кнопок главного меню.

    Args:
        event: Событие нажатия кнопки.
    """
    payload = event.callback.payload

    if payload == CB_MY_ID:
        await edit_with_card(event, format_user(event.callback.user))
        return

    if payload == CB_CHAT_ID:
        if event.message is None:
            await event.ack(notification="Не удалось определить чат")
            return
        await edit_with_card(event, format_chat(event.message.recipient))
        return

    if payload == CB_HELP:
        await event.edit(
            text=HELP_TEXT,
            attachments=[main_menu()],
            format=ParseMode.HTML,
        )
        return

    logger.warning("Неизвестный payload кнопки: %r", payload)
    await event.ack(notification="Неизвестная кнопка")
