import logging

from aiogram import Router
from aiogram.types import ErrorEvent

log = logging.getLogger(__name__)
router = Router(name="errors")


@router.error()
async def global_error_handler(event: ErrorEvent) -> None:
    log.exception("unhandled exception in handler", exc_info=event.exception)
