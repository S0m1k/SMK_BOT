# SMK-BOT — План реализации

Документ для Claude Sonnet 4.6, который будет реализовывать проект. Содержит все согласованные с заказчиком (соло-разработчиком) архитектурные решения, структуру файлов, схему БД, сигнатуры функций и порядок работ. Sonnet может отступать от плана только в мелочах реализации (имена переменных, внутренняя организация helper-функций); архитектурные решения зафиксированы и переутверждению не подлежат.

ТЗ заказчика лежит в `C:\Users\user\Downloads\Telegram Desktop\ТЕХНИЧЕСКОЕ ЗАДАНИЕ (2).docx` (канонический вариант, более подробный) и `ТЕХНИЧЕСКОЕ ЗАДАНИЕ.docx` (краткий). При расхождениях — приоритет у `(2)`.

---

## 0. Решённые архитектурные вопросы (НЕ переутверждать)

| Вопрос | Решение |
|---|---|
| Парсинг чатов | **Telethon** (MTProto userbot) |
| Админка / доставка лидов | **aiogram 3.x** (Bot API) |
| Связь между ними | Общий `asyncio.Queue` в процессе, общая БД |
| БД | **PostgreSQL 16** с самого начала, через SQLAlchemy 2.x async + asyncpg |
| Миграции | Alembic |
| Matcher | **pyahocorasick** для substring + скомпилированный regex `\bword\b` для exact-match |
| Хранение сессии Telethon | Файл `data/session.session`, volume в Docker, права `600`, бэкап шифровать вне рамок v1 |
| Админка | aiogram FSM + inline-кнопки, пагинация; slash-команды из ТЗ тоже работают |
| Роли | `OWNER` (из .env, immutable) + `ADMIN` (управляется через бота, только OWNER может добавлять/удалять) |
| Получатель лидов | Один чат менеджеров, ID хранится в `settings` (изменяется через бота) |
| Антидубль | НЕ делаем в v1 |
| Аккаунт | Отдельный, гретый — прогрев не реализуем |
| 152-ФЗ | Отложено, тесты в тестовых чатах |
| Деплой | Docker Compose (`bot` + `postgres`) |
| Python | 3.11+ |

---

## 1. Структура репозитория

```
SMK_BOT/
├── app/
│   ├── __init__.py
│   ├── __main__.py                 # точка входа: python -m app
│   ├── main.py                     # orchestrator: запуск userbot + bot, graceful shutdown
│   ├── config.py                   # pydantic-settings, читает .env
│   │
│   ├── userbot/
│   │   ├── __init__.py
│   │   ├── client.py               # фабрика TelegramClient, login, session-handling
│   │   ├── listener.py             # @client.on(events.NewMessage), фильтр по chats из БД
│   │   ├── chat_ops.py             # join_chat, leave_chat, resolve_entity, get_chat_info
│   │   └── floodwait.py            # декоратор/обёртка FloodWaitGuard
│   │
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── dispatcher.py           # Dispatcher, регистрация роутеров, middleware
│   │   ├── lead_sender.py          # форматирование Lead → отправка в receiver chat
│   │   ├── middlewares/
│   │   │   ├── __init__.py
│   │   │   ├── access.py           # ACL: пропускает только OWNER/ADMIN
│   │   │   └── throttle.py         # 1.1s между send_message в receiver
│   │   ├── keyboards/
│   │   │   ├── __init__.py
│   │   │   ├── main_menu.py        # корневое меню (inline)
│   │   │   ├── chats.py            # список/пагинация чатов
│   │   │   ├── words.py            # список/пагинация ключей, фильтр по категориям
│   │   │   ├── admins.py           # список админов
│   │   │   └── common.py           # confirm Yes/No, back, cancel
│   │   ├── states.py               # все FSM StatesGroup'ы
│   │   └── handlers/
│   │       ├── __init__.py
│   │       ├── start.py            # /start, root menu
│   │       ├── chats.py            # 📥 Чаты: list/add/remove/+slash-commands
│   │       ├── words.py            # 🔑 Ключи: list/add/remove/toggle exact
│   │       ├── import_export.py    # 📤 Импорт/экспорт
│   │       ├── settings.py         # ⚙ Настройки: receiver, rebuild matcher
│   │       ├── admins.py           # 👮 Управление админами (только OWNER)
│   │       ├── status.py           # 📊 Статус, /status, /stop, /startbot
│   │       └── errors.py           # глобальный error handler
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── matcher.py              # KeywordMatcher: Aho-Corasick + exact regex
│   │   ├── normalizer.py           # normalize_text(s) → casefold, ё→е, ...
│   │   ├── extractors.py           # extract_phone, extract_email, extract_tg_link
│   │   ├── lead.py                 # dataclass Lead
│   │   └── bus.py                  # глобальная asyncio.Queue + типы событий
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py                 # engine, async_session_maker, Base
│   │   ├── models.py               # Chat, Keyword, Category, Admin, Setting, LeadLog
│   │   └── repo.py                 # тонкие CRUD-функции
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py               # logging setup, RotatingFileHandler по дням
│       └── heartbeat.py            # asyncio.Task, лог каждые 15 минут
│
├── migrations/                     # alembic
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_normalizer.py
│   ├── test_matcher.py
│   ├── test_extractors.py
│   └── fixtures/
│       └── sample_messages.py
│
├── data/                           # gitignored
│   └── session.session             # Telethon session
├── logs/                           # gitignored
│
├── .env.example
├── .gitignore
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml                  # или requirements.txt — выбрать одно
├── README.md
└── PLAN.md                         # этот файл
```

---

## 2. Зависимости

`pyproject.toml` (или requirements.txt — на усмотрение):

```
python = ">=3.11,<3.13"

aiogram = "^3.13"
telethon = "^1.36"
SQLAlchemy = {extras = ["asyncio"], version = "^2.0"}
asyncpg = "^0.29"
alembic = "^1.13"
pydantic = "^2.7"
pydantic-settings = "^2.4"
pyahocorasick = "^2.1"
python-dotenv = "^1.0"             # читать .env в dev (Docker сам пробрасывает)
cryptg = "^0.4"                    # ускорение Telethon (опционально, рекомендуется)

# dev
pytest = "^8.3"
pytest-asyncio = "^0.23"
ruff = "^0.6"
mypy = "^1.11"
```

---

## 3. Конфигурация (.env.example)

```env
# Telegram API (https://my.telegram.org)
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_PHONE=+7900XXXXXXX           # номер userbot-аккаунта

# aiogram bot (@BotFather)
BOT_TOKEN=

# OWNERs — иммутабельные суперадмины через запятую (Telegram user_id)
OWNER_IDS=123456789,987654321

# База
POSTGRES_DSN=postgresql+asyncpg://smk:smk@postgres:5432/smk

# Логи
LOG_LEVEL=INFO
LOG_DIR=./logs

# Пути
SESSION_PATH=./data/session

# Параметры рантайма
RECEIVER_CHAT_ID=                     # опц., можно задать через бота /setreceiver
HEARTBEAT_INTERVAL_SEC=900            # 15 минут
JOIN_CHAT_DELAY_SEC=25                # средняя задержка между join'ами
LEAD_SEND_DELAY_SEC=1.1               # антифлуд для send_message
```

`app/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    telegram_api_id: int
    telegram_api_hash: str
    telegram_phone: str

    bot_token: str
    owner_ids: list[int]

    postgres_dsn: str
    session_path: str = "./data/session"

    log_level: str = "INFO"
    log_dir: str = "./logs"

    receiver_chat_id: int | None = None
    heartbeat_interval_sec: int = 900
    join_chat_delay_sec: int = 25
    lead_send_delay_sec: float = 1.1

    @field_validator("owner_ids", mode="before")
    @classmethod
    def parse_owner_ids(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v

settings = Settings()
```

---

## 4. Схема БД

SQLAlchemy 2.x declarative с typed Mapped[]. Один файл `app/db/models.py`.

```python
from datetime import datetime
from enum import StrEnum
from sqlalchemy import BigInteger, String, Boolean, ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    pass

class MatchType(StrEnum):
    SUBSTRING = "substring"
    EXACT = "exact"

class AdminRole(StrEnum):
    OWNER = "owner"          # из .env, не хранится в БД (но мог бы)
    ADMIN = "admin"          # хранится в БД, добавлен через бота

class Chat(Base):
    __tablename__ = "chats"
    id:          Mapped[int]     = mapped_column(primary_key=True)
    tg_id:       Mapped[int]     = mapped_column(BigInteger, unique=True)  # отрицательные для супергрупп
    title:       Mapped[str]     = mapped_column(String(256))
    username:    Mapped[str | None] = mapped_column(String(64), nullable=True)
    invite_link: Mapped[str | None] = mapped_column(String(256), nullable=True)
    active:      Mapped[bool]    = mapped_column(Boolean, default=True)
    added_at:    Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    added_by:    Mapped[int]     = mapped_column(BigInteger)  # tg user_id админа

class Category(Base):
    __tablename__ = "categories"
    id:    Mapped[int] = mapped_column(primary_key=True)
    name:  Mapped[str] = mapped_column(String(64), unique=True)
    keywords: Mapped[list["Keyword"]] = relationship(back_populates="category")

class Keyword(Base):
    __tablename__ = "keywords"
    __table_args__ = (UniqueConstraint("text", "match_type", name="uq_keyword_text_match"),)
    id:          Mapped[int] = mapped_column(primary_key=True)
    text:        Mapped[str] = mapped_column(String(256))
    match_type:  Mapped[MatchType] = mapped_column(String(16), default=MatchType.SUBSTRING)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    active:      Mapped[bool] = mapped_column(Boolean, default=True)
    added_at:    Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    added_by:    Mapped[int]  = mapped_column(BigInteger)
    category:    Mapped[Category | None] = relationship(back_populates="keywords")

class Admin(Base):
    __tablename__ = "admins"
    id:        Mapped[int] = mapped_column(primary_key=True)
    tg_id:     Mapped[int] = mapped_column(BigInteger, unique=True)
    username:  Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    role:      Mapped[AdminRole] = mapped_column(String(16), default=AdminRole.ADMIN)
    added_by:  Mapped[int] = mapped_column(BigInteger)  # tg_id того, кто добавил (OWNER)
    added_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    active:    Mapped[bool] = mapped_column(Boolean, default=True)

class Setting(Base):
    __tablename__ = "settings"
    key:   Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)

class LeadLog(Base):
    """Минимальный лог отправленных лидов — для статистики и будущего антидубля."""
    __tablename__ = "lead_log"
    id:           Mapped[int] = mapped_column(primary_key=True)
    chat_id:      Mapped[int] = mapped_column(BigInteger)
    message_id:   Mapped[int] = mapped_column(BigInteger)
    author_id:    Mapped[int] = mapped_column(BigInteger)
    matched_words: Mapped[str] = mapped_column(Text)  # CSV
    sent_at:      Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

**Settings keys (как используем `settings` таблицу):**
- `receiver_chat_id` — текущий чат менеджеров (изменяется через бота).
- `monitoring_enabled` — `"1"` / `"0"`, флаг `/stop`/`/startbot`.

**Bootstrap (на старте main.py):**
1. Создать категории, если нет: `СРО и специалисты`, `Лицензии и реестры`, `ЭПБ`, `Документация и ИСО`, `Сертификация и экспорт`, `Тендеры`, `Прочее`.
2. Положить в `settings`: `monitoring_enabled=1` (если нет).
3. **НЕ** записывать OWNER в `admins` — OWNER живёт только в .env. ACL проверяет: `is_owner(uid) or db_admin_active(uid)`.

---

## 5. Matcher — детально

`app/core/normalizer.py`:

```python
import re

_RUS_E_MAP = str.maketrans("ёЁ", "ее")
_WS_RE = re.compile(r"\s+")

def normalize(text: str) -> str:
    """Приводит к виду для поиска: lowercase, ё→е, схлопывает пробелы.
    НЕ удаляет пунктуацию — она нужна для границ \b в exact-match.
    """
    s = text.translate(_RUS_E_MAP).casefold()
    s = _WS_RE.sub(" ", s)
    return s.strip()
```

`app/core/matcher.py`:

```python
import re
from dataclasses import dataclass
import ahocorasick
from app.core.normalizer import normalize

@dataclass(frozen=True)
class KeywordSpec:
    id: int
    text: str            # оригинал (для отображения)
    normalized: str      # после normalize()
    exact: bool
    category: str | None

class KeywordMatcher:
    """Потокобезопасный матчер. Перестраивается целиком при изменении словаря."""

    def __init__(self, specs: list[KeywordSpec]):
        self._specs_by_id: dict[int, KeywordSpec] = {s.id: s for s in specs}

        # Substring: один Aho-Corasick для всех substring-ключей
        self._aho = ahocorasick.Automaton()
        for s in specs:
            if not s.exact:
                # ключ автомата — нормализованный текст,
                # значение — id ключевого слова (для маппинга обратно)
                self._aho.add_word(s.normalized, s.id)
        self._aho.make_automaton()

        # Exact: один скомпилированный regex по альтернативам, с границами \b.
        # Для русских аббревиатур \b работает корректно (в Python re \w включает кириллицу).
        exact_alts = [re.escape(s.normalized) for s in specs if s.exact]
        if exact_alts:
            # ID кладём в named groups? Нет — проще сматчить и потом найти, какой именно.
            # Зато компактно. Для 50 аббревиатур скорость избыточна.
            self._exact_re = re.compile(r"\b(" + "|".join(exact_alts) + r")\b")
            self._exact_norm_to_id = {s.normalized: s.id for s in specs if s.exact}
        else:
            self._exact_re = None
            self._exact_norm_to_id = {}

    def match(self, text: str) -> list[KeywordSpec]:
        """Возвращает уникальный список сматченных KeywordSpec."""
        norm = normalize(text)
        matched_ids: set[int] = set()

        # substring
        for _end, kw_id in self._aho.iter(norm):
            matched_ids.add(kw_id)

        # exact
        if self._exact_re:
            for m in self._exact_re.finditer(norm):
                kw_id = self._exact_norm_to_id.get(m.group(1))
                if kw_id is not None:
                    matched_ids.add(kw_id)

        return [self._specs_by_id[i] for i in matched_ids]
```

**Hot-reload:** в `app/core/bus.py` живёт глобальный `current_matcher: KeywordMatcher | None` + `matcher_lock = asyncio.Lock()`. Функция `rebuild_matcher(session)` вычитывает все active keywords из БД, строит новый KeywordMatcher и атомарно подменяет ссылку. Вызывается:
- на старте main.py,
- после `/addword`, `/removeword`, импорта, переключения exact/substr,
- по кнопке «🔄 Перестроить matcher» в настройках.

---

## 6. Extractors

`app/core/extractors.py`:

```python
import re

# RU и общие международные форматы. Не пытаемся валидировать — извлекаем первое попавшееся.
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
```

Тесты обязательны — позитивные и негативные кейсы из ТЗ.

---

## 7. Поток событий

`app/core/lead.py`:

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Lead:
    chat_tg_id: int
    chat_title: str
    message_id: int
    message_link: str            # https://t.me/c/... или https://t.me/username/...
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
```

`app/core/bus.py`:

```python
import asyncio
from app.core.lead import Lead
from app.core.matcher import KeywordMatcher

# Очередь между userbot и bot
lead_queue: asyncio.Queue[Lead] = asyncio.Queue(maxsize=1000)

# Hot-reload matcher
_current_matcher: KeywordMatcher | None = None
_matcher_lock = asyncio.Lock()

async def get_matcher() -> KeywordMatcher | None:
    return _current_matcher

async def set_matcher(m: KeywordMatcher) -> None:
    global _current_matcher
    async with _matcher_lock:
        _current_matcher = m
```

`app/userbot/listener.py` — псевдокод:

```python
@client.on(events.NewMessage())
async def on_message(event):
    # 0. фильтр: чат должен быть в БД и active
    if event.chat_id not in active_chat_ids_cache:
        return
    matcher = await get_matcher()
    if matcher is None:
        return
    matches = matcher.match(event.raw_text or "")
    if not matches:
        return
    sender = await event.get_sender()
    chat = await event.get_chat()
    lead = Lead(
        chat_tg_id=event.chat_id,
        chat_title=getattr(chat, "title", "") or "",
        message_id=event.id,
        message_link=_build_link(chat, event.id),
        author_id=sender.id,
        author_username=getattr(sender, "username", None),
        author_first_name=getattr(sender, "first_name", None),
        author_last_name=getattr(sender, "last_name", None),
        text=event.raw_text or "",
        matched_words=[m.text for m in matches],
        extracted_phone=extract_phone(event.raw_text or ""),
        extracted_email=extract_email(event.raw_text or ""),
        extracted_tg=extract_tg_username(event.raw_text or ""),
    )
    await lead_queue.put(lead)
```

`active_chat_ids_cache` — `set[int]`, обновляется при любых изменениях через тот же rebuild-механизм, что и matcher. Альтернатива (проще) — на каждом сообщении лезть в БД, но это дорого. Лучше кэш.

`_build_link`:
- если у чата есть `username` → `https://t.me/{username}/{message_id}`
- иначе для супергрупп: `https://t.me/c/{abs(chat_id) - 1_000_000_000_000}/{message_id}` (Telegram convention: убрать префикс `-100`).

`app/bot/lead_sender.py` — псевдокод:

```python
async def lead_sender_loop(bot: Bot):
    while True:
        lead: Lead = await lead_queue.get()
        try:
            await _send_one(bot, lead)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
            await _send_one(bot, lead)
        except Exception:
            log.exception("failed to send lead")
        finally:
            await asyncio.sleep(settings.lead_send_delay_sec)
            lead_queue.task_done()

def format_lead(lead: Lead) -> str:
    # ТЗ-2 п.2.5 — точный формат
    ...
```

Формат сообщения — берём шаблон из ТЗ-2 п.2.5 буквально, только подставляя реальные значения. Эмодзи оставить. Если телефона/email нет — соответствующие строки **не выводим** (а не пишем «не найдено»).

---

## 8. Админ-панель — детально

### 8.1 Главное меню (`📊` показывает текущий статус)

```
СМК-БОТ — мониторинг АКТИВЕН ✅
Чатов: {N}   Слов: {M}   Лидов за 24ч: {K}
Получатель: «{receiver_title}»

[ 📥 Чаты ]      [ 🔑 Ключи ]
[ 📤 Импорт ]   [ 📊 Статус ]
[ ⏸ Пауза ]     [ ⚙ Настройки ]
[ 👮 Админы ]   (только OWNER видит)
```

Callback data: `cb:menu:chats`, `cb:menu:words` и т.д. Договорённость о формате `cb:` — см. ниже.

### 8.2 Соглашение о callback_data

Формат: `<scope>:<action>:<arg1>:<arg2>...` где аргументы только цифры/латиница.
Максимум 64 байта (Telegram limit).

Примеры:
- `cb:menu:chats` — открыть раздел чатов
- `cb:chat:del:42` — кнопка удалить чат с id=42
- `cb:chat:del_yes:42` / `cb:chat:del_no:42` — подтверждение
- `cb:word:list:cat=1:page=2` — список слов категории 1, страница 2
- `cb:word:toggle:42` — переключить match_type
- `cb:admin:del:99` — удалить админа

Парсер callback'ов — простой `split(":")` + dispatch по второму элементу.

### 8.3 FSM состояния (`app/bot/states.py`)

```python
from aiogram.fsm.state import State, StatesGroup

class AddChat(StatesGroup):
    waiting_link = State()

class AddWord(StatesGroup):
    waiting_text = State()
    choosing_category = State()
    choosing_match_type = State()

class ImportWords(StatesGroup):
    waiting_file = State()
    confirming = State()           # бот показал превью «новых X, дубликатов Y»

class SetReceiver(StatesGroup):
    waiting_forward = State()      # ждём forward из целевого чата ИЛИ ввод ID

class AddAdmin(StatesGroup):
    waiting_contact = State()      # ждём forward сообщения или ввод user_id
```

### 8.4 Slash-команды (из ТЗ — тоже должны работать)

Все команды дублируют функционал кнопок, чтобы заказчик мог пользоваться как привык:

| Команда | Доступ | Аналог в UI |
|---|---|---|
| `/start` | все админы | главное меню |
| `/addchat <link>` | admin | 📥 Чаты → ➕ |
| `/removechat <id>` | admin | 📥 Чаты → ✕ |
| `/listchats` | admin | 📥 Чаты |
| `/addword <text>` | admin | 🔑 Ключи → ➕ |
| `/addwords w1, w2, ...` | admin | масс-добавление |
| `/removeword <text>` | admin | 🔑 Ключи → ✕ |
| `/listwords` | admin | 🔑 Ключи |
| `/exportwords` | admin | 📤 → Экспорт |
| `/importwords` (с файлом) | admin | 📤 → Импорт |
| `/setreceiver` (forward или id) | admin | ⚙ → получатель |
| `/status` | admin | 📊 |
| `/stop` | admin | ⏸ |
| `/startbot` | admin | ⏸ (toggle) |
| `/addadmin <id или forward>` | **OWNER only** | 👮 → ➕ |
| `/removeadmin <id>` | **OWNER only** | 👮 → ✕ |
| `/listadmins` | admin (видеть могут все, удалять только OWNER) | 👮 |

### 8.5 ACL middleware

```python
class AccessMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user is None:
            return
        uid = user.id
        is_owner = uid in settings.owner_ids
        is_admin = is_owner or await repo.is_active_admin(session, uid)
        if not is_admin:
            return                  # тихо игнорируем
        data["is_owner"] = is_owner
        data["is_admin"] = True
        return await handler(event, data)
```

В хендлерах добавления админов — отдельная проверка `if not is_owner: return` (показываем «Только OWNER»).

---

## 9. Импорт / экспорт ключей

**Формат файла** (UTF-8, .txt, по строке на ключ):

```
# Комментарии после # игнорируются
сро
вступление в СРО
=НОК           # знак равенства в начале = exact match
=СГР
=ЭПБ
сертификация ИСО | ИСО                # категория после "|" (опционально)
```

Парсер:
1. Strip пустых и комментариев.
2. Если строка начинается с `=` → exact=True, иначе substring.
3. Если в строке есть ` | category_name` → пытаемся найти категорию по имени; если нет — создаём.

**Импорт-флоу:**
1. Пользователь жмёт «📥 Импорт» → FSM `ImportWords.waiting_file`.
2. Присылает .txt.
3. Парсим, считаем `(new, duplicate, invalid)` без записи.
4. Показываем превью + кнопки `[✅ Импортировать N] [✖ Отмена]`.
5. На подтверждение — пакетный insert, rebuild matcher.

**Экспорт:** обратное преобразование в тот же формат, отправляется как Document.

---

## 10. Heartbeat и логи

`app/utils/logger.py`:
- Корневой логгер, формат: `%(asctime)s %(levelname)s [%(name)s] %(message)s`.
- Хендлеры: stdout + `TimedRotatingFileHandler` по дням, хранить 14 файлов.

`app/utils/heartbeat.py`:
```python
async def heartbeat_loop():
    while True:
        log.info("heartbeat | chats=%d words=%d qsize=%d",
                 cache.chat_count, cache.word_count, lead_queue.qsize())
        await asyncio.sleep(settings.heartbeat_interval_sec)
```

---

## 11. Точка входа и graceful shutdown

`app/main.py`:

```python
async def main():
    setup_logging()
    await init_db()
    await bootstrap_categories()
    await reload_caches()              # matcher + active_chats

    client = await build_telethon_client()
    bot, dp = build_aiogram()

    tasks = [
        asyncio.create_task(client.run_until_disconnected(), name="userbot"),
        asyncio.create_task(dp.start_polling(bot), name="bot"),
        asyncio.create_task(lead_sender_loop(bot), name="lead-sender"),
        asyncio.create_task(heartbeat_loop(), name="heartbeat"),
    ]

    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        asyncio.get_event_loop().add_signal_handler(sig, stop.set)

    await stop.wait()
    log.info("shutting down")
    for t in tasks: t.cancel()
    await client.disconnect()
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
```

На Windows `add_signal_handler` не работает — обернуть `try/except NotImplementedError`, в этом случае оставить только KeyboardInterrupt из `asyncio.run`.

---

## 12. Docker

`Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libssl-dev && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .
COPY . .
CMD ["python", "-m", "app"]
```

`docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: smk
      POSTGRES_PASSWORD: smk
      POSTGRES_DB: smk
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U smk"]
      interval: 5s
      retries: 10

  bot:
    build: .
    depends_on:
      postgres:
        condition: service_healthy
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped

volumes:
  pg_data:
```

**Первый запуск Telethon** требует ввода кода из SMS — это делается интерактивно. План: один раз запускают `python -m app.userbot.client --login` ВНЕ Docker, получают `data/session.session`, дальше Docker подхватывает его как volume. Опишем в README.

---

## 13. Порядок реализации (для Sonnet)

Делать **строго по этапам, в этом порядке**. После каждого этапа — коммит и проверка, что код запускается.

### Этап 1 — Скелет (день 1)
- [ ] Создать структуру папок (раздел 1).
- [ ] `pyproject.toml` с зависимостями (раздел 2).
- [ ] `.env.example`, `.gitignore` (исключить `data/`, `logs/`, `.env`, `__pycache__`, `.venv`).
- [ ] `app/config.py` (раздел 3) + быстрый тест: `python -c "from app.config import settings; print(settings.owner_ids)"`.
- [ ] `app/db/base.py` — engine, async sessionmaker.
- [ ] `app/db/models.py` (раздел 4).
- [ ] `docker-compose.yml` + `Dockerfile` (раздел 12).
- [ ] Alembic init + первая миграция: `alembic revision --autogenerate -m "initial"` → `alembic upgrade head`.
- [ ] `app/utils/logger.py` (раздел 10).
- [ ] Stub `app/main.py` который запускается, печатает «started» и спит.
- [ ] `docker compose up postgres bot` запускается без ошибок.

**Acceptance:** контейнер `bot` стартует, в логах «started», БД содержит таблицы из миграции.

### Этап 2 — Matcher и extractors (полдня)
- [ ] `app/core/normalizer.py` + тест `tests/test_normalizer.py`.
- [ ] `app/core/extractors.py` + тест `tests/test_extractors.py` (минимум 5 позитивных + 3 негативных кейса на каждую функцию).
- [ ] `app/core/matcher.py` (раздел 5) + тест `tests/test_matcher.py`. Обязательные кейсы:
    - substring matching (`"СРО"` находит «вступить в СРО»),
    - exact ловит `"НОК"`, но не `"кому"` (несмотря на то, что `нок` — подстрока `"кому"`... стоп, не находится без exact, проверить),
    - смесь substring+exact в одном тексте,
    - кириллица `ё` нормализуется,
    - сэмпл из ТЗ-2 п.2.5.
- [ ] `app/core/bus.py`, `app/core/lead.py`.

**Acceptance:** `pytest` зелёный.

### Этап 3 — DB repo и кэши (полдня)
- [ ] `app/db/repo.py` — функции: `get_active_chats()`, `get_active_keywords()`, `is_active_admin(uid)`, `get_setting(key)`, `set_setting(key, value)`, `add_chat`, `remove_chat`, `add_keyword`, `remove_keyword`, `add_admin`, `remove_admin`, `list_admins`, и т.д.
- [ ] В `bus.py` — функция `reload_caches(session)` строит matcher + обновляет `active_chat_ids_cache`.
- [ ] Bootstrap категорий в `main.py`.

**Acceptance:** unit-тест: вставить ключевые в БД → `reload_caches` → matcher находит.

### Этап 4 — Telethon listener (день)
- [ ] `app/userbot/client.py` — фабрика, поддержка `--login` CLI mode.
- [ ] `app/userbot/floodwait.py` — обёртка с экспоненциальной задержкой.
- [ ] `app/userbot/chat_ops.py` — `join`, `leave`, `resolve_entity`.
- [ ] `app/userbot/listener.py` (раздел 7).
- [ ] В `main.py` запускаем userbot параллельно с stub bot'ом.

**Acceptance:** залогиниться вручную, добавить тестовый чат в БД руками (через psql), отправить туда сообщение со словом «СРО» → в логе бот пишет «matched».

### Этап 5 — aiogram skeleton + access middleware (полдня)
- [ ] `app/bot/dispatcher.py` — Bot, Dispatcher, регистрация роутеров.
- [ ] `app/bot/middlewares/access.py` (раздел 8.5).
- [ ] `app/bot/handlers/start.py` — `/start`, корневое меню (раздел 8.1).
- [ ] `app/bot/keyboards/main_menu.py`.

**Acceptance:** OWNER пишет боту `/start` → видит меню. Не-OWNER пишет → молчание.

### Этап 6 — Доставка лидов (полдня)
- [ ] `app/bot/lead_sender.py` (раздел 7) + `format_lead` по ТЗ-2 п.2.5.
- [ ] Команда `/setreceiver` (handlers/settings.py): принимает forward или ID, сохраняет в `settings`.
- [ ] `app/bot/middlewares/throttle.py` — семафор на отправку.

**Acceptance:** залить тестовое слово в БД, отправить в тестовый чат сообщение → менеджерский чат получает форматированный лид.

### Этап 7 — Управление чатами (полдня)
- [ ] `handlers/chats.py`: list (с пагинацией), add (FSM AddChat → Telethon.join → запись в БД → rebuild caches), remove (с confirm).
- [ ] Slash-команды `/addchat`, `/removechat`, `/listchats`.
- [ ] `keyboards/chats.py` — inline-кнопки.

**Acceptance:** через бота можно добавить чат по ссылке, увидеть его в списке, удалить.

### Этап 8 — Управление словами (день)
- [ ] `handlers/words.py`: list с пагинацией и фильтром по категориям, add (FSM AddWord), toggle exact/substring, remove.
- [ ] Slash-команды `/addword`, `/addwords` (через запятую), `/removeword`, `/listwords`.

**Acceptance:** добавить слово через FSM, переключить на exact, удалить.

### Этап 9 — Импорт/экспорт (полдня)
- [ ] `handlers/import_export.py` (раздел 9).
- [ ] Slash-команды `/importwords`, `/exportwords`.

**Acceptance:** экспортировать → отредактировать → импортировать обратно, бот показывает «новых X, дубликатов Y», подтверждение работает.

### Этап 10 — Управление админами (полдня)
- [ ] `handlers/admins.py`: list, add (FSM AddAdmin: ждёт forward от целевого юзера или ввод user_id), remove. Только OWNER может add/remove.
- [ ] Slash `/addadmin`, `/removeadmin`, `/listadmins`.
- [ ] В list_admins показывать OWNER'ов (из .env) с пометкой «(owner)» и без кнопки удалить, а ADMIN'ов из БД — с кнопкой удалить.

**Acceptance:** OWNER добавил юзера → юзер стал админом → может управлять чатами/словами, но не админами. OWNER удалил → юзер потерял доступ.

### Этап 11 — Status, stop/start, heartbeat (полдня)
- [ ] `handlers/status.py`: `/status`, `/stop`, `/startbot`. При `monitoring_enabled=0` listener пропускает все события.
- [ ] `app/utils/heartbeat.py` запускается из main.py.

**Acceptance:** `/stop` → новые сообщения не дают лидов. `/startbot` → снова дают. `/status` показывает корректные счётчики.

### Этап 12 — Стабилизация и тесты (1-2 дня)
- [ ] FloodWaitGuard в местах: join, resolve_entity.
- [ ] Глобальный error handler aiogram (`handlers/errors.py`) — логирует и уведомляет OWNER.
- [ ] README с инструкцией: создать .env, `python -m app.userbot.client --login`, `docker compose up`.
- [ ] Скрипт бэкапа `scripts/backup.sh` — `pg_dump` + копия `data/session.session`.
- [ ] 48 часов uptime-теста на тестовых чатах.

**Acceptance:** см. ТЗ-2 п.6.

---

## 14. Что НЕ делаем в v1 (явно)

- Не делаем антидубль.
- Не делаем per-category routing получателей.
- Не делаем web-админку.
- Не делаем многопроцессность / multi-account.
- Не делаем прогрев аккаунта.
- Не шифруем session-файл (только volume + права).
- Не делаем GDPR/152-ФЗ механики (right-to-erasure и т.п.).
- Не используем Redis.

Это «v2 backlog», если будет.

---

## 15. Sonnet — заметки по стилю

- **Не выдумывай новые архитектурные решения.** Если что-то непонятно — оставь TODO с вопросом, не делай молча.
- **Не пиши обёртки и хелперы про запас.** Если функция вызывается один раз — она inline.
- **Не добавляй docstrings и type hints, выходящие за рамки правил Pyright/mypy strict.** Типы — да; нарратив в docstring — нет.
- **Не добавляй try/except «на всякий случай».** Глобальный error handler aiogram уже ловит всё в хендлерах. В userbot — критичные операции уже обёрнуты FloodWaitGuard.
- **Не выводи print** — используй logger.
- **Эмодзи в коде/комментариях не используем.** В пользовательских сообщениях бота — да, как в шаблонах ТЗ.
- **Все async** — никаких блокирующих вызовов (включая запись в БД, файлы должны быть `aiofiles` или offload в thread).
- **Текст для пользователя пишем на русском.** Логи — на английском.
- **Коммиты делай этапами** — `feat: skeleton`, `feat: matcher`, `feat: telethon listener` и т.д. По одному этапу = один коммит (или несколько мелких внутри этапа).

---

## 16. Открытые TODO для уточнения с человеком

(Sonnet — если упрёшься в эти вопросы, спроси человека, не решай сам.)

1. Дефолтный список категорий (раздел 4) — захардкодить как в плане или ждать от заказчика?
2. Что показывать в `/status` если monitoring выключен — менеджерскому чату или только админу запросившему?
3. Сообщение слишком длинное (>4096 символов): резать до 4000 + «…» или отправлять ссылкой и куском?
4. Если в одном сообщении сматчилось 20 ключевых слов — все перечислять в лиде или первые 5 + «… и ещё 15»?
