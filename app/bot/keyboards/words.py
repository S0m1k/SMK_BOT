from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.db.models import Category, Keyword, MatchType

PAGE_SIZE = 10


def words_list_keyboard(
    keywords: list[Keyword],
    page: int,
    total: int,
    category_id: int | None,
    categories: list[Category],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    # Category filter row
    all_label = "✓Все" if category_id is None else "Все"
    cat_buttons = [
        InlineKeyboardButton(text=all_label, callback_data="cb:word:list:cat=0:page=1")
    ]
    for cat in categories[:4]:
        label = f"{'✓' if cat.id == category_id else ''}{cat.name[:12]}"
        cat_buttons.append(
            InlineKeyboardButton(text=label, callback_data=f"cb:word:list:cat={cat.id}:page=1")
        )
    rows.append(cat_buttons)

    # Keywords rows
    for kw in keywords:
        match_label = "≈" if kw.match_type == MatchType.SUBSTRING else "="
        rows.append([
            InlineKeyboardButton(
                text=f"{match_label} {kw.text[:35]}",
                callback_data=f"cb:word:toggle:{kw.id}",
            ),
            InlineKeyboardButton(text="✕", callback_data=f"cb:word:del:{kw.id}"),
        ])

    # Pagination
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    cat_param = category_id or 0
    nav: list[InlineKeyboardButton] = []
    if page > 1:
        nav.append(
            InlineKeyboardButton(text="◀", callback_data=f"cb:word:list:cat={cat_param}:page={page - 1}")
        )
    nav.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="cb:noop"))
    if page < total_pages:
        nav.append(
            InlineKeyboardButton(text="▶", callback_data=f"cb:word:list:cat={cat_param}:page={page + 1}")
        )
    if nav:
        rows.append(nav)

    rows.append([
        InlineKeyboardButton(text="➕ Добавить слово", callback_data="cb:word:add"),
        InlineKeyboardButton(text="↩ Назад", callback_data="cb:menu:back_main"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def category_choose_keyboard(categories: list[Category]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for cat in categories:
        rows.append([
            InlineKeyboardButton(text=cat.name, callback_data=f"cb:word:cat:{cat.id}")
        ])
    rows.append([InlineKeyboardButton(text="Без категории", callback_data="cb:word:cat:0")])
    rows.append([InlineKeyboardButton(text="✖ Отмена", callback_data="cb:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def match_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="≈ Подстрока (по умолчанию)",
                callback_data="cb:word:matchtype:substring",
            ),
            InlineKeyboardButton(
                text="= Точное слово",
                callback_data="cb:word:matchtype:exact",
            ),
        ],
        [InlineKeyboardButton(text="✖ Отмена", callback_data="cb:cancel")],
    ])
