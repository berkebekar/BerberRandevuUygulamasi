"""
Alembic env.py — Migration ortamı; app.models.Base metadata kullanılacak.
"""
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.models import Base

config = context.config

if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url():
    # Render env vars: DATABASE_URL_SYNC veya DATABASE_URL
    url = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL_SYNC (or DATABASE_URL) is not set for Alembic")

    # async URL gelirse sync'e çevir
    return url.replace("+asyncpg", "")


def run_migrations_offline():
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    conf = config.get_section(config.config_ini_section) or {}
    conf["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        conf,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()