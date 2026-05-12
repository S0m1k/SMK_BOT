import re

_RUS_E_MAP = str.maketrans("ёЁ", "ее")
_WS_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    s = text.translate(_RUS_E_MAP).casefold()
    s = _WS_RE.sub(" ", s)
    return s.strip()
