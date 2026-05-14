import asyncio

_send_lock = asyncio.Semaphore(1)


async def throttled_send(coro):
    async with _send_lock:
        result = await coro
        from app.config import settings
        await asyncio.sleep(settings.lead_send_delay_sec)
        return result
