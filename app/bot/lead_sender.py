import asyncio
import logging
from datetime import timezone

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter

from app.core.bus import lead_queue
from app.core.lead import Lead
from app.db.base import async_session_maker
from app.db.repo import get_setting, log_lead

log = logging.getLogger(__name__)

MAX_TEXT_LEN = 4000
MAX_KEYWORDS_LEN = 200


def format_lead(lead: Lead) -> str:
    text = lead.text
    if len(text) > MAX_TEXT_LEN:
        text = text[:MAX_TEXT_LEN] + "…"

    kw_str = ", ".join(lead.matched_words)
    if len(kw_str) > MAX_KEYWORDS_LEN:
        visible: list[str] = []
        length = 0
        for kw in lead.matched_words:
            if length + len(kw) + 2 > MAX_KEYWORDS_LEN:
                remaining = len(lead.matched_words) - len(visible)
                visible.append(f"… и ещё {remaining}")
                break
            visible.append(kw)
            length += len(kw) + 2
        kw_str = ", ".join(visible)

    parts = filter(None, [lead.author_first_name, lead.author_last_name])
    full_name = " ".join(parts) or "Неизвестен"

    lines = [
        f"🔔 НОВЫЙ ЛИД | чат: «{lead.chat_title}»",
        f"👤 Имя: {full_name}",
    ]
    if lead.author_username:
        lines.append(f"🔗 {lead.author_username}")
    if lead.extracted_phone:
        lines.append(f"📞 Телефон: {lead.extracted_phone}")
    if lead.extracted_email:
        lines.append(f"📧 Email: {lead.extracted_email}")
    if lead.extracted_tg and lead.extracted_tg != lead.author_username:
        lines.append(f"💬 TG в тексте: {lead.extracted_tg}")

    ts = lead.matched_at.astimezone(timezone.utc).strftime("%d.%m.%Y %H:%M")
    lines += [
        f"💬 Сообщение:\n«{text}»",
        f"🔑 Ключевые слова: {kw_str}",
        f"🕒 Время: {ts} UTC",
        f"🔗 Ссылка: {lead.message_link}",
    ]
    return "\n".join(lines)


async def lead_sender_loop(bot: Bot) -> None:
    from app.config import settings

    while True:
        lead: Lead = await lead_queue.get()
        try:
            async with async_session_maker() as session:
                receiver_id = await get_setting(session, "receiver_chat_id")
                if not receiver_id:
                    log.warning("receiver_chat_id not set, dropping lead")
                    continue
                text = format_lead(lead)
                try:
                    await bot.send_message(int(receiver_id), text)
                except TelegramRetryAfter as e:
                    log.warning("retry after %ds", e.retry_after)
                    await asyncio.sleep(e.retry_after + 1)
                    await bot.send_message(int(receiver_id), text)
                await log_lead(session, lead)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("error sending lead")
        finally:
            await asyncio.sleep(settings.lead_send_delay_sec)
            lead_queue.task_done()
