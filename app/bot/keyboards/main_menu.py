from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard(is_owner: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="📥 Чаты", callback_data="cb:menu:chats"),
            InlineKeyboardButton(text="🔑 Ключи", callback_data="cb:menu:words"),
        ],
        [
            InlineKeyboardButton(text="📤 Импорт/Экспорт", callback_data="cb:menu:import"),
            InlineKeyboardButton(text="📊 Статус", callback_data="cb:menu:status"),
        ],
        [
            InlineKeyboardButton(text="⏸ Пауза/Старт", callback_data="cb:menu:toggle"),
            InlineKeyboardButton(text="⚙ Настройки", callback_data="cb:menu:settings"),
        ],
    ]
    if is_owner:
        rows.append([
            InlineKeyboardButton(text="👮 Админы", callback_data="cb:menu:admins"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
