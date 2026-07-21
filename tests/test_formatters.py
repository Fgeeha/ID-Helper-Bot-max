"""Тесты форматтеров идентификаторов. Без сети и без реального бота."""

from __future__ import annotations

import pytest
from maxapi.enums.chat_type import ChatType
from maxapi.types import (
    ContactAttachmentPayload,
    LinkedMessage,
    MessageBody,
    Recipient,
    User,
)
from maxapi.types.attachments.image import Image
from maxapi.types.attachments.video import Video

from bot.formatters import (
    NOTHING_FOUND_TEXT,
    IdCard,
    format_chat,
    format_contact,
    format_linked_message,
    format_media,
    format_user,
    merge_cards,
)


def make_user(**overrides: object) -> User:
    """Собирает пользователя с заполненными обязательными полями."""
    fields: dict[str, object] = {
        "user_id": 12345,
        "first_name": "Никита",
        "last_name": "Колесников",
        "username": "nkolesnikov",
        "is_bot": False,
        "last_activity_time": 0,
    }
    fields.update(overrides)
    return User(**fields)  # type: ignore[arg-type]


class TestFormatUser:
    """Карточка обычного пользователя."""

    def test_contains_all_identifiers(self) -> None:
        card = format_user(make_user())

        assert "user_id: <code>12345</code>" in card.text
        assert "Никита Колесников" in card.text
        assert "<code>@nkolesnikov</code>" in card.text
        assert "<code>max://user/12345</code>" in card.text
        assert card.copy_value == "12345"

    def test_without_username_and_last_name(self) -> None:
        card = format_user(make_user(username=None, last_name=None))

        assert "Имя: Никита" in card.text
        assert "@" not in card.text
        assert card.copy_value == "12345"

    def test_marks_bot(self) -> None:
        assert "Это бот" in format_user(make_user(is_bot=True)).text

    def test_escapes_html_in_name(self) -> None:
        card = format_user(make_user(first_name="<b>hack</b>", last_name=None))

        assert "<b>hack</b>" not in card.text.removeprefix("<b>Твой ID</b>")
        assert "&lt;b&gt;hack&lt;/b&gt;" in card.text

    def test_custom_title(self) -> None:
        assert "<b>Автор</b>" in format_user(make_user(), title="Автор").text


class TestFormatContact:
    """Карточка контакта."""

    def test_uses_max_info(self) -> None:
        payload = ContactAttachmentPayload(
            vcf_info=None,
            hash=None,
            max_info=make_user(user_id=777, first_name="Иван", last_name=None),
        )

        card = format_contact(payload)

        assert "<b>Контакт</b>" in card.text
        assert "user_id: <code>777</code>" in card.text
        assert "Имя: Иван" in card.text
        assert "<code>max://user/777</code>" in card.text
        assert card.copy_value == "777"

    def test_contact_without_max_account(self) -> None:
        payload = ContactAttachmentPayload(vcf_info="BEGIN:VCARD", hash=None, max_info=None)

        card = format_contact(payload)

        assert "нет аккаунта MAX" in card.text
        assert card.copy_value is None


class TestFormatChat:
    """Карточка чата."""

    @pytest.mark.parametrize(
        ("chat_type", "label"),
        [
            (ChatType.DIALOG, "личный диалог"),
            (ChatType.CHAT, "групповой чат"),
            (ChatType.CHANNEL, "канал"),
        ],
    )
    def test_chat_type_label(self, chat_type: ChatType, label: str) -> None:
        card = format_chat(Recipient(user_id=None, chat_id=-42, chat_type=chat_type))

        assert "chat_id: <code>-42</code>" in card.text
        assert label in card.text
        assert card.copy_value == "-42"

    def test_missing_chat_id(self) -> None:
        card = format_chat(Recipient(user_id=1, chat_id=None, chat_type=ChatType.DIALOG))

        assert "недоступен" in card.text
        assert card.copy_value is None


class TestFormatLinkedMessage:
    """Карточка пересланного сообщения."""

    def test_shows_author_and_mid(self) -> None:
        link = LinkedMessage(
            type="forward",
            sender=make_user(user_id=999, first_name="Автор", last_name=None, username=None),
            chat_id=-100,
            message=MessageBody(mid="mid-abc", seq=1, text="привет", attachments=None),
        )

        card = format_linked_message(link)

        assert "user_id автора: <code>999</code>" in card.text
        assert "mid сообщения: <code>mid-abc</code>" in card.text
        assert "chat_id источника: <code>-100</code>" in card.text
        assert card.copy_value == "999"

    def test_hidden_sender(self) -> None:
        link = LinkedMessage(
            type="forward",
            sender=None,
            chat_id=None,
            message=MessageBody(mid="mid-xyz", seq=1, text=None, attachments=None),
        )

        card = format_linked_message(link)

        assert "скрыт" in card.text
        assert "<code>mid-xyz</code>" in card.text
        assert card.copy_value is None


class TestFormatMedia:
    """Карточка медиа-вложения."""

    def test_photo_uses_photo_id(self) -> None:
        attachment = Image.model_validate(
            {"type": "image", "payload": {"photo_id": 555, "token": "tok", "url": "http://x"}}
        )

        card = format_media(attachment)

        assert "изображение" in card.text
        assert "<code>555</code>" in card.text
        assert card.copy_value == "555"

    def test_video_falls_back_to_token(self) -> None:
        attachment = Video.model_validate(
            {"type": "video", "payload": None, "token": "video-token"}
        )

        card = format_media(attachment)

        assert "видео" in card.text
        assert "<code>video-token</code>" in card.text
        assert card.copy_value == "video-token"

    def test_media_without_identifier(self) -> None:
        attachment = Video.model_validate({"type": "video", "payload": None})

        card = format_media(attachment)

        assert "недоступен" in card.text
        assert card.copy_value is None


class TestMergeCards:
    """Склейка нескольких карточек."""

    def test_empty_returns_hint(self) -> None:
        assert merge_cards([]).text == NOTHING_FOUND_TEXT

    def test_takes_first_available_copy_value(self) -> None:
        merged = merge_cards(
            [
                IdCard(text="раз"),
                IdCard(text="два", copy_value="7"),
                IdCard(text="три", copy_value="8"),
            ]
        )

        assert merged.text == "раз\n\nдва\n\nтри"
        assert merged.copy_value == "7"
