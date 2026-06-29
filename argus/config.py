from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os
import secrets


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Argus OSINT"
    debug: bool = False
    api_port: int = 8000
    argus_db_url: str = "sqlite+aiosqlite:///./argus.db"

    secret_key: str = os.getenv("SESSION_SECRET", secrets.token_hex(32))
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_bot_name: str = os.getenv("TELEGRAM_BOT_NAME", "ArgusOSINTBot")

    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

    cors_origins: str = "*"
    max_concurrent_investigations: int = 5
    investigation_timeout_seconds: int = 120
    data_retention_days: int = 90

    # SMTP (email notifications)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_email: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
