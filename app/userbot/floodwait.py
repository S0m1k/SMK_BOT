import asyncio
import functools
import logging

from telethon.errors import FloodWaitError

log = logging.getLogger(__name__)


def flood_safe(max_wait: int = 300):
    """Decorator for Telethon client calls. Retries once after FloodWait if wait <= max_wait."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except FloodWaitError as e:
                if e.seconds > max_wait:
                    log.error(
                        "flood wait %ds exceeds max_wait=%ds, giving up",
                        e.seconds, max_wait,
                    )
                    raise
                log.warning("flood wait %ds on %s, sleeping", e.seconds, func.__name__)
                await asyncio.sleep(e.seconds + 1)
                return await func(*args, **kwargs)
        return wrapper
    return decorator
