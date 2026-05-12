TZ_SAMPLE = (
    "Коллеги, кто-нибудь может помочь со вступлением в строительное СРО? "
    "Нужен допуск на генподряд до 10 млн. Желательно срочно. "
    "Также интересует НОК и внесение в реестр НРС."
)

PHONE_MESSAGES = [
    "Звоните: +7 (999) 123-45-67",
    "Мой номер 8 916 000 11 22",
    "Тел: +7-900-555-44-33",
    "+44 20 7946 0958",
    "8(800)555-35-35",
]

PHONE_NO_MESSAGES = [
    "нет телефона",
    "12345",
    "просто текст",
]

EMAIL_MESSAGES = [
    "Пишите на info@example.com",
    "почта: test.user+tag@mail.ru",
    "email: company@sub.domain.org",
    "support@smk-standart.ru",
    "a.b+c@x.io",
]

EMAIL_NO_MESSAGES = [
    "нет почты",
    "просто текст без @",
    "@notanemail",
]

TG_MESSAGES = [
    "Пишите @username",
    "Ссылка: t.me/smkstandart",
    "Наш канал @smk_standart",
    "Пишите в https://t.me/manager_bot",
    "@user1234",
]

TG_NO_MESSAGES = [
    "нет контактов",
    "просто текст",
    "@ab",  # слишком короткий (меньше 4 символов после @)
]
