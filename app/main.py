import asyncio
import logging
import signal

import app.core.bus as bus
from app.bot.lead_sender import lead_sender_loop
from app.core.bus import reload_caches
from app.db.base import async_session_maker, init_db
from app.db.repo import get_or_create_category, get_setting, set_setting
from app.userbot.client import build_client
from app.userbot.listener import register_handlers
from app.bot.dispatcher import build_bot_and_dp
from app.utils.logger import setup_logging
from app.utils.heartbeat import heartbeat_loop

log = logging.getLogger(__name__)

_DEFAULT_CATEGORIES = [
    "СРО и специалисты",
    "Лицензии и реестры",
    "ЭПБ",
    "Документация и ИСО",
    "Сертификация и экспорт",
    "Тендеры",
    "Прочее",
]


async def _bootstrap(session) -> None:  # type: ignore[no-untyped-def]
    for name in _DEFAULT_CATEGORIES:
        await get_or_create_category(session, name)
    if await get_setting(session, "monitoring_enabled") is None:
        await set_setting(session, "monitoring_enabled", "1")


async def main() -> None:
    setup_logging()
    await init_db()

    async with async_session_maker() as session:
        await _bootstrap(session)
        await reload_caches(session)
        monitoring_val = await get_setting(session, "monitoring_enabled")
        if monitoring_val == "0":
            bus.monitoring_enabled = False
            log.info("monitoring disabled (persisted setting)")

    userbot = build_client()
    # Uses saved session file; no interactive prompt in normal mode
    await userbot.start(phone=lambda: None)  # type: ignore[arg-type]
    register_handlers(userbot)

    bot, dp = build_bot_and_dp(userbot)

    stop_event = asyncio.Event()

    def _on_signal() -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _on_signal)
    except NotImplementedError:
        pass  # Windows does not support add_signal_handler

    tasks = [
        asyncio.create_task(userbot.run_until_disconnected(), name="userbot"),
        asyncio.create_task(dp.start_polling(bot, handle_signals=False), name="bot"),
        asyncio.create_task(lead_sender_loop(bot), name="lead-sender"),
        asyncio.create_task(heartbeat_loop(), name="heartbeat"),
    ]

    await stop_event.wait()
    log.info("shutting down")
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await userbot.disconnect()
    await bot.session.close()
    log.info("shutdown complete")
