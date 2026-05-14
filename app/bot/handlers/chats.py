import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.chats import PAGE_SIZE, chats_list_keyboard
from app.bot.keyboards.common import cancel_keyboard, confirm_keyboard
from app.bot.states import AddChat
from app.core.bus import reload_caches
from app.db.base import async_session_maker
from app.db.repo import add_chat, deactivate_chat, get_chats_page
from app.userbot.chat_ops import join_chat, leave_chat

log = logging.getLogger(__name__)
router = Router(name="chats")


async def _send_chats_page(target, page: int) -> None:
    """Send or edit chats list page. target is Message or CallbackQuery."""
    async with async_session_maker() as session:
        chats, total = await get_chats_page(session, page, PAGE_SIZE)
    kb = chats_list_keyboard(chats, page, total)
    text = f"📥 Чаты (всего: {total})"
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=kb)
        await target.answer()
    else:
        await target.answer(text, reply_markup=kb)


# ---- List ----

@router.callback_query(F.data == "cb:menu:chats")
async def cb_menu_chats(callback: CallbackQuery) -> None:
    await _send_chats_page(callback, 1)


@router.callback_query(F.data.startswith("cb:chat:list:"))
async def cb_chat_list_page(callback: CallbackQuery) -> None:
    page = int(callback.data.split(":")[3])
    await _send_chats_page(callback, page)


@router.message(Command("listchats"))
async def cmd_listchats(message: Message) -> None:
    async with async_session_maker() as session:
        chats, total = await get_chats_page(session, 1, 50)
    if not chats:
        await message.answer("Нет активных чатов.")
        return
    lines = [f"#{c.id} {c.title} (@{c.username or '—'})" for c in chats]
    await message.answer("Активные чаты:\n" + "\n".join(lines))


# ---- Add via FSM ----

@router.callback_query(F.data == "cb:chat:add")
async def cb_chat_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddChat.waiting_link)
    await callback.message.answer(
        "Введите ссылку или @username чата:", reply_markup=cancel_keyboard()
    )
    await callback.answer()


@router.message(AddChat.waiting_link)
async def fsm_chat_link_received(
    message: Message, state: FSMContext, userbot_client, is_owner: bool = False
) -> None:
    link = message.text.strip() if message.text else ""
    if not link:
        await message.answer("Пожалуйста, введите ссылку или @username.")
        return

    await state.clear()
    await message.answer("⏳ Вступаю в чат...")

    try:
        info = await join_chat(userbot_client, link)
    except ValueError as e:
        err = str(e).lower()
        if "flood" in err or "wait" in err:
            await message.answer(f"⏳ Telegram ограничил запрос. {e}")
        else:
            await message.answer(f"❌ {e}")
        return

    uid = message.from_user.id if message.from_user else 0
    async with async_session_maker() as session:
        existing = await _get_chat_by_tg_id(session, info["tg_id"])
        if existing and existing.active:
            await message.answer(f"ℹ️ Чат «{existing.title}» уже добавлен.")
            return
        await add_chat(
            session,
            tg_id=info["tg_id"],
            title=info["title"],
            username=info["username"],
            invite_link=link if link.startswith("http") else None,
            added_by=uid,
        )
        await reload_caches(session)

    await message.answer(f"✅ Добавлено: {info['title']}")


async def _get_chat_by_tg_id(session, tg_id: int):
    from app.db.repo import get_chat_by_tg_id
    return await get_chat_by_tg_id(session, tg_id)


# ---- Add via slash command ----

@router.message(Command("addchat"))
async def cmd_addchat(
    message: Message, state: FSMContext, userbot_client
) -> None:
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await state.set_state(AddChat.waiting_link)
        await message.answer(
            "Введите ссылку или @username чата:", reply_markup=cancel_keyboard()
        )
        return

    link = args[1].strip()
    await message.answer("⏳ Вступаю в чат...")
    try:
        info = await join_chat(userbot_client, link)
    except ValueError as e:
        err = str(e).lower()
        if "flood" in err or "wait" in err:
            await message.answer(f"⏳ Telegram ограничил запрос. {e}")
        else:
            await message.answer(f"❌ {e}")
        return

    uid = message.from_user.id if message.from_user else 0
    async with async_session_maker() as session:
        existing = await _get_chat_by_tg_id(session, info["tg_id"])
        if existing and existing.active:
            await message.answer(f"ℹ️ Чат «{existing.title}» уже добавлен.")
            return
        await add_chat(
            session,
            tg_id=info["tg_id"],
            title=info["title"],
            username=info["username"],
            invite_link=link if link.startswith("http") else None,
            added_by=uid,
        )
        await reload_caches(session)

    await message.answer(f"✅ Добавлено: {info['title']}")


# ---- Delete ----

@router.callback_query(F.data.startswith("cb:chat:del:"))
async def cb_chat_del(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    chat_id = int(parts[3])
    await callback.message.edit_text(
        "Удалить чат из мониторинга?",
        reply_markup=confirm_keyboard(
            yes_data=f"cb:chat:del_yes:{chat_id}",
            no_data=f"cb:chat:del_no:{chat_id}",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cb:chat:del_no:"))
async def cb_chat_del_no(callback: CallbackQuery) -> None:
    await _send_chats_page(callback, 1)


@router.callback_query(F.data.startswith("cb:chat:del_yes:"))
async def cb_chat_del_yes(callback: CallbackQuery, userbot_client) -> None:
    parts = callback.data.split(":")
    chat_db_id = int(parts[3])

    async with async_session_maker() as session:
        from sqlalchemy import select
        from app.db.models import Chat
        result = await session.execute(select(Chat).where(Chat.id == chat_db_id))
        chat = result.scalar_one_or_none()
        if chat is None:
            await callback.answer("Чат не найден.", show_alert=True)
            return
        tg_id = chat.tg_id
        await deactivate_chat(session, chat_db_id)
        await reload_caches(session)

    await leave_chat(userbot_client, tg_id)
    await _send_chats_page(callback, 1)


@router.message(Command("removechat"))
async def cmd_removechat(message: Message, userbot_client) -> None:
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /removechat <chat_db_id>")
        return
    try:
        chat_db_id = int(args[1].strip())
    except ValueError:
        await message.answer("ID должен быть числом.")
        return

    async with async_session_maker() as session:
        from sqlalchemy import select
        from app.db.models import Chat
        result = await session.execute(select(Chat).where(Chat.id == chat_db_id))
        chat = result.scalar_one_or_none()
        if chat is None:
            await message.answer("Чат не найден.")
            return
        tg_id = chat.tg_id
        title = chat.title
        await deactivate_chat(session, chat_db_id)
        await reload_caches(session)

    await leave_chat(userbot_client, tg_id)
    await message.answer(f"✅ Чат «{title}» удалён из мониторинга.")


# ---- Info (placeholder — just acknowledge) ----

@router.callback_query(F.data.startswith("cb:chat:info:"))
async def cb_chat_info(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    chat_db_id = int(parts[3])
    async with async_session_maker() as session:
        from sqlalchemy import select
        from app.db.models import Chat
        result = await session.execute(select(Chat).where(Chat.id == chat_db_id))
        chat = result.scalar_one_or_none()
    if chat is None:
        await callback.answer("Чат не найден.", show_alert=True)
        return
    username_str = f"@{chat.username}" if chat.username else "—"
    text = (
        f"ID в БД: {chat.id}\n"
        f"Telegram ID: {chat.tg_id}\n"
        f"Название: {chat.title}\n"
        f"Username: {username_str}\n"
        f"Активен: {'да' if chat.active else 'нет'}"
    )
    await callback.answer(text[:200], show_alert=True)
