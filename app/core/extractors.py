import re

_PHONE_RE = re.compile(
    r"(?:(?<!\d)(?:\+?7|8)\s*\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2})"
    r"|(?:\+\d{1,3}[\s\-]?\d{2,4}[\s\-]?\d{2,4}[\s\-]?\d{2,4})"
)
_EMAIL_RE = re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+")
_TG_RE = re.compile(r"(?:@|t\.me/)([A-Za-z][A-Za-z0-9_]{3,31})")


def extract_phone(text: str) -> str | None:
    m = _PHONE_RE.search(text)
    return m.group(0) if m else None


def extract_email(text: str) -> str | None:
    m = _EMAIL_RE.search(text)
    return m.group(0) if m else None


def extract_tg_username(text: str) -> str | None:
    m = _TG_RE.search(text)
    return ("@" + m.group(1)) if m else None
