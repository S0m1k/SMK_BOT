import logging

from telethon import TelegramClient
from telethon.errors import InviteHashExpiredError, UserAlreadyParticipantError
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.types import Channel

from app.userbot.floodwait import flood_safe

log = logging.getLogger(__name__)


def _to_event_chat_id(entity) -> int:
    """Convert Telethon entity to the chat_id format used in NewMessage events.

    For channels/supergroups, event.chat_id is -100XXXXXXXXX.
    Telethon entity.id is the bare ID without the -100 prefix.
    """
    raw_id = entity.id
    if isinstance(entity, Channel):
        return int(f"-100{raw_id}")
    # Regular groups come back as negative already in events
    return -raw_id if raw_id > 0 else raw_id


@flood_safe(max_wait=300)
async def join_chat(client: TelegramClient, link_or_username: str) -> dict:
    """Join a chat and return info dict with keys: tg_id, title, username.

    Raises ValueError with a human-readable message on failure.
    """
    try:
        entity = await client.get_entity(link_or_username)
    except Exception as e:
        raise ValueError(f"Не удалось найти чат: {e}") from e

    try:
        await client(JoinChannelRequest(entity))
    except UserAlreadyParticipantError:
        pass  # already in — that is fine
    except InviteHashExpiredError:
        raise ValueError("Ссылка-приглашение устарела или недействительна")
    except Exception as e:
        raise ValueError(f"Не удалось вступить: {e}") from e

    return {
        "tg_id": _to_event_chat_id(entity),
        "title": getattr(entity, "title", str(entity.id)),
        "username": getattr(entity, "username", None),
    }


@flood_safe(max_wait=300)
async def leave_chat(client: TelegramClient, tg_id: int) -> None:
    try:
        entity = await client.get_entity(tg_id)
        await client(LeaveChannelRequest(entity))
    except Exception as e:
        log.warning("could not leave chat %d: %s", tg_id, e)


async def resolve_chat_info(client: TelegramClient, link_or_username: str) -> dict:
    """Resolve entity without joining. Returns same dict shape as join_chat."""
    entity = await client.get_entity(link_or_username)
    return {
        "tg_id": _to_event_chat_id(entity),
        "title": getattr(entity, "title", str(entity.id)),
        "username": getattr(entity, "username", None),
    }
