import asyncio
import logging
import sys

from telethon import TelegramClient

from app.config import settings

log = logging.getLogger(__name__)


def build_client() -> TelegramClient:
    return TelegramClient(
        settings.session_path,
        settings.telegram_api_id,
        settings.telegram_api_hash,
    )


async def login_interactive() -> None:
    """Run with --login flag to create session interactively."""
    client = build_client()
    await client.start(phone=settings.telegram_phone)
    me = await client.get_me()
    log.info("logged in as %s (@%s)", me.first_name, me.username)
    await client.disconnect()


if __name__ == "__main__":
    from app.utils.logger import setup_logging
    setup_logging()
    if "--login" in sys.argv:
        asyncio.run(login_interactive())
    else:
        print("Usage: python -m app.userbot.client --login")
