from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Lead:
    chat_tg_id: int
    chat_title: str
    message_id: int
    message_link: str
    author_id: int
    author_username: str | None
    author_first_name: str | None
    author_last_name: str | None
    text: str
    matched_words: list[str]
    extracted_phone: str | None = None
    extracted_email: str | None = None
    extracted_tg: str | None = None
    matched_at: datetime = field(default_factory=datetime.utcnow)
