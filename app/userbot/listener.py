import logging

from telethon import TelegramClient, events

from app.core.bus import active_chat_ids, get_matcher, lead_queue
from app.core.extractors import extract_email, extract_phone, extract_tg_username
from app.core.lead import Lead

log = logging.getLogger(__name__)


def _build_message_link(chat_id: int, msg_id: int, username: str | None) -> str:
    if username:
        return f"https://t.me/{username}/{msg_id}"
    # chat_id for supergroups is like -1001234567890; strip the leading -100
    bare = str(abs(chat_id))
    if bare.startswith("100"):
        bare = bare[3:]
    return f"https://t.me/c/{bare}/{msg_id}"


def register_handlers(client: TelegramClient) -> None:
    @client.on(events.NewMessage())
    async def on_new_message(event: events.NewMessage.Event) -> None:
        chat_id = event.chat_id
        if chat_id not in active_chat_ids:
            return

        from app.core.bus import monitoring_enabled
        if not monitoring_enabled:
            return

        text = event.raw_text or ""
        if not text.strip():
            return

        matcher = await get_matcher()
        if matcher is None:
            return

        matches = matcher.match(text)
        if not matches:
            return

        try:
            sender = await event.get_sender()
            chat = await event.get_chat()
        except Exception as e:
            log.warning("could not get sender/chat for event: %s", e)
            return

        username = getattr(chat, "username", None)
        lead = Lead(
            chat_tg_id=chat_id,
            chat_title=getattr(chat, "title", str(chat_id)),
            message_id=event.id,
            message_link=_build_message_link(chat_id, event.id, username),
            author_id=sender.id,
            author_username=getattr(sender, "username", None),
            author_first_name=getattr(sender, "first_name", None),
            author_last_name=getattr(sender, "last_name", None),
            text=text,
            matched_words=[m.text for m in matches],
            extracted_phone=extract_phone(text),
            extracted_email=extract_email(text),
            extracted_tg=extract_tg_username(text),
        )

        try:
            lead_queue.put_nowait(lead)
            log.info(
                "matched chat=%d author=%d words=%s",
                chat_id,
                sender.id,
                [m.text for m in matches],
            )
        except Exception:
            log.warning("lead_queue full, dropping lead from chat=%d", chat_id)
