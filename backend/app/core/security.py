"""
security.py — Şifre hash (bcrypt) ve JWT işlemleri.
OTP ve şifre asla plain text saklanmaz (CLAUDE.md).
"""

from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

# bcrypt ile hash; OTP ve admin şifreleri için kullanılacak
_password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Düz metin parolayı bcrypt ile hash'ler."""
    return _password_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Parolanın hash ile eşleşip eşleşmediğini kontrol eder."""
    return _password_context.verify(plain, hashed)


def create_token(data: dict, expires_minutes: int) -> str:
    """
    Verilen data'yı JWT olarak imzalar.
    expires_minutes kadar sonra süresi dolar.
    SECRET_KEY ile HS256 algoritması kullanılır.
    """
    from app.core.config import get_settings

    payload = data.copy()
    # Token'ın ne zaman geçersiz hale geleceğini belirt
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    return jwt.encode(payload, get_settings().secret_key, algorithm="HS256")


def decode_token(token: str) -> dict:
    """
    JWT'yi doğrular ve payload'ı döndürür.
    Geçersiz veya süresi dolmuşsa jose.JWTError fırlatır.
    """
    from app.core.config import get_settings

    # algorithms listesi zorunlu — jose kütüphanesi alg confusion saldırısına karşı bunu ister
    return jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
