import re
from dataclasses import dataclass

import ahocorasick

from app.core.normalizer import normalize


@dataclass(frozen=True)
class KeywordSpec:
    id: int
    text: str
    normalized: str
    exact: bool
    category: str | None


class KeywordMatcher:
    def __init__(self, specs: list[KeywordSpec]):
        self._specs_by_id: dict[int, KeywordSpec] = {s.id: s for s in specs}

        self._aho: ahocorasick.Automaton = ahocorasick.Automaton()
        for s in specs:
            if not s.exact:
                self._aho.add_word(s.normalized, s.id)
        if specs and any(not s.exact for s in specs):
            self._aho.make_automaton()

        exact_alts = [re.escape(s.normalized) for s in specs if s.exact]
        if exact_alts:
            self._exact_re: re.Pattern[str] | None = re.compile(
                r"\b(" + "|".join(exact_alts) + r")\b"
            )
            self._exact_norm_to_id: dict[str, int] = {
                s.normalized: s.id for s in specs if s.exact
            }
        else:
            self._exact_re = None
            self._exact_norm_to_id = {}

    def match(self, text: str) -> list[KeywordSpec]:
        norm = normalize(text)
        matched_ids: set[int] = set()

        if self._aho:
            for _end, kw_id in self._aho.iter(norm):
                matched_ids.add(kw_id)

        if self._exact_re:
            for m in self._exact_re.finditer(norm):
                kw_id = self._exact_norm_to_id.get(m.group(1))
                if kw_id is not None:
                    matched_ids.add(kw_id)

        return [self._specs_by_id[i] for i in matched_ids]
