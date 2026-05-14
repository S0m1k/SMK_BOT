from __future__ import annotations

import io
import logging
from datetime import date

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Document, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.keyboards.common import cancel_keyboard, confirm_keyboard
from app.bot.keyboards.main_menu import main_menu_keyboard
from app.bot.states import ImportWords
from app.core.bus import reload_caches
from app.db.base import async_session_maker
from app.db.models import MatchType
from app.db.repo import add_keyword, get_active_keywords, get_or_create_category

log = logging.getLogger(__name__)
router = Router(name="import_export")


# ── Export ───────────────────────────────────────────────────────────────────

@router.message(Command("exportwords"))
@router.callback_query(F.data == "cb:import:export")
async def cmd_export(event, is_owner: bool = False) -> None:
    msg = event if isinstance(event, Message) else event.message
    async with async_session_maker() as session:
        keywords = await get_active_keywords(session)
    if not keywords:
        await msg.answer("Список ключевых слов пуст.")
        if isinstance(event, CallbackQuery):
            await event.answer()
        return
    lines = []
    for kw in keywords:
        prefix = "=" if kw.match_type == MatchType.EXACT else ""
        cat = f" | {kw.category.name}" if kw.category else ""
        lines.append(f"{prefix}{kw.text}{cat}")
    content = "\n".join(lines).encode("utf-8")
    filename = f"keywords_{date.today().isoformat()}.txt"
    await msg.answer_document(
        BufferedInputFile(content, filename=filename),
        caption=f"Экспортировано {len(lines)} ключевых слов",
    )
    if isinstance(event, CallbackQuery):
        await event.answer()


# ── Import ────────────────────────────────────────────────────────────────────

def _parse_keywords_file(content: str) -> list[dict]:
    """Parse keyword file. Returns list of {text, exact, category_name}."""
    items = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # strip inline comment
        if " #" in line:
            line = line[:line.index(" #")].strip()
        # category
        category_name = None
        if " | " in line:
            line, category_name = line.rsplit(" | ", 1)
            line = line.strip()
            category_name = category_name.strip()
        # exact match
        exact = line.startswith("=")
        text = line.lstrip("=").strip()
        if text:
            items.append({"text": text, "exact": exact, "category_name": category_name})
    return items


@router.message(Command("importwords"))
@router.callback_query(F.data == "cb:import:import")
async def cmd_import_start(event, state: FSMContext) -> None:
    msg = event if isinstance(event, Message) else event.message
    await state.set_state(ImportWords.waiting_file)
    await msg.answer(
        "Пришли файл .txt (UTF-8). Формат:\n"
        "• Одно слово на строке\n"
        "• = в начале = точное совпадение\n"
        "• # — комментарий\n"
        "• слово | Категория — с категорией",
        reply_markup=cancel_keyboard(),
    )
    if isinstance(event, CallbackQuery):
        await event.answer()


@router.message(ImportWords.waiting_file, F.document)
async def process_import_file(message: Message, state: FSMContext, bot: Bot) -> None:
    doc: Document = message.document
    if not doc.file_name or not doc.file_name.endswith(".txt"):
        await message.answer("Нужен файл с расширением .txt")
        return

    file = await bot.get_file(doc.file_id)
    buf = io.BytesIO()
    await bot.download_file(file.file_path, buf)
    try:
        content = buf.getvalue().decode("utf-8")
    except UnicodeDecodeError:
        await message.answer("Файл должен быть в кодировке UTF-8.")
        return

    parsed = _parse_keywords_file(content)
    if not parsed:
        await message.answer("Файл пуст или все строки — комментарии.")
        return

    async with async_session_maker() as session:
        existing = await get_active_keywords(session)
    existing_texts = {kw.text.casefold() for kw in existing}

    new_items = [p for p in parsed if p["text"].casefold() not in existing_texts]
    dup_count = len(parsed) - len(new_items)

    await state.update_data(pending_items=new_items)
    await message.answer(
        f"Найдено: новых {len(new_items)}, дубликатов {dup_count}.\n"
        f"Импортировать {len(new_items)} слов?",
        reply_markup=confirm_keyboard("cb:import:confirm", "cb:import:cancel"),
    )
    await state.set_state(ImportWords.confirming)


@router.callback_query(ImportWords.confirming, F.data == "cb:import:confirm")
async def confirm_import(callback: CallbackQuery, state: FSMContext, is_owner: bool = False) -> None:
    data = await state.get_data()
    items: list[dict] = data.get("pending_items", [])
    added = 0
    async with async_session_maker() as session:
        for item in items:
            cat_id = None
            if item["category_name"]:
                cat = await get_or_create_category(session, item["category_name"])
                cat_id = cat.id
            match_type = MatchType.EXACT if item["exact"] else MatchType.SUBSTRING
            await add_keyword(session, item["text"], match_type, cat_id, callback.from_user.id)
            added += 1
        await reload_caches(session)
    await state.clear()
    await callback.message.edit_text(
        f"✅ Импортировано {added} ключевых слов.",
        reply_markup=main_menu_keyboard(is_owner),
    )
    await callback.answer()


@router.callback_query(F.data == "cb:import:cancel")
async def cancel_import(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Импорт отменён.")
    await callback.answer()


@router.callback_query(F.data == "cb:menu:import")
async def cb_import_menu(callback: CallbackQuery) -> None:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Импорт из файла", callback_data="cb:import:import")],
        [InlineKeyboardButton(text="📤 Экспорт в файл", callback_data="cb:import:export")],
        [InlineKeyboardButton(text="↩ Назад", callback_data="cb:menu:back_main")],
    ])
    await callback.message.edit_text("📤 Импорт / Экспорт ключевых слов", reply_markup=kb)
    await callback.answer()
