from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.lead import Lead
from app.db.models import Admin, AdminRole, Category, Chat, Keyword, LeadLog, MatchType, Setting


# --- Settings ---

async def get_setting(session: AsyncSession, key: str) -> str | None:
    result = await session.execute(select(Setting).where(Setting.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else None


async def set_setting(session: AsyncSession, key: str, value: str) -> None:
    existing = await session.execute(select(Setting).where(Setting.key == key))
    row = existing.scalar_one_or_none()
    if row:
        row.value = value
    else:
        session.add(Setting(key=key, value=value))
    await session.commit()


# --- Chats ---

async def get_active_chats(session: AsyncSession) -> list[Chat]:
    result = await session.execute(select(Chat).where(Chat.active.is_(True)))
    return list(result.scalars().all())


async def get_chats_page(
    session: AsyncSession, page: int, page_size: int
) -> tuple[list[Chat], int]:
    offset = (page - 1) * page_size
    total_result = await session.execute(
        select(func.count()).select_from(Chat).where(Chat.active.is_(True))
    )
    total = total_result.scalar_one()
    result = await session.execute(
        select(Chat).where(Chat.active.is_(True)).offset(offset).limit(page_size)
    )
    return list(result.scalars().all()), total


async def add_chat(
    session: AsyncSession,
    tg_id: int,
    title: str,
    username: str | None,
    invite_link: str | None,
    added_by: int,
) -> Chat:
    chat = Chat(
        tg_id=tg_id,
        title=title,
        username=username,
        invite_link=invite_link,
        added_by=added_by,
    )
    session.add(chat)
    await session.commit()
    await session.refresh(chat)
    return chat


async def deactivate_chat(session: AsyncSession, chat_id: int) -> bool:
    result = await session.execute(
        update(Chat).where(Chat.id == chat_id).values(active=False).returning(Chat.id)
    )
    await session.commit()
    return result.scalar_one_or_none() is not None


async def get_chat_by_tg_id(session: AsyncSession, tg_id: int) -> Chat | None:
    result = await session.execute(select(Chat).where(Chat.tg_id == tg_id))
    return result.scalar_one_or_none()


# --- Categories ---

async def list_categories(session: AsyncSession) -> list[Category]:
    result = await session.execute(select(Category))
    return list(result.scalars().all())


async def get_or_create_category(session: AsyncSession, name: str) -> Category:
    result = await session.execute(select(Category).where(Category.name == name))
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    category = Category(name=name)
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


# --- Keywords ---

async def get_active_keywords(session: AsyncSession) -> list[Keyword]:
    result = await session.execute(
        select(Keyword)
        .where(Keyword.active.is_(True))
        .options(selectinload(Keyword.category))
    )
    return list(result.scalars().all())


async def get_keywords_page(
    session: AsyncSession,
    page: int,
    page_size: int,
    category_id: int | None = None,
) -> tuple[list[Keyword], int]:
    offset = (page - 1) * page_size
    base_q = select(Keyword).where(Keyword.active.is_(True))
    count_q = select(func.count()).select_from(Keyword).where(Keyword.active.is_(True))
    if category_id is not None:
        base_q = base_q.where(Keyword.category_id == category_id)
        count_q = count_q.where(Keyword.category_id == category_id)
    total = (await session.execute(count_q)).scalar_one()
    result = await session.execute(
        base_q
        .options(selectinload(Keyword.category))
        .offset(offset)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def add_keyword(
    session: AsyncSession,
    text: str,
    match_type: MatchType,
    category_id: int | None,
    added_by: int,
) -> Keyword:
    keyword = Keyword(
        text=text,
        match_type=match_type,
        category_id=category_id,
        added_by=added_by,
    )
    session.add(keyword)
    await session.commit()
    await session.refresh(keyword)
    return keyword


async def deactivate_keyword(session: AsyncSession, keyword_id: int) -> bool:
    result = await session.execute(
        update(Keyword)
        .where(Keyword.id == keyword_id)
        .values(active=False)
        .returning(Keyword.id)
    )
    await session.commit()
    return result.scalar_one_or_none() is not None


async def toggle_keyword_match_type(
    session: AsyncSession, keyword_id: int
) -> Keyword | None:
    result = await session.execute(select(Keyword).where(Keyword.id == keyword_id))
    keyword = result.scalar_one_or_none()
    if keyword is None:
        return None
    keyword.match_type = (
        MatchType.EXACT if keyword.match_type == MatchType.SUBSTRING else MatchType.SUBSTRING
    )
    await session.commit()
    await session.refresh(keyword)
    return keyword


# --- Admins ---

async def is_active_admin(session: AsyncSession, tg_id: int) -> bool:
    result = await session.execute(
        select(Admin).where(Admin.tg_id == tg_id, Admin.active.is_(True))
    )
    return result.scalar_one_or_none() is not None


async def list_admins(session: AsyncSession) -> list[Admin]:
    result = await session.execute(select(Admin).where(Admin.active.is_(True)))
    return list(result.scalars().all())


async def add_admin(
    session: AsyncSession,
    tg_id: int,
    username: str | None,
    full_name: str | None,
    added_by: int,
) -> Admin:
    admin = Admin(
        tg_id=tg_id,
        username=username,
        full_name=full_name,
        added_by=added_by,
        role=AdminRole.ADMIN,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin


async def deactivate_admin(session: AsyncSession, tg_id: int) -> bool:
    result = await session.execute(
        update(Admin)
        .where(Admin.tg_id == tg_id)
        .values(active=False)
        .returning(Admin.tg_id)
    )
    await session.commit()
    return result.scalar_one_or_none() is not None


# --- Lead log ---

async def log_lead(session: AsyncSession, lead: Lead) -> None:
    entry = LeadLog(
        chat_id=lead.chat_tg_id,
        message_id=lead.message_id,
        author_id=lead.author_id,
        matched_words=", ".join(lead.matched_words),
    )
    session.add(entry)
    await session.commit()
