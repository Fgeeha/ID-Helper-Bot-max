"""Чтение конфигурации бота из переменных окружения."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

DEFAULT_LOG_LEVEL = "INFO"
# Слушаем все интерфейсы: наружу порт публикует Docker, а не сам процесс
DEFAULT_WEBHOOK_HOST = "0.0.0.0"
DEFAULT_WEBHOOK_PORT = 8080

# Ограничения MAX на секрет вебхука: длина 5-256, только латиница, цифры и дефис
SECRET_MIN_LENGTH = 5
SECRET_MAX_LENGTH = 256
SECRET_ALLOWED = re.compile(r"^[A-Za-z0-9-]+$")


class BotMode(StrEnum):
    """Способ получения обновлений от MAX."""

    POLLING = "polling"
    WEBHOOK = "webhook"


class ConfigError(RuntimeError):
    """Конфигурация окружения неполна или некорректна."""


@dataclass(frozen=True)
class WebhookConfig:
    """Настройки режима webhook.

    Attributes:
        url: Публичный HTTPS-адрес, который регистрируется в MAX.
        host: Интерфейс, который слушает локальный сервер.
        port: Порт локального сервера.
        path: Путь, который обслуживает локальный сервер.
        secret: Секрет для проверки заголовка `X-Max-Bot-Api-Secret`.
    """

    url: str
    host: str = DEFAULT_WEBHOOK_HOST
    port: int = DEFAULT_WEBHOOK_PORT
    path: str = "/"
    secret: str | None = None


@dataclass(frozen=True)
class Config:
    """Настройки бота. Неизменяемая после создания."""

    bot_token: str
    mode: BotMode = BotMode.POLLING
    log_level: str = DEFAULT_LOG_LEVEL
    admin_ids: frozenset[int] = frozenset()
    webhook: WebhookConfig | None = None

    @classmethod
    def from_env(cls) -> Config:
        """Собирает конфигурацию из окружения (и из `.env`, если он есть).

        Returns:
            Заполненная конфигурация.

        Raises:
            ConfigError: Если `BOT_TOKEN` не задан или настройки webhook
                неполны либо некорректны.
        """
        load_dotenv()

        token = os.environ.get("BOT_TOKEN", "").strip()
        if not token:
            msg = (
                "Не задана переменная окружения BOT_TOKEN. "
                "Скопируй .env.example в .env и впиши токен от @MasterBot."
            )
            raise ConfigError(msg)

        mode = parse_mode(os.environ.get("BOT_MODE", BotMode.POLLING))

        return cls(
            bot_token=token,
            mode=mode,
            log_level=os.environ.get("LOG_LEVEL", DEFAULT_LOG_LEVEL).strip().upper(),
            admin_ids=parse_admin_ids(os.environ.get("ADMIN_IDS", "")),
            webhook=webhook_from_env() if mode is BotMode.WEBHOOK else None,
        )


def parse_mode(raw: str) -> BotMode:
    """Разбирает значение `BOT_MODE`.

    Args:
        raw: Значение переменной окружения.

    Returns:
        Режим работы бота.

    Raises:
        ConfigError: Если режим неизвестен.
    """
    value = raw.strip().lower()
    try:
        return BotMode(value)
    except ValueError as e:
        allowed = ", ".join(m.value for m in BotMode)
        msg = f"Неизвестный BOT_MODE: {raw!r}. Допустимые значения: {allowed}."
        raise ConfigError(msg) from e


def parse_port(raw: str) -> int:
    """Разбирает номер порта.

    Args:
        raw: Значение переменной окружения.

    Returns:
        Номер порта.

    Raises:
        ConfigError: Если значение не является портом.
    """
    try:
        port = int(raw)
    except ValueError as e:
        msg = f"WEBHOOK_PORT должен быть числом, получено {raw!r}."
        raise ConfigError(msg) from e

    if not 1 <= port <= 65535:
        msg = f"WEBHOOK_PORT вне допустимого диапазона 1-65535: {port}."
        raise ConfigError(msg)

    return port


def validate_secret(secret: str) -> str | None:
    """Проверяет секрет вебхука по требованиям MAX.

    Проверка делается здесь, а не при подписке: иначе ошибка вылезет уже
    после старта, в глубине библиотеки, и без внятного объяснения.

    Args:
        secret: Значение `WEBHOOK_SECRET`; пустая строка означает «не задан».

    Returns:
        Секрет либо `None`, если он не задан.

    Raises:
        ConfigError: Если секрет не удовлетворяет требованиям MAX.
    """
    if not secret:
        logger.warning(
            "WEBHOOK_SECRET не задан: бот примет запрос от кого угодно, "
            "кто знает адрес вебхука"
        )
        return None

    if not SECRET_MIN_LENGTH <= len(secret) <= SECRET_MAX_LENGTH:
        msg = (
            f"WEBHOOK_SECRET должен быть длиной от {SECRET_MIN_LENGTH} "
            f"до {SECRET_MAX_LENGTH} символов, получено {len(secret)}."
        )
        raise ConfigError(msg)

    if not SECRET_ALLOWED.match(secret):
        msg = "WEBHOOK_SECRET может содержать только латиницу, цифры и дефис."
        raise ConfigError(msg)

    return secret


def webhook_from_env() -> WebhookConfig:
    """Собирает настройки webhook из окружения.

    Путь локального сервера по умолчанию берётся из `WEBHOOK_URL`: так адрес,
    зарегистрированный в MAX, и путь, который бот реально обслуживает, не
    разъезжаются. Переопределить можно через `WEBHOOK_PATH` — это нужно, когда
    перед ботом стоит реверс-прокси, срезающий префикс.

    Returns:
        Настройки режима webhook.

    Raises:
        ConfigError: Если `WEBHOOK_URL` не задан или задан не по HTTPS.
    """
    url = os.environ.get("WEBHOOK_URL", "").strip()
    if not url:
        msg = "В режиме BOT_MODE=webhook нужно задать WEBHOOK_URL — публичный HTTPS-адрес бота."
        raise ConfigError(msg)

    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        msg = f"WEBHOOK_URL должен быть абсолютным HTTPS-адресом, получено {url!r}."
        raise ConfigError(msg)

    path = os.environ.get("WEBHOOK_PATH", "").strip() or parsed.path or "/"
    if not path.startswith("/"):
        path = f"/{path}"

    secret = validate_secret(os.environ.get("WEBHOOK_SECRET", "").strip())

    return WebhookConfig(
        url=url,
        host=os.environ.get("WEBHOOK_HOST", DEFAULT_WEBHOOK_HOST).strip()
        or DEFAULT_WEBHOOK_HOST,
        port=parse_port(os.environ.get("WEBHOOK_PORT", str(DEFAULT_WEBHOOK_PORT))),
        path=path,
        secret=secret,
    )


def parse_admin_ids(raw: str) -> frozenset[int]:
    """Разбирает список ID администраторов, записанных через запятую.

    Нечисловые элементы пропускаются с предупреждением: неверная запись
    в `.env` не должна ронять бота на старте.

    Args:
        raw: Строка вида `"123, 456"`.

    Returns:
        Множество ID администраторов.
    """
    ids: set[int] = set()
    for chunk in raw.split(","):
        item = chunk.strip()
        if not item:
            continue
        try:
            ids.add(int(item))
        except ValueError:
            logger.warning("Пропущен нечисловой ID в ADMIN_IDS: %r", item)
    return frozenset(ids)


def setup_logging(level: str) -> None:
    """Настраивает корневой логгер.

    Args:
        level: Имя уровня логирования, например `"INFO"`.
    """
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
