import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import chats, errors, start
from app.bot.middlewares.access import AccessMiddleware
from app.config import settings

log = logging.getLogger(__name__)


def build_bot_and_dp(userbot_client) -> tuple:
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # Pass userbot client to all handlers via data
    dp["userbot_client"] = userbot_client

    # Register access middleware on all updates
    dp.update.middleware(AccessMiddleware())

    # Register routers — errors first so it catches exceptions from other routers
    dp.include_router(errors.router)
    dp.include_router(start.router)
    dp.include_router(chats.router)

    return bot, dp
