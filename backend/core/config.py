from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_token:       str | None = None
    telegram_allowed_ids: list[int] = []
    database_url:         str       = "sqlite+aiosqlite:///./braille_glove.db"
    ble_scan_timeout:     float     = 10.0
    api_host:             str       = "0.0.0.0"
    api_port:             int       = 8000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
