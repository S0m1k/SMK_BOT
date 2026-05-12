import logging
import os
from logging.handlers import TimedRotatingFileHandler

from app.config import settings


def setup_logging() -> None:
    os.makedirs(settings.log_dir, exist_ok=True)

    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    if not root.handlers:
        stdout_handler = logging.StreamHandler()
        stdout_handler.setFormatter(fmt)
        root.addHandler(stdout_handler)

        file_handler = TimedRotatingFileHandler(
            filename=os.path.join(settings.log_dir, "smk_bot.log"),
            when="midnight",
            interval=1,
            backupCount=14,
            encoding="utf-8",
        )
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
