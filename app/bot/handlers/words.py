import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.common import cancel_keyboard, confirm_keyboard
from app.bot.keyboards.words import PAGE_SIZE, category_choose_keyboard, match_type_keyboard, words_list_keyboard
from app.bot.states import AddWord
from app.core.bus import reload_caches
from app.db.base import async_session_maker
from app.db.models import MatchType
from app.db.repo import (
    add_keyword,
    deactivate_keyword,
    deactivate_keyword_by_text,
    get_active_keywords,
    get_keywords_page,
    list_categories,
    toggle_keyword_match_type,
)

log = logging.getLogger(__name__)
router = Router(name="words")


async def _send_words_page(
    target: Message | CallbackQuery,
    page: int,
    category_id: int | None,
) -> None:
    async with async_session_maker() as session:
        keywords, total = await get_keywords_page(session, page, PAGE_SIZE, category_id)
        categories = await list_categories(session)

    kb = words_list_keyboard(keywords, page, total, category_id, categories)
    text = f"🔑 Ключевые слова (всего: {total})"
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=kb)
        await target.answer()
    else:
        await target.answer(text, reply_markup=kb)


# ---- List ----

@router.callback_query(F.data == "cb:menu:words")
async def cb_menu_words(callback: CallbackQuery) -> None:
    await _send_words_page(callback, 1, None)


@router.callback_query(F.data.startswith("cb:word:list:"))
async def cb_word_list_page(callback: CallbackQuery) -> None:
    # Format: cb:word:list:cat=X:page=Y
    parts = callback.data.split(":")
    cat_id = int(parts[3].split("=")[1])
    page = int(parts[4].split("=")[1])
    category_id = cat_id if cat_id != 0 else None
    await _send_words_page(callback, page, category_id)


# ---- Add via FSM ----

@router.callback_query(F.data == "cb:word:add")
async def cb_word_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddWord.waiting_text)
    await state.update_data(list_page=1, list_cat=0)
    await callback.message.answer(
        "Введите ключевое слово или фразу:", reply_markup=cancel_keyboard()
    )
    await callback.answer()


@router.message(AddWord.waiting_text)
async def fsm_word_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("Пожалуйста, введите текст слова.")
        return

    await state.update_data(word_text=text)
    await state.set_state(AddWord.choosing_category)

    async with async_session_maker() as session:
        categories = await list_categories(session)

    await message.answer(
        f"Слово: «{text}»\nВыберите категорию:",
        reply_markup=category_choose_keyboard(categories),
    )


@router.callback_query(F.data.startswith("cb:word:cat:"), AddWord.choosing_category)
async def fsm_word_category(callback: CallbackQuery, state: FSMContext) -> None:
    cat_id = int(callback.data.split(":")[3])
    await state.update_data(word_cat_id=cat_id if cat_id != 0 else None)
    await state.set_state(AddWord.choosing_match_type)
    await callback.message.edit_text(
        "Выберите тип совпадения:",
        reply_markup=match_type_keyboard(),
    )
    await callback.answer()


@router.callback_query(
    F.data.in_({"cb:word:matchtype:substring", "cb:word:matchtype:exact"}),
    AddWord.choosing_match_type,
)
async def fsm_word_matchtype(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    word_text: str = data["word_text"]
    cat_id: int | None = data.get("word_cat_id")
    match_type = MatchType.SUBSTRING if "substring" in callback.data else MatchType.EXACT
    added_by = callback.from_user.id if callback.from_user else 0

    async with async_session_maker() as session:
        await add_keyword(session, word_text, match_type, cat_id, added_by)
        await reload_caches(session)

    await state.clear()
    match_label = "подстрока" if match_type == MatchType.SUBSTRING else "точное"
    log.info("keyword added: %r (%s) by user %d", word_text, match_type, added_by)
    await callback.message.edit_text(f"✅ Добавлено: «{word_text}» ({match_label})")
    await callback.answer()


# ---- Toggle match type ----

@router.callback_query(F.data.startswith("cb:word:toggle:"))
async def cb_word_toggle(callback: CallbackQuery) -> None:
    kw_id = int(callback.data.split(":")[3])

    async with async_session_maker() as session:
        kw = await toggle_keyword_match_type(session, kw_id)
        await reload_caches(session)

    if kw is None:
        await callback.answer("Слово не найдено.", show_alert=True)
        return

    match_label = "подстрока" if kw.match_type == MatchType.SUBSTRING else "точное"
    log.info("keyword %d toggled to %s", kw_id, kw.match_type)
    await callback.answer(f"Тип изменён на: {match_label}")
    await _send_words_page(callback, 1, None)


# ---- Delete ----

@router.callback_query(F.data.startswith("cb:word:del:"))
async def cb_word_del(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    list_page = data.get("list_page", 1)
    list_cat = data.get("list_cat", 0)
    kw_id = int(callback.data.split(":")[3])
    # Persist current page/cat so we can return after deletion
    await state.update_data(del_kw_id=kw_id, list_page=list_page, list_cat=list_cat)
    await callback.message.edit_text(
        "Удалить ключевое слово?",
        reply_markup=confirm_keyboard(
            yes_data=f"cb:word:del_yes:{kw_id}",
            no_data=f"cb:word:del_no:{kw_id}",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cb:word:del_no:"))
async def cb_word_del_no(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    page = data.get("list_page", 1)
    cat = data.get("list_cat", 0)
    await _send_words_page(callback, page, cat if cat != 0 else None)


@router.callback_query(F.data.startswith("cb:word:del_yes:"))
async def cb_word_del_yes(callback: CallbackQuery, state: FSMContext) -> None:
    kw_id = int(callback.data.split(":")[3])
    data = await state.get_data()
    page = data.get("list_page", 1)
    cat = data.get("list_cat", 0)

    async with async_session_maker() as session:
        deleted = await deactivate_keyword(session, kw_id)
        await reload_caches(session)

    if not deleted:
        await callback.answer("Слово не найдено.", show_alert=True)
    else:
        log.info("keyword %d deactivated", kw_id)
        await callback.answer("Удалено.")

    await _send_words_page(callback, page, cat if cat != 0 else None)


# ---- Slash commands ----

@router.message(Command("addword"))
async def cmd_addword(message: Message) -> None:
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Использование: /addword <слово>")
        return

    text = args[1].strip()
    added_by = message.from_user.id if message.from_user else 0

    async with async_session_maker() as session:
        await add_keyword(session, text, MatchType.SUBSTRING, None, added_by)
        await reload_caches(session)

    log.info("keyword added via /addword: %r by user %d", text, added_by)
    await message.answer(f"✅ Добавлено: «{text}»")


@router.message(Command("addwords"))
async def cmd_addwords(message: Message) -> None:
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Использование: /addwords слово1, слово2, слово3")
        return

    raw_words = [w.strip() for w in args[1].split(",") if w.strip()]
    if not raw_words:
        await message.answer("Не найдено слов для добавления.")
        return

    added_by = message.from_user.id if message.from_user else 0

    async with async_session_maker() as session:
        for word_text in raw_words:
            await add_keyword(session, word_text, MatchType.SUBSTRING, None, added_by)
        await reload_caches(session)

    log.info("batch added %d keywords via /addwords by user %d", len(raw_words), added_by)
    await message.answer(f"✅ Добавлено слов: {len(raw_words)}")


@router.message(Command("removeword"))
async def cmd_removeword(message: Message) -> None:
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Использование: /removeword <слово>")
        return

    text = args[1].strip()

    async with async_session_maker() as session:
        deleted = await deactivate_keyword_by_text(session, text)
        if deleted:
            await reload_caches(session)

    if deleted:
        log.info("keyword deactivated by text %r", text)
        await message.answer(f"✅ Слово «{text}» удалено.")
    else:
        await message.answer(f"Слово «{text}» не найдено среди активных.")


@router.message(Command("listwords"))
async def cmd_listwords(message: Message) -> None:
    async with async_session_maker() as session:
        keywords = await get_active_keywords(session)

    if not keywords:
        await message.answer("Нет активных ключевых слов.")
        return

    chunk_size = 50
    chunks = [keywords[i:i + chunk_size] for i in range(0, len(keywords), chunk_size)]
    for i, chunk in enumerate(chunks):
        lines = [
            f"{'≈' if kw.match_type == MatchType.SUBSTRING else '='} {kw.text}"
            for kw in chunk
        ]
        header = f"Ключевые слова (всего {len(keywords)})"
        if len(chunks) > 1:
            header += f" — часть {i + 1}/{len(chunks)}"
        await message.answer(header + ":\n" + "\n".join(lines))
