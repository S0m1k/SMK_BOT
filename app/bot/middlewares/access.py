from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from app.config import settings
from app.db.base import async_session_maker
from app.db.repo import is_active_admin


class AccessMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None:
            return
        uid = user.id
        is_owner = uid in settings.owner_ids
        if not is_owner:
            async with async_session_maker() as session:
                if not await is_active_admin(session, uid):
                    return  # silently ignore non-admins
        data["is_owner"] = is_owner
        data["is_admin"] = True
        return await handler(event, data)
