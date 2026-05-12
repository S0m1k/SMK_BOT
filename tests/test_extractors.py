import pytest

from app.core.extractors import extract_email, extract_phone, extract_tg_username
from tests.fixtures.sample_messages import (
    EMAIL_MESSAGES,
    EMAIL_NO_MESSAGES,
    PHONE_MESSAGES,
    PHONE_NO_MESSAGES,
    TG_MESSAGES,
    TG_NO_MESSAGES,
)


# --- phone ---

@pytest.mark.parametrize("text", PHONE_MESSAGES)
def test_extract_phone_positive(text: str):
    assert extract_phone(text) is not None, f"Expected phone in: {text!r}"


@pytest.mark.parametrize("text", PHONE_NO_MESSAGES)
def test_extract_phone_negative(text: str):
    assert extract_phone(text) is None, f"Expected no phone in: {text!r}"


def test_extract_phone_ru_format():
    result = extract_phone("+7 (999) 123-45-67")
    assert result is not None
    assert "999" in result


def test_extract_phone_8_format():
    result = extract_phone("8 916 000 11 22")
    assert result is not None
    assert "916" in result


# --- email ---

@pytest.mark.parametrize("text", EMAIL_MESSAGES)
def test_extract_email_positive(text: str):
    assert extract_email(text) is not None, f"Expected email in: {text!r}"


@pytest.mark.parametrize("text", EMAIL_NO_MESSAGES)
def test_extract_email_negative(text: str):
    assert extract_email(text) is None, f"Expected no email in: {text!r}"


def test_extract_email_returns_address():
    result = extract_email("Пишите на info@example.com пожалуйста")
    assert result == "info@example.com"


def test_extract_email_with_plus():
    result = extract_email("test.user+tag@mail.ru")
    assert result is not None
    assert "@" in result


# --- tg username ---

@pytest.mark.parametrize("text", TG_MESSAGES)
def test_extract_tg_positive(text: str):
    assert extract_tg_username(text) is not None, f"Expected tg in: {text!r}"


@pytest.mark.parametrize("text", TG_NO_MESSAGES)
def test_extract_tg_negative(text: str):
    assert extract_tg_username(text) is None, f"Expected no tg in: {text!r}"


def test_extract_tg_returns_with_at():
    result = extract_tg_username("Пишите @manager123")
    assert result == "@manager123"


def test_extract_tg_from_link():
    result = extract_tg_username("t.me/smkstandart")
    assert result == "@smkstandart"


def test_extract_tg_no_short_handle():
    assert extract_tg_username("@abc") is None
