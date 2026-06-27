from pydantic_settings import BaseSettings
from functools import lru_cache
import os
import secrets


class Settings(BaseSettings):
    app_name: str = "Argus OSINT"
    debug: bool = False
    api_port: int = 8000
    argus_db_url: str = "sqlite+aiosqlite:///./argus.db"

    secret_key: str = os.getenv("SESSION_SECRET", secrets.token_hex(32))
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_bot_name: str = os.getenv("TELEGRAM_BOT_NAME", "ArgusOSINTBot")

    max_concurrent_investigations: int = 5
    investigation_timeout_seconds: int = 120

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
