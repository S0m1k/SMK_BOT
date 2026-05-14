# SMK-BOT

Telegram-бот для мониторинга бизнес-чатов и лидогенерации.
Telethon userbot (слушатель) + aiogram бот (админ-панель).

## Быстрый старт

### 1. Конфигурация
```bash
cp .env.example .env
# Заполни .env: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE,
# BOT_TOKEN, OWNER_IDS, POSTGRES_DSN
```

### 2. Первый логин userbot (один раз, на хосте)
```bash
pip install -e .
python -m app.userbot.client --login
# Введи код из Telegram SMS и пароль 2FA если включён
# Создаётся data/session.session
```

### 3. Запуск
```bash
docker compose up -d
```

### 4. Первичное наполнение БД (опционально)
```bash
docker compose exec bot python scripts/seed_test_data.py
```

## Команды бота

| Команда | Описание |
|---|---|
| /start | Главное меню |
| /addchat | Добавить чат в мониторинг |
| /listchats | Список отслеживаемых чатов |
| /addword | Добавить ключевое слово |
| /addwords | Массовое добавление через запятую |
| /listwords | Список ключевых слов |
| /exportwords | Экспорт в .txt |
| /importwords | Импорт из .txt |
| /setreceiver | Задать чат для получения лидов |
| /status | Статус бота |
| /stop | Пауза мониторинга |
| /startbot | Возобновить мониторинг |
| /addadmin | Добавить админа (только OWNER) |
| /removeadmin | Удалить админа (только OWNER) |
| /listadmins | Список админов |

## Бэкап
```bash
bash scripts/backup.sh
# Сохраняет pg_dump + session.session в ./backups/
```

## Восстановление сессии
Положи файл `session.session` в папку `data/` и перезапусти контейнер.

## Восстановление БД
```bash
docker exec -i smk_bot-postgres-1 psql -U smk smk < backups/pg_dump_smk.sql
```
