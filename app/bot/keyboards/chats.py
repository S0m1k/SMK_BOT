from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.db.models import Chat

PAGE_SIZE = 10


def chats_list_keyboard(
    chats: list[Chat], page: int, total: int
) -> InlineKeyboardMarkup:
    rows = []
    for chat in chats:
        rows.append([
            InlineKeyboardButton(
                text=f"{'🟢 ' if chat.active else ''}{chat.title[:35]}",
                callback_data=f"cb:chat:info:{chat.id}",
            ),
            InlineKeyboardButton(text="✕", callback_data=f"cb:chat:del:{chat.id}"),
        ])

    nav = []
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    if page > 1:
        nav.append(InlineKeyboardButton(text="◀", callback_data=f"cb:chat:list:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="cb:noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="▶", callback_data=f"cb:chat:list:{page + 1}"))
    if nav:
        rows.append(nav)

    rows.append([
        InlineKeyboardButton(text="➕ Добавить чат", callback_data="cb:chat:add"),
        InlineKeyboardButton(text="↩ Назад", callback_data="cb:menu:back_main"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
