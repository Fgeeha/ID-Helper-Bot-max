"""Точка входа: сборка диспетчера и запуск в выбранном режиме."""

from __future__ import annotations

import asyncio
import contextlib
import logging

from maxapi import Bot, Dispatcher
from maxapi.exceptions.max import InvalidToken

from bot.config import BotMode, Config, ConfigError, WebhookConfig, setup_logging
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


async def run_polling(bot: Bot, dp: Dispatcher) -> None:
    """Запускает бота в режиме long polling.

    Args:
        bot: Экземпляр бота.
        dp: Диспетчер с подключёнными роутерами.
    """
    # Пока жива хоть одна подписка на вебхук, MAX не отдаёт события в polling.
    with contextlib.suppress(Exception):
        await bot.delete_webhook()

    logger.info("Запускаю polling")
    await dp.start_polling(bot)


async def run_webhook(bot: Bot, dp: Dispatcher, config: WebhookConfig) -> None:
    """Регистрирует подписку и поднимает сервер вебхука.

    Args:
        bot: Экземпляр бота.
        dp: Диспетчер с подключёнными роутерами.
        config: Настройки режима webhook.
    """
    # Снимаем прежние подписки, иначе события начнут дублироваться на старый адрес.
    with contextlib.suppress(Exception):
        await bot.delete_webhook()

    await bot.subscribe_webhook(url=config.url, secret=config.secret)
    logger.info("Подписка на вебхук зарегистрирована: %s", config.url)

    logger.info(
        "Запускаю сервер вебхука на %s:%s%s", config.host, config.port, config.path
    )
    await dp.handle_webhook(
        bot,
        host=config.host,
        port=config.port,
        path=config.path,
        secret=config.secret,
    )


async def main() -> None:
    """Читает конфигурацию и запускает бота в выбранном режиме."""
    config = Config.from_env()
    setup_logging(config.log_level)

    # auto_requests=False: иначе на каждое событие уходит лишний запрос
    # get_chat_by_id. Хендлеры берут всё из payload, так что чат нам не нужен,
    # а лимит MAX — 30 запросов в секунду.
    bot = Bot(config.bot_token, auto_requests=False)
    dp = build_dispatcher()

    logger.info("Режим работы: %s", config.mode.value)
    try:
        if config.mode is BotMode.WEBHOOK:
            if config.webhook is None:
                msg = "Режим webhook выбран, но его настройки не собраны."
                raise ConfigError(msg)
            await run_webhook(bot, dp, config.webhook)
        else:
            await run_polling(bot, dp)
    finally:
        await bot.close_session()


def cli() -> None:
    """Синхронная обёртка над `main()` для `project.scripts`.

    Raises:
        SystemExit: Если конфигурация окружения неполна или токен неверен.
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
