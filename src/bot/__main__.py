"""Точка входа: сборка диспетчера и запуск polling."""

from __future__ import annotations

import asyncio
import contextlib
import logging

from maxapi import Bot, Dispatcher
from maxapi.exceptions.max import InvalidToken

from bot.config import Config, ConfigError, setup_logging
from bot.handlers import ROUTERS

logger = logging.getLogger(__name__)


def build_dispatcher() -> Dispatcher:
    """Собирает диспетчер с подключёнными роутерами.

    Returns:
        Готовый к запуску диспетчер.
    """
    dp = Dispatcher()
    dp.include_routers(*ROUTERS)
    return dp


async def main() -> None:
    """Запускает бота в режиме long polling."""
    config = Config.from_env()
    setup_logging(config.log_level)

    bot = Bot(config.bot_token)
    dp = build_dispatcher()

    # Если раньше был настроен вебхук, polling не получит события,
    # пока подписка не снята.
    with contextlib.suppress(Exception):
        await bot.delete_webhook()

    logger.info("Запускаю polling")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.close_session()


def cli() -> None:
    """Синхронная обёртка над `main()` для `project.scripts`.

    Raises:
        SystemExit: Если конфигурация окружения неполна.
    """
    try:
        asyncio.run(main())
    except ConfigError as e:
        raise SystemExit(f"Ошибка конфигурации: {e}") from e
    except InvalidToken as e:
        raise SystemExit("Неверный BOT_TOKEN — проверь значение в .env") from e
    except KeyboardInterrupt:
        logger.info("Остановлено пользователем")


if __name__ == "__main__":
    cli()
