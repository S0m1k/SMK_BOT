from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.config import settings as app_settings
from app.db.models import Admin


def admins_list_keyboard(admins: list[Admin]) -> InlineKeyboardMarkup:
    rows = []
    for admin in admins:
        name = admin.full_name or admin.username or str(admin.tg_id)
        is_owner = admin.tg_id in app_settings.owner_ids
        label = f"👑 {name} (owner)" if is_owner else f"👤 {name}"
        row = [InlineKeyboardButton(text=label, callback_data="cb:noop")]
        if not is_owner:
            row.append(InlineKeyboardButton(text="✕", callback_data=f"cb:admin:del:{admin.tg_id}"))
        rows.append(row)
    rows.append([
        InlineKeyboardButton(text="➕ Добавить админа", callback_data="cb:admin:add"),
        InlineKeyboardButton(text="↩ Назад", callback_data="cb:menu:back_main"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
