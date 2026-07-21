"""Извлечение идентификаторов из входящих сообщений."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from maxapi.dispatcher import Router
from maxapi.enums.parse_mode import ParseMode
from maxapi.types import Command, CommandStart

from bot.formatters import (
    GREETING_TEXT,
    HELP_TEXT,
    MEDIA_TYPES,
    NOTHING_FOUND_TEXT,
    IdCard,
    format_chat,
    format_contact,
    format_linked_message,
    format_media,
    format_user,
    merge_cards,
)
from bot.keyboards import build_reply_markup, main_menu

if TYPE_CHECKING:
    from maxapi.types import BotStarted, MessageCreated

logger = logging.getLogger(__name__)

# Роутер команд: подключается первым, чтобы команды не съел catch-all
commands_router = Router(router_id="commands")

# Catch-all роутер: подключается последним
fallback_router = Router(router_id="fallback")


async def answer_card(event: MessageCreated, card: IdCard) -> None:
    """Отправляет карточку с идентификатором и клавиатурой.

    Args:
        event: Событие входящего сообщения.
        card: Готовая карточка.
    """
    await event.message.answer(
        text=card.text,
        attachments=build_reply_markup(card.copy_value),
        parse_mode=ParseMode.HTML,
    )


def collect_cards(event: MessageCreated) -> list[IdCard]:
    """Собирает все карточки идентификаторов из входящего сообщения.

    Args:
        event: Событие входящего сообщения.

    Returns:
        Список карточек; пустой, если полезных идентификаторов нет.
    """
    message = event.message
    cards: list[IdCard] = []

    if message.link is not None:
        cards.append(format_linked_message(message.link))

    body = message.body
    attachments = body.attachments if body is not None else None
    for attachment in attachments or []:
        attachment_type = str(getattr(attachment.type, "value", attachment.type))

        if attachment_type == "contact":
            if attachment.payload is not None:
                cards.append(format_contact(attachment.payload))
        elif attachment_type in MEDIA_TYPES:
            cards.append(format_media(attachment))

    return cards


@commands_router.bot_started()
async def on_bot_started(event: BotStarted) -> None:
    """Приветствует пользователя при первом запуске бота.

    Args:
        event: Событие запуска бота.
    """
    logger.info("Бот запущен пользователем user_id=%s", event.user.user_id)
    await event.send(
        text=GREETING_TEXT,
        attachments=[main_menu()],
        parse_mode=ParseMode.HTML,
    )


@commands_router.message_created(CommandStart())
async def on_start(event: MessageCreated) -> None:
    """Отвечает на `/start`: краткая справка и меню.

    Args:
        event: Событие входящего сообщения.
    """
    await event.message.answer(
        text=GREETING_TEXT,
        attachments=[main_menu()],
        parse_mode=ParseMode.HTML,
    )


@commands_router.message_created(Command("help"))
async def on_help(event: MessageCreated) -> None:
    """Отвечает на `/help`.

    Args:
        event: Событие входящего сообщения.
    """
    await event.message.answer(
        text=HELP_TEXT,
        attachments=[main_menu()],
        parse_mode=ParseMode.HTML,
    )


@commands_router.message_created(Command("myid"))
async def on_my_id(event: MessageCreated) -> None:
    """Отвечает на `/myid`: идентификатор отправителя.

    Args:
        event: Событие входящего сообщения.
    """
    sender = event.message.sender
    if sender is None:
        await event.message.answer(
            text="Не удалось определить отправителя этого сообщения.",
            parse_mode=ParseMode.HTML,
        )
        return

    await answer_card(event, format_user(sender))


@commands_router.message_created(Command("chatid"))
async def on_chat_id(event: MessageCreated) -> None:
    """Отвечает на `/chatid`: идентификатор и тип текущего чата.

    Args:
        event: Событие входящего сообщения.
    """
    await answer_card(event, format_chat(event.message.recipient))


@fallback_router.message_created()
async def on_any_message(event: MessageCreated) -> None:
    """Разбирает произвольное сообщение: пересылка, контакт, медиа.

    Регистрируется в отдельном роутере, который подключается последним,
    поэтому команды сюда не попадают.

    Args:
        event: Событие входящего сообщения.
    """
    cards = collect_cards(event)

    if not cards:
        await event.message.answer(
            text=NOTHING_FOUND_TEXT,
            attachments=[main_menu()],
            parse_mode=ParseMode.HTML,
        )
        return

    await answer_card(event, merge_cards(cards))
