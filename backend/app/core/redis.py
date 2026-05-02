"""
core/redis.py — Async Redis bağlantı yönetimi.

WhatsApp bot konuşma state'ini saklamak için kullanılır.
Bağlantı uygulama yaşam döngüsünde bir kez oluşturulur (lazy singleton).
"""

import logging

import redis.asyncio as aioredis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Singleton Redis client döndürür. İlk çağrıda bağlantı açılır."""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info("Redis bağlantısı açıldı: %s", settings.redis_url)
    return _redis_client


async def close_redis() -> None:
    """Uygulama kapanırken bağlantıyı kapat."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis bağlantısı kapatıldı.")
