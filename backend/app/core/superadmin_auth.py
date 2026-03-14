"""
superadmin_auth.py - Super admin auth icin ortak helper'lar.
"""

from app.core.config import get_settings


def get_superadmin_secret() -> str:
    """
    Super admin token imza anahtarini dondurur.
    Ayrica compatibility icin SECRET_KEY fallback'i vardir.
    """
    settings = get_settings()
    return settings.super_admin_session_secret or settings.secret_key


def get_superadmin_cookie_name() -> str:
    """Super admin cookie adini dondurur."""
    settings = get_settings()
    return settings.super_admin_cookie_name
