import pytest

from app.core.matcher import KeywordMatcher, KeywordSpec
from app.core.normalizer import normalize
from tests.fixtures.sample_messages import TZ_SAMPLE


def make_spec(id: int, text: str, exact: bool = False, category: str | None = None) -> KeywordSpec:
    return KeywordSpec(id=id, text=text, normalized=normalize(text), exact=exact, category=category)


def make_matcher(*specs: KeywordSpec) -> KeywordMatcher:
    return KeywordMatcher(list(specs))


# --- substring matching ---

def test_substring_basic():
    matcher = make_matcher(make_spec(1, "СРО"))
    results = matcher.match("Хочу вступить в СРО срочно")
    assert any(s.id == 1 for s in results)


def test_substring_case_insensitive():
    matcher = make_matcher(make_spec(1, "сро"))
    results = matcher.match("ХОЧУ ВСТУПИТЬ В СРО")
    assert any(s.id == 1 for s in results)


def test_substring_yo_normalization():
    matcher = make_matcher(make_spec(1, "страхование"))
    results = matcher.match("вопрос по страхованию объекта")
    assert any(s.id == 1 for s in results)


def test_substring_yo_in_keyword():
    matcher = make_matcher(make_spec(1, "ёжик"))
    results = matcher.match("видели ежика в лесу")
    assert any(s.id == 1 for s in results)


def test_substring_no_match():
    matcher = make_matcher(make_spec(1, "лицензия"))
    results = matcher.match("вопрос про сертификацию")
    assert results == []


def test_substring_partial_word():
    matcher = make_matcher(make_spec(1, "сро"))
    results = matcher.match("интересует просро ченная задолженность")
    assert any(s.id == 1 for s in results)


# --- exact matching ---

def test_exact_full_word():
    matcher = make_matcher(make_spec(1, "НОК", exact=True))
    results = matcher.match("интересует НОК")
    assert any(s.id == 1 for s in results)


def test_exact_no_partial():
    matcher = make_matcher(make_spec(1, "НОК", exact=True))
    # "нок" не является отдельным словом в "кому" — \b должен отсечь
    results = matcher.match("никому не нужно")
    assert results == []


def test_exact_vs_substring_difference():
    sub = make_spec(1, "СРО", exact=False)
    ex = make_spec(2, "НОК", exact=True)
    matcher = make_matcher(sub, ex)
    results = matcher.match("просрочка")
    ids = {s.id for s in results}
    assert 1 in ids   # substring найдёт "сро" в "просрочка"
    assert 2 not in ids  # exact не найдёт "НОК"


def test_exact_word_boundary():
    matcher = make_matcher(make_spec(1, "ЭПБ", exact=True))
    results = matcher.match("нужна ЭПБ объекта")
    assert any(s.id == 1 for s in results)


def test_exact_no_match_embedded():
    matcher = make_matcher(make_spec(1, "СГР", exact=True))
    results = matcher.match("СГРупповой заказ")
    assert results == []


# --- mixed substring + exact ---

def test_mixed_match():
    specs = [
        make_spec(1, "СРО", exact=False),
        make_spec(2, "НОК", exact=True),
        make_spec(3, "НРС", exact=True),
    ]
    matcher = KeywordMatcher(specs)
    results = matcher.match("вступление в СРО, интересует НОК и реестр НРС")
    ids = {s.id for s in results}
    assert ids == {1, 2, 3}


# --- ТЗ sample ---

def test_tz_sample_sro():
    specs = [
        make_spec(1, "СРО", exact=False),
        make_spec(2, "вступление в СРО", exact=False),
        make_spec(3, "НОК", exact=True),
        make_spec(4, "НРС", exact=True),
        make_spec(5, "генподряд", exact=False),
    ]
    matcher = KeywordMatcher(specs)
    results = matcher.match(TZ_SAMPLE)
    ids = {s.id for s in results}
    assert 1 in ids or 2 in ids, "should match СРО"
    assert 3 in ids, "should match НОК"
    assert 4 in ids, "should match НРС"
    assert 5 in ids, "should match генподряд"


# --- empty ---

def test_empty_text():
    matcher = make_matcher(make_spec(1, "СРО"))
    assert matcher.match("") == []


def test_empty_matcher():
    matcher = KeywordMatcher([])
    assert matcher.match("вступление в СРО") == []


# --- multiple matches, uniqueness ---

def test_unique_results():
    matcher = make_matcher(make_spec(1, "сро"))
    results = matcher.match("СРО сро СРО")
    ids = [s.id for s in results]
    assert ids.count(1) == 1


# --- category preserved ---

def test_category_in_result():
    spec = make_spec(1, "СРО", category="СРО и специалисты")
    matcher = make_matcher(spec)
    results = matcher.match("вступить в СРО")
    assert results[0].category == "СРО и специалисты"
