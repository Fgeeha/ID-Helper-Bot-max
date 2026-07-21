"""Чистые функции форматирования ответов бота.

Модуль намеренно не зависит от сети и от объекта `Bot`: сюда приходят уже
разобранные библиотекой модели, отсюда уходит готовый HTML. Благодаря этому
всё содержимое покрывается обычными юнит-тестами.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from maxapi.types import ContactAttachmentPayload, LinkedMessage, Recipient, User
    from maxapi.types.attachments.attachment import Attachment

# Подписи типов чата для человекочитаемого вывода
CHAT_TYPE_LABELS: dict[str, str] = {
    "dialog": "личный диалог",
    "chat": "групповой чат",
    "channel": "канал",
}

# Подписи типов вложений
ATTACHMENT_TYPE_LABELS: dict[str, str] = {
    "image": "изображение",
    "video": "видео",
    "audio": "аудио",
    "file": "файл",
    "sticker": "стикер",
    "share": "ссылка",
    "location": "геопозиция",
    "contact": "контакт",
}

# Типы вложений, для которых показываем идентификатор медиа
MEDIA_TYPES: frozenset[str] = frozenset({"image", "video", "audio", "file", "sticker"})

HELP_TEXT = (
    "Я показываю идентификаторы в MAX.\n\n"
    "<b>Что умею:</b>\n"
    "• <code>/myid</code> — твой <code>user_id</code>\n"
    "• <code>/chatid</code> — <code>chat_id</code> текущего чата\n"
    "• перешли мне сообщение — покажу ID его автора\n"
    "• пришли контакт — покажу <code>user_id</code> этого человека\n"
    "• пришли фото, видео или файл — покажу тип и идентификатор медиа"
)

NOTHING_FOUND_TEXT = (
    "В этом сообщении нет полезных идентификаторов.\n\n"
    "Можешь прислать мне:\n"
    "• пересланное сообщение — покажу ID автора\n"
    "• контакт — покажу <code>user_id</code> человека\n"
    "• фото, видео или файл — покажу идентификатор медиа\n\n"
    "Или используй команды <code>/myid</code> и <code>/chatid</code>."
)

GREETING_TEXT = "Привет! 👋\n\n" + HELP_TEXT


@dataclass(frozen=True)
class IdCard:
    """Готовый ответ бота.

    Attributes:
        text: HTML-текст сообщения.
        copy_value: Значение для кнопки «Скопировать ID», либо `None`,
            если копировать нечего.
    """

    text: str
    copy_value: str | None = None


def _enum_value(value: object) -> str:
    """Приводит enum или строку к строковому значению.

    Args:
        value: Поле модели, которое может быть `Enum` или обычной строкой.

    Returns:
        Строковое представление значения.
    """
    return str(getattr(value, "value", value))


def format_user_name(user: User) -> str:
    """Собирает отображаемое имя пользователя.

    Args:
        user: Модель пользователя.

    Returns:
        Имя и фамилия через пробел, экранированные для HTML.
    """
    parts = [user.first_name, user.last_name]
    return escape(" ".join(part for part in parts if part))


def format_user(user: User, *, title: str = "Твой ID") -> IdCard:
    """Форматирует карточку пользователя.

    Args:
        user: Модель пользователя.
        title: Заголовок карточки.

    Returns:
        Карточка с `user_id`, именем, `@username` и ссылкой на профиль.
    """
    lines = [
        f"<b>{escape(title)}</b>",
        f"user_id: <code>{user.user_id}</code>",
        f"Имя: {format_user_name(user)}",
    ]

    if user.username:
        lines.append(f"Username: <code>@{escape(user.username)}</code>")
    if user.is_bot:
        lines.append("Это бот 🤖")

    lines.append(f"Ссылка: <code>max://user/{user.user_id}</code>")

    return IdCard(text="\n".join(lines), copy_value=str(user.user_id))


def format_chat(recipient: Recipient) -> IdCard:
    """Форматирует карточку чата.

    Args:
        recipient: Получатель сообщения — источник `chat_id` и типа чата.

    Returns:
        Карточка с `chat_id` и типом чата.
    """
    chat_type = _enum_value(recipient.chat_type)
    label = CHAT_TYPE_LABELS.get(chat_type, chat_type)

    lines = ["<b>Этот чат</b>"]

    if recipient.chat_id is None:
        lines.append("chat_id: недоступен для этого чата")
    else:
        lines.append(f"chat_id: <code>{recipient.chat_id}</code>")

    lines.append(f"Тип: {escape(label)} (<code>{escape(chat_type)}</code>)")

    copy_value = None if recipient.chat_id is None else str(recipient.chat_id)
    return IdCard(text="\n".join(lines), copy_value=copy_value)


def format_linked_message(link: LinkedMessage) -> IdCard:
    """Форматирует карточку пересланного или процитированного сообщения.

    Args:
        link: Связанное сообщение.

    Returns:
        Карточка с ID автора и `mid` исходного сообщения.
    """
    lines = [f"<b>Пересланное сообщение</b> (<code>{escape(_enum_value(link.type))}</code>)"]

    copy_value: str | None = None
    if link.sender is None:
        lines.append("Автор скрыт настройками приватности")
    else:
        lines.append(f"Автор: {format_user_name(link.sender)}")
        lines.append(f"user_id автора: <code>{link.sender.user_id}</code>")
        if link.sender.username:
            lines.append(f"Username: <code>@{escape(link.sender.username)}</code>")
        copy_value = str(link.sender.user_id)

    if link.chat_id is not None:
        lines.append(f"chat_id источника: <code>{link.chat_id}</code>")

    lines.append(f"mid сообщения: <code>{escape(link.message.mid)}</code>")

    return IdCard(text="\n".join(lines), copy_value=copy_value)


def format_contact(payload: ContactAttachmentPayload) -> IdCard:
    """Форматирует карточку контакта из вложения.

    Args:
        payload: Полезная нагрузка вложения типа `contact`.

    Returns:
        Карточка с `user_id` человека из контакта.
    """
    lines = ["<b>Контакт</b>"]

    if payload.max_info is None:
        lines.append("У этого контакта нет аккаунта MAX — идентификатора нет")
        return IdCard(text="\n".join(lines))

    contact = payload.max_info
    lines.append(f"Имя: {format_user_name(contact)}")
    lines.append(f"user_id: <code>{contact.user_id}</code>")
    if contact.username:
        lines.append(f"Username: <code>@{escape(contact.username)}</code>")
    lines.append(f"Ссылка: <code>max://user/{contact.user_id}</code>")

    return IdCard(text="\n".join(lines), copy_value=str(contact.user_id))


def extract_media_id(attachment: Attachment) -> str | None:
    """Достаёт идентификатор медиа из вложения.

    Разные типы вложений хранят идентификатор по-разному: у фото это
    `payload.photo_id`, у остальных — токен на самом вложении или в payload.

    Args:
        attachment: Вложение сообщения.

    Returns:
        Идентификатор медиа или `None`, если его нет.
    """
    payload = attachment.payload

    photo_id = getattr(payload, "photo_id", None)
    if photo_id is not None:
        return str(photo_id)

    for source in (attachment, payload):
        token = getattr(source, "token", None)
        if token:
            return str(token)

    return None


def format_media(attachment: Attachment) -> IdCard:
    """Форматирует карточку медиа-вложения.

    Args:
        attachment: Вложение сообщения.

    Returns:
        Карточка с типом вложения и идентификатором медиа.
    """
    attachment_type = _enum_value(attachment.type)
    label = ATTACHMENT_TYPE_LABELS.get(attachment_type, attachment_type)

    lines = [
        "<b>Медиа</b>",
        f"Тип: {escape(label)} (<code>{escape(attachment_type)}</code>)",
    ]

    filename = getattr(attachment, "filename", None)
    if filename:
        lines.append(f"Имя файла: {escape(str(filename))}")

    media_id = extract_media_id(attachment)
    if media_id is None:
        lines.append("Идентификатор медиа недоступен")
    else:
        lines.append(f"file_id: <code>{escape(media_id)}</code>")

    return IdCard(text="\n".join(lines), copy_value=media_id)


def merge_cards(cards: list[IdCard]) -> IdCard:
    """Склеивает несколько карточек в один ответ.

    Args:
        cards: Непустой список карточек.

    Returns:
        Карточка с объединённым текстом; значение для копирования берётся
        у первой карточки, где оно есть.
    """
    if not cards:
        return IdCard(text=NOTHING_FOUND_TEXT)

    copy_value = next((card.copy_value for card in cards if card.copy_value), None)
    return IdCard(
        text="\n\n".join(card.text for card in cards),
        copy_value=copy_value,
    )
