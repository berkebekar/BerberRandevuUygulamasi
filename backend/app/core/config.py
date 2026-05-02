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
    app_domain: str = ""
    allowed_subdomains: str = ""
    env: str = "development"
    super_admin_session_secret: str = ""
    super_admin_cookie_name: str = "superadmin_session"
    superadmin_stats_cache_ttl_seconds: int = 30

    # Redis — konuşma state yönetimi için (WhatsApp botu)
    redis_url: str = "redis://localhost:6379/0"

    # WhatsApp Business API (Meta Cloud API)
    # wa_verify_token: Meta dashboard'a girilen webhook doğrulama tokeni (platform geneli)
    # wa_phone_number_id ve wa_access_token: Tenant bazında DB'de tutulur,
    # ancak platform geneli default olarak da buradan okunabilir.
    wa_verify_token: str = ""


@lru_cache
def get_settings() -> Settings:
    """
    Ayarları döndürür.
    lru_cache: uygulama ömrü boyunca tek bir Settings nesnesi tutulur;
    her çağrıda .env tekrar okunmaz — performans ve tutarlılık için.
    """
    return Settings()
