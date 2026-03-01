"""
base.py — Tüm SQLAlchemy modellerinin kalıtım alacağı DeclarativeBase.
Alembic metadata bu Base üzerinden kullanılacak.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Ortak Base sınıfı; tablo modelleri buradan türetilecek."""
    pass
