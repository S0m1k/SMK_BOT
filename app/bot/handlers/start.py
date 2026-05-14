import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main_menu import main_menu_keyboard
from app.core.bus import active_chat_ids, monitoring_enabled
from app.db.base import async_session_maker
from app.db.repo import get_active_keywords

log = logging.getLogger(__name__)
router = Router(name="start")


async def _status_text(is_owner: bool) -> str:
    async with async_session_maker() as session:
        keywords = await get_active_keywords(session)
    status = "АКТИВЕН ✅" if monitoring_enabled else "НА ПАУЗЕ ⏸"
    return (
        f"СМК-БОТ — мониторинг {status}\n"
        f"Чатов: {len(active_chat_ids)}   Слов: {len(keywords)}"
    )


@router.message(Command("start"))
async def cmd_start(message: Message, is_owner: bool = False) -> None:
    text = await _status_text(is_owner)
    await message.answer(text, reply_markup=main_menu_keyboard(is_owner))


@router.callback_query(lambda c: c.data == "cb:menu:back_main")
async def cb_back_main(callback: CallbackQuery, is_owner: bool = False) -> None:
    text = await _status_text(is_owner)
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard(is_owner))
    await callback.answer()


@router.callback_query(lambda c: c.data == "cb:noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(lambda c: c.data == "cb:cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.delete()
    await callback.answer("Отменено")
