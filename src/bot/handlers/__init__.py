"""Роутеры бота.

Порядок в `ROUTERS` важен: диспетчер отдаёт событие первому подходящему
обработчику, поэтому catch-all роутер должен идти последним, иначе он
перехватит команды.
"""

from .callbacks import callbacks_router
from .ids import commands_router, fallback_router

ROUTERS = (commands_router, callbacks_router, fallback_router)

__all__ = [
    "ROUTERS",
    "callbacks_router",
    "commands_router",
    "fallback_router",
]
