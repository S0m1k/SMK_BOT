import pytest

from app.core.normalizer import normalize


def test_casefold_latin():
    assert normalize("Hello World") == "hello world"


def test_casefold_cyrillic():
    assert normalize("Привет МИР") == "привет мир"


def test_yo_to_ye():
    assert normalize("ёлка") == "елка"


def test_yo_to_ye_uppercase():
    assert normalize("Ёж") == "еж"


def test_whitespace_collapse():
    assert normalize("  много   пробелов  ") == "много пробелов"


def test_tab_and_newline_collapse():
    assert normalize("а\tб\nв") == "а б в"


def test_strip():
    assert normalize("  текст  ") == "текст"


def test_mixed_yo_and_case():
    assert normalize("Стёкла СТЁКЛА") == "стекла стекла"


def test_empty_string():
    assert normalize("") == ""


def test_punctuation_preserved():
    result = normalize("СРО, НОК.")
    assert "," in result
    assert "." in result
