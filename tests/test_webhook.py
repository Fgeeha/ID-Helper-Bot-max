"""Интеграционные тесты webhook-эндпоинта.

Сеть не используется: инициализация диспетчера и отправка ответа
подменяются заглушками, поднимается только локальный aiohttp-сервер.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

import pytest
from aiohttp.test_utils import TestClient, TestServer
from maxapi import Bot
from maxapi.types import Message
from maxapi.webhook.aiohttp import AiohttpMaxWebhook

from bot.__main__ import build_dispatcher

WEBHOOK_PATH = "/max/hook"
SECRET = "s3cret"

MESSAGE_CREATED_PAYLOAD: dict[str, Any] = {
    "update_type": "message_created",
    "timestamp": 1_700_000_000_000,
    "message": {
        "sender": {
            "user_id": 12345,
            "first_name": "Никита",
            "last_name": None,
            "username": "nkolesnikov",
            "is_bot": False,
            "last_activity_time": 0,
        },
        "recipient": {"user_id": 12345, "chat_id": -42, "chat_type": "dialog"},
        "timestamp": 1_700_000_000_000,
        "body": {"mid": "mid-1", "seq": 1, "text": "/myid"},
    },
}


@pytest.fixture
def sent_messages(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Перехватывает исходящие ответы бота вместо обращения к API."""
    captured: list[dict[str, Any]] = []

    async def fake_answer(self: Message, *args: Any, **kwargs: Any) -> None:
        captured.append(kwargs)

    monkeypatch.setattr(Message, "answer", fake_answer)
    return captured


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Поднимает webhook-приложение с настоящими роутерами бота."""

    async def fake_startup(self: Any, bot: Bot) -> None:
        """Пропускает обращение к `getMe` при инициализации диспетчера."""
        self.bot = bot
        self.routers.append(self)
        self._prepare_handlers(bot)
        self._ready = True

    monkeypatch.setattr("maxapi.dispatcher.Dispatcher.startup", fake_startup)

    dp = build_dispatcher()
    # auto_requests=False — как в проде: событие разбирается без обращений к API
    bot = Bot("test-token", auto_requests=False)
    webhook = AiohttpMaxWebhook(dp=dp, bot=bot, secret=SECRET)

    test_client = TestClient(TestServer(webhook.create_app(path=WEBHOOK_PATH)))
    await test_client.start_server()
    try:
        yield test_client
    finally:
        await test_client.close()


class TestWebhookEndpoint:
    """Приём обновлений по HTTP."""

    async def test_delivers_update_to_handler(
        self, client: TestClient, sent_messages: list[dict[str, Any]]
    ) -> None:
        response = await client.post(
            WEBHOOK_PATH,
            json=MESSAGE_CREATED_PAYLOAD,
            headers={"X-Max-Bot-Api-Secret": SECRET},
        )

        assert response.status == HTTPStatus.OK
        assert await response.json() == {"ok": True}
        assert len(sent_messages) == 1
        assert "user_id: <code>12345</code>" in sent_messages[0]["text"]

    async def test_rejects_wrong_secret(
        self, client: TestClient, sent_messages: list[dict[str, Any]]
    ) -> None:
        response = await client.post(
            WEBHOOK_PATH,
            json=MESSAGE_CREATED_PAYLOAD,
            headers={"X-Max-Bot-Api-Secret": "wrong"},
        )

        assert response.status == HTTPStatus.FORBIDDEN
        assert sent_messages == []

    async def test_rejects_missing_secret(
        self, client: TestClient, sent_messages: list[dict[str, Any]]
    ) -> None:
        response = await client.post(WEBHOOK_PATH, json=MESSAGE_CREATED_PAYLOAD)

        assert response.status == HTTPStatus.FORBIDDEN
        assert sent_messages == []

    async def test_unknown_path_is_not_served(self, client: TestClient) -> None:
        response = await client.post(
            "/other",
            json=MESSAGE_CREATED_PAYLOAD,
            headers={"X-Max-Bot-Api-Secret": SECRET},
        )

        assert response.status == HTTPStatus.NOT_FOUND
