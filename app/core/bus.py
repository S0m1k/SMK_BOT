import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.lead import Lead
from app.core.matcher import KeywordMatcher, KeywordSpec
from app.db.models import MatchType

log = logging.getLogger(__name__)

lead_queue: asyncio.Queue[Lead] = asyncio.Queue(maxsize=1000)

# Toggled by /stop and /startbot commands; not re-read from DB on every message
monitoring_enabled: bool = True

_current_matcher: KeywordMatcher | None = None
_matcher_lock = asyncio.Lock()

active_chat_ids: set[int] = set()


async def get_matcher() -> KeywordMatcher | None:
    return _current_matcher


async def set_matcher(m: KeywordMatcher) -> None:
    global _current_matcher
    async with _matcher_lock:
        _current_matcher = m


async def reload_caches(session: AsyncSession) -> None:
    # Import here to avoid circular import at module level
    from app.db.repo import get_active_chats, get_active_keywords

    keywords = await get_active_keywords(session)
    specs = [
        KeywordSpec(
            id=kw.id,
            text=kw.text,
            normalized=kw.text.casefold().replace("ё", "е").replace("Ё", "е"),
            exact=kw.match_type == MatchType.EXACT,
            category=kw.category.name if kw.category else None,
        )
        for kw in keywords
    ]
    matcher = KeywordMatcher(specs)
    await set_matcher(matcher)

    chats = await get_active_chats(session)
    active_chat_ids.clear()
    active_chat_ids.update(c.tg_id for c in chats)

    substring_count = sum(1 for s in specs if not s.exact)
    exact_count = sum(1 for s in specs if s.exact)
    log.info(
        "matcher rebuilt: %d substring + %d exact keywords, %d active chats",
        substring_count,
        exact_count,
        len(active_chat_ids),
    )
