"""
database.py — PostgreSQL async bağlantı iskeleti.
SQLAlchemy AsyncEngine ve session factory; tüm sorgularda tenant_id filtresi zorunludur (CLAUDE.md).
"""

from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_settings = get_settings()
# asyncpg sürücüsü kullanılır (postgresql+asyncpg://...)
_engine = create_async_engine(_settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Her request için bir DB session üretir.
    İleride tüm sorgularda tenant_id filtresi eklenecek.
    """
    async with AsyncSessionLocal() as session:
        yield session
