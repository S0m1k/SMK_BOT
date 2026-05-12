import asyncio
import logging

from app.config import settings

log = logging.getLogger(__name__)


async def heartbeat_loop() -> None:
    while True:
        from app.core.bus import active_chat_ids, lead_queue
        log.info(
            "heartbeat | chats=%d qsize=%d",
            len(active_chat_ids),
            lead_queue.qsize(),
        )
        await asyncio.sleep(settings.heartbeat_interval_sec)
