"""Seed test keywords and categories for manual testing.

Usage: python scripts/seed_test_data.py
"""
import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from app.db.base import async_session_maker, init_db
from app.db.models import MatchType
from app.db.repo import add_keyword, get_or_create_category

SEED_KEYWORDS = [
    ("сро", MatchType.SUBSTRING, "СРО и специалисты"),
    ("вступление в сро", MatchType.SUBSTRING, "СРО и специалисты"),
    ("допуск сро", MatchType.SUBSTRING, "СРО и специалисты"),
    ("НОК", MatchType.EXACT, "СРО и специалисты"),
    ("НРС", MatchType.EXACT, "СРО и специалисты"),
    ("повышение квалификации", MatchType.SUBSTRING, "СРО и специалисты"),
    ("охрана труда", MatchType.SUBSTRING, "СРО и специалисты"),
    ("лицензия мчс", MatchType.SUBSTRING, "Лицензии и реестры"),
    ("лицензия фсб", MatchType.SUBSTRING, "Лицензии и реестры"),
    ("ФСБ", MatchType.EXACT, "Лицензии и реестры"),
    ("товарный знак", MatchType.SUBSTRING, "Лицензии и реестры"),
    ("эпб", MatchType.SUBSTRING, "ЭПБ"),
    ("экспертиза промышленной безопасности", MatchType.SUBSTRING, "ЭПБ"),
    ("Э14.4ТУ", MatchType.EXACT, "ЭПБ"),
    ("сертификация исо", MatchType.SUBSTRING, "Документация и ИСО"),
    ("исо 9001", MatchType.SUBSTRING, "Документация и ИСО"),
    ("тендер", MatchType.SUBSTRING, "Тендеры"),
    ("тендерное сопровождение", MatchType.SUBSTRING, "Тендеры"),
    ("44-фз", MatchType.SUBSTRING, "Тендеры"),
    ("223-фз", MatchType.SUBSTRING, "Тендеры"),
]


async def seed() -> None:
    await init_db()
    async with async_session_maker() as session:
        added = 0
        for text, match_type, cat_name in SEED_KEYWORDS:
            cat = await get_or_create_category(session, cat_name)
            await add_keyword(session, text, match_type, cat.id, added_by=0)
            added += 1
            print(f"  + {text} ({match_type})")
        print(f"\nSeeded {added} keywords.")


asyncio.run(seed())
