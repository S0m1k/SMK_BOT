from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.admins import admins_list_keyboard
from app.bot.keyboards.common import cancel_keyboard, confirm_keyboard
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.states import AddAdmin
from app.config import settings as app_settings
from app.db.base import async_session_maker
from app.db.repo import add_admin, deactivate_admin, list_admins

log = logging.getLogger(__name__)
router = Router(name="admins")


async def _show_admin_list(target, is_owner: bool = False) -> None:
    async with async_session_maker() as session:
        admins = await list_admins(session)
    msg = target if isinstance(target, Message) else target.message
    text = f"👮 Админы ({len(admins)} в БД + {len(app_settings.owner_ids)} owner из .env)"
    await msg.answer(text, reply_markup=admins_list_keyboard(admins))


@router.callback_query(F.data == "cb:menu:admins")
async def cb_admins_menu(callback: CallbackQuery, is_owner: bool = False) -> None:
    if not is_owner:
        await callback.answer("Только OWNER", show_alert=True)
        return
    async with async_session_maker() as session:
        admins = await list_admins(session)
    text = f"👮 Админы ({len(admins)} в БД)"
    await callback.message.edit_text(text, reply_markup=admins_list_keyboard(admins))
    await callback.answer()


@router.message(Command("listadmins"))
async def cmd_list_admins(message: Message, is_owner: bool = False) -> None:
    await _show_admin_list(message, is_owner)


@router.callback_query(F.data == "cb:admin:add")
@router.message(Command("addadmin"))
async def cmd_add_admin(event, state: FSMContext, is_owner: bool = False) -> None:
    if not is_owner:
        msg = event if isinstance(event, Message) else event.message
        await msg.answer("Только OWNER может добавлять админов.")
        if isinstance(event, CallbackQuery):
            await event.answer()
        return
    msg = event if isinstance(event, Message) else event.message
    # Support /addadmin <user_id> inline
    if isinstance(event, Message) and event.text:
        parts = event.text.split(maxsplit=1)
        if len(parts) == 2 and parts[1].lstrip("-").isdigit():
            uid = int(parts[1])
            await _do_add_admin(msg, uid, None, None, event.from_user.id, is_owner)
            return
    await state.set_state(AddAdmin.waiting_contact)
    await msg.answer(
        "Перешли сообщение от пользователя которого хочешь сделать админом, "
        "или отправь его числовой user_id.",
        reply_markup=cancel_keyboard(),
    )
    if isinstance(event, CallbackQuery):
        await event.answer()


@router.message(AddAdmin.waiting_contact)
async def process_add_admin(message: Message, state: FSMContext, is_owner: bool = False) -> None:
    tg_id: int | None = None
    username: str | None = None
    full_name: str | None = None

    if message.forward_from:
        tg_id = message.forward_from.id
        username = message.forward_from.username
        full_name = " ".join(filter(None, [
            message.forward_from.first_name, message.forward_from.last_name
        ])) or None
    elif message.text and message.text.lstrip("-").isdigit():
        tg_id = int(message.text.strip())
    else:
        await message.answer("Не распознал. Перешли сообщение или введи числовой user_id.")
        return

    await state.clear()
    await _do_add_admin(message, tg_id, username, full_name, message.from_user.id, is_owner)


async def _do_add_admin(
    msg: Message,
    tg_id: int,
    username: str | None,
    full_name: str | None,
    added_by: int,
    is_owner: bool,
) -> None:
    if tg_id in app_settings.owner_ids:
        await msg.answer("Этот пользователь уже является OWNER.")
        return
    async with async_session_maker() as session:
        await add_admin(session, tg_id, username, full_name, added_by)
    name = full_name or username or str(tg_id)
    await msg.answer(
        f"✅ Админ добавлен: {name} (ID: {tg_id})",
        reply_markup=main_menu_keyboard(is_owner),
    )


@router.callback_query(F.data.startswith("cb:admin:del:"))
async def cb_admin_del(callback: CallbackQuery, is_owner: bool = False) -> None:
    if not is_owner:
        await callback.answer("Только OWNER", show_alert=True)
        return
    tg_id = int(callback.data.split(":")[-1])
    await callback.message.edit_reply_markup(
        reply_markup=confirm_keyboard(f"cb:admin:del_yes:{tg_id}", f"cb:admin:del_no:{tg_id}")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cb:admin:del_yes:"))
async def cb_admin_del_confirm(callback: CallbackQuery, is_owner: bool = False) -> None:
    tg_id = int(callback.data.split(":")[-1])
    async with async_session_maker() as session:
        removed = await deactivate_admin(session, tg_id)
    if removed:
        await callback.message.edit_text(f"✅ Админ {tg_id} удалён.")
    else:
        await callback.message.edit_text(f"Не найден админ с ID {tg_id}.")
    await callback.answer()


@router.callback_query(F.data.startswith("cb:admin:del_no:"))
async def cb_admin_del_cancel(callback: CallbackQuery) -> None:
    async with async_session_maker() as session:
        admins = await list_admins(session)
    await callback.message.edit_reply_markup(reply_markup=admins_list_keyboard(admins))
    await callback.answer()


@router.message(Command("removeadmin"))
async def cmd_remove_admin(message: Message, is_owner: bool = False) -> None:
    if not is_owner:
        await message.answer("Только OWNER может удалять админов.")
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2 or not parts[1].lstrip("-").isdigit():
        await message.answer("Использование: /removeadmin <user_id>")
        return
    tg_id = int(parts[1])
    if tg_id in app_settings.owner_ids:
        await message.answer("OWNER нельзя удалить через бота.")
        return
    async with async_session_maker() as session:
        removed = await deactivate_admin(session, tg_id)
    await message.answer("✅ Удалён." if removed else "Не найден.")
