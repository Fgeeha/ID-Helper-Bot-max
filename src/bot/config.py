"""Чтение конфигурации бота из переменных окружения."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

DEFAULT_LOG_LEVEL = "INFO"


class ConfigError(RuntimeError):
    """Конфигурация окружения неполна или некорректна."""


@dataclass(frozen=True)
class Config:
    """Настройки бота. Неизменяемая после создания."""

    bot_token: str
    log_level: str = DEFAULT_LOG_LEVEL
    admin_ids: frozenset[int] = frozenset()

    @classmethod
    def from_env(cls) -> Config:
        """Собирает конфигурацию из окружения (и из `.env`, если он есть).

        Returns:
            Заполненная конфигурация.

        Raises:
            ConfigError: Если `BOT_TOKEN` не задан или пуст.
        """
        load_dotenv()

        token = os.environ.get("BOT_TOKEN", "").strip()
        if not token:
            msg = (
                "Не задана переменная окружения BOT_TOKEN. "
                "Скопируй .env.example в .env и впиши токен от @MasterBot."
            )
            raise ConfigError(msg)

        return cls(
            bot_token=token,
            log_level=os.environ.get("LOG_LEVEL", DEFAULT_LOG_LEVEL).strip().upper(),
            admin_ids=parse_admin_ids(os.environ.get("ADMIN_IDS", "")),
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
