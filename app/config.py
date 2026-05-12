from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

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
    def _parse_owner_ids(cls, v: object) -> object:
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v


settings = Settings()  # type: ignore[call-arg]
