"""
config.py — Ortam değişkenlerini okur (CLAUDE.md ENVIRONMENT VARIABLES).
Gerçek değerler .env veya ortamdan gelir; burada sadece iskelet tanımlar.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    CLAUDE.md'deki tüm environment variable'ları temsil eder.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    secret_key: str = "CHANGE_ME_MIN_32_CHARS_SECRET_KEY_FOR_DEV"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    app_domain: str = ""
    allowed_subdomains: str = ""
    env: str = "development"


@lru_cache
def get_settings() -> Settings:
    """
    Ayarları döndürür.
    lru_cache: uygulama ömrü boyunca tek bir Settings nesnesi tutulur;
    her çağrıda .env tekrar okunmaz — performans ve tutarlılık için.
    """
    return Settings()
