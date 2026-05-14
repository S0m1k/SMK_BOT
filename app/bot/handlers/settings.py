import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.keyboards.common import cancel_keyboard
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.states import SetReceiver
from app.db.base import async_session_maker
from app.db.repo import set_setting

log = logging.getLogger(__name__)
router = Router(name="settings")


def _settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Установить получателя", callback_data="cb:settings:setreceiver")],
        [InlineKeyboardButton(text="↩ Назад", callback_data="cb:menu:back_main")],
    ])


@router.callback_query(F.data == "cb:menu:settings")
async def cb_settings_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "⚙ Настройки",
        reply_markup=_settings_keyboard(),
    )
    await callback.answer()


@router.message(Command("setreceiver"))
@router.callback_query(F.data == "cb:settings:setreceiver")
async def cmd_set_receiver(event: Message | CallbackQuery, state: FSMContext) -> None:
    msg = event if isinstance(event, Message) else event.message
    await state.set_state(SetReceiver.waiting_forward)
    await msg.answer(
        "Перешли любое сообщение из чата менеджеров, или отправь его числовой ID.",
        reply_markup=cancel_keyboard(),
    )
    if isinstance(event, CallbackQuery):
        await event.answer()


@router.message(SetReceiver.waiting_forward)
async def process_receiver(message: Message, state: FSMContext, is_owner: bool = False) -> None:
    chat_id: int | None = None
    title: str

    if message.forward_from_chat:
        chat_id = message.forward_from_chat.id
        title = message.forward_from_chat.title or str(chat_id)
    elif message.text and message.text.lstrip("-").isdigit():
        chat_id = int(message.text.strip())
        title = str(chat_id)
    else:
        await message.answer(
            "Не распознал. Перешли сообщение из нужного чата или введи числовой ID."
        )
        return

    async with async_session_maker() as session:
        await set_setting(session, "receiver_chat_id", str(chat_id))

    await state.clear()
    log.info("receiver_chat_id set to %d by user %s", chat_id, message.from_user.id if message.from_user else "?")
    await message.answer(
        f"✅ Получатель установлен: {title} ({chat_id})",
        reply_markup=main_menu_keyboard(is_owner),
    )
