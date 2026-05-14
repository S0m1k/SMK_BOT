from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import app.core.bus as bus
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.db.base import async_session_maker
from app.db.repo import get_active_keywords, get_setting, set_setting

log = logging.getLogger(__name__)
router = Router(name="status")

_start_time = datetime.now(timezone.utc)


def _uptime_str() -> str:
    delta = datetime.now(timezone.utc) - _start_time
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m = rem // 60
    return f"{h}ч {m}м"


async def _status_text() -> str:
    async with async_session_maker() as session:
        keywords = await get_active_keywords(session)
        receiver_id = await get_setting(session, "receiver_chat_id")
    status = "АКТИВЕН ✅" if bus.monitoring_enabled else "НА ПАУЗЕ ⏸"
    receiver = receiver_id or "не задан"
    return (
        f"Статус бота\n\n"
        f"Мониторинг: {status}\n"
        f"Чатов: {len(bus.active_chat_ids)}\n"
        f"Слов: {len(keywords)}\n"
        f"Получатель: {receiver}\n"
        f"Очередь лидов: {bus.lead_queue.qsize()}\n"
        f"Uptime: {_uptime_str()}"
    )


@router.message(Command("status"))
@router.callback_query(F.data == "cb:menu:status")
async def cmd_status(event, is_owner: bool = False) -> None:
    text = await _status_text()
    if isinstance(event, Message):
        await event.answer(text)
    else:
        await event.message.edit_text(text, reply_markup=main_menu_keyboard(is_owner))
        await event.answer()


@router.message(Command("stop"))
@router.callback_query(F.data == "cb:menu:toggle")
async def cmd_stop_or_toggle(event, is_owner: bool = False) -> None:
    msg = event if isinstance(event, Message) else event.message
    is_command_stop = isinstance(event, Message)

    if is_command_stop:
        bus.monitoring_enabled = False
        async with async_session_maker() as session:
            await set_setting(session, "monitoring_enabled", "0")
        await msg.answer("Мониторинг приостановлен.")
    else:
        bus.monitoring_enabled = not bus.monitoring_enabled
        val = "1" if bus.monitoring_enabled else "0"
        async with async_session_maker() as session:
            await set_setting(session, "monitoring_enabled", val)
        status_notice = "Мониторинг возобновлён." if bus.monitoring_enabled else "Мониторинг приостановлен."
        await msg.edit_text(await _status_text(), reply_markup=main_menu_keyboard(is_owner))
        await event.answer(status_notice)


@router.message(Command("startbot"))
async def cmd_startbot(message: Message) -> None:
    bus.monitoring_enabled = True
    async with async_session_maker() as session:
        await set_setting(session, "monitoring_enabled", "1")
    await message.answer("Мониторинг возобновлён.")
