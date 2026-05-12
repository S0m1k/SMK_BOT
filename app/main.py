import asyncio
import logging

from app.core.bus import reload_caches
from app.db.base import async_session_maker, init_db
from app.db.repo import get_or_create_category, get_setting, set_setting
from app.utils.logger import setup_logging

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


async def _bootstrap(session):  # type: ignore[no-untyped-def]
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

    log.info("started")
    # Stub: userbot + aiogram tasks wired here from Stage 4 onwards
    await asyncio.sleep(0)
