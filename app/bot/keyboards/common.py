from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def confirm_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да", callback_data=yes_data),
        InlineKeyboardButton(text="✖ Нет", callback_data=no_data),
    ]])


def back_keyboard(back_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="↩ Назад", callback_data=back_data),
    ]])


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✖ Отмена", callback_data="cb:cancel"),
    ]])
