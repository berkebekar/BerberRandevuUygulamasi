"""
auth/service.py â€” OTP ve kullanÄ±cÄ±/admin auth business logic.

Bu dosya sistemin kritik kurallarÄ±nÄ± iÃ§erir:
- OTP plain text asla saklanmaz (bcrypt hash)
- Rate limit: aynÄ± numaraya 60sn'de 1 OTP
- Max 3 yanlÄ±ÅŸ deneme â†’ OTP iptal
- KullanÄ±cÄ±: Yeni â†’ registration_token, Mevcut â†’ direkt session cookie
- Admin: Tek seferlik kayÄ±t (tenant baÅŸÄ±na 1), iki giriÅŸ yÃ¶ntemi (OTP + ÅŸifre)
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_token, decode_token, hash_password, verify_password
from app.models.admin import Admin
from app.models.enums import OTPRole
from app.models.otp_record import OTPRecord
from app.models.user import User

logger = logging.getLogger(__name__)

_DEFAULT_TEST_OTP_CODE = "123456"


async def send_otp(db: AsyncSession, tenant_id, phone: str) -> str:
    """
    Verilen telefon numarasÄ± iÃ§in 6 haneli OTP Ã¼retir ve DB'ye kaydeder.

    Rate limit kuralÄ±: aynÄ± numaraya son 60sn iÃ§inde aktif OTP varsa 429 fÄ±rlatÄ±r.
    OTP Ã¼retildikten sonra SMS gÃ¶ndermek iÃ§in code string olarak dÃ¶ndÃ¼rÃ¼lÃ¼r
    (router'da BackgroundTask olarak SMS gÃ¶nderilir).

    Returns:
        code: 6 haneli OTP string (SMS iÃ§in)
    """
    # Son 60 saniyede bu numaraya gÃ¶nderilmiÅŸ aktif OTP var mÄ±?
    # Varsa rate limit ihlali â€” 429 dÃ¶n
    sixty_seconds_ago = datetime.now(timezone.utc) - timedelta(seconds=60)
    result = await db.execute(
        select(OTPRecord).where(
            OTPRecord.tenant_id == tenant_id,
            OTPRecord.phone == phone,
            OTPRecord.role == OTPRole.user,
            OTPRecord.is_used == False,  # noqa: E712
            OTPRecord.created_at > sixty_seconds_ago,
        )
    )
    if result.scalar_one_or_none():
        # 60 saniye dolmadan ikinci istek â†’ reddet
        raise HTTPException(429, {"error": "rate_limit_exceeded"})

    # Test/deploy ortamlarÄ±nda SMS saÄŸlayÄ±cÄ±sÄ± olmasa da giriÅŸ/kayÄ±t akÄ±ÅŸÄ±nÄ±n
    # Ã§alÄ±ÅŸabilmesi iÃ§in OTP kodunu sabit kullan.
    code = _DEFAULT_TEST_OTP_CODE
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    # OTP'yi hash'leyerek kaydet â€” plain text asla DB'ye yazÄ±lmaz (CLAUDE.md)
    record = OTPRecord(
        tenant_id=tenant_id,
        phone=phone,
        code_hash=hash_password(code),
        role=OTPRole.user,
        expires_at=expires_at,
        is_used=False,
        attempt_count=0,
    )
    db.add(record)
    await db.commit()

    # Kodu SMS gÃ¶ndermek iÃ§in dÃ¶ndÃ¼r (servis SMS'i bilmez, router bilir)
    return code


async def verify_otp(
    db: AsyncSession,
    tenant_id,
    phone: str,
    code: str,
) -> dict:
    """
    OTP kodunu doÄŸrular, kullanÄ±cÄ± durumunu dÃ¶ndÃ¼rÃ¼r.

    BaÅŸarÄ±lÄ± doÄŸrulamada:
    - KullanÄ±cÄ± varsa: {"status": "returning_user", "user": User}
    - KullanÄ±cÄ± yoksa: {"status": "new_user", "registration_token": "<jwt>"}

    BaÅŸarÄ±sÄ±z durumlarda HTTPException fÄ±rlatÄ±r:
    - 401: OTP bulunamadÄ±, sÃ¼resi dolmuÅŸ veya yanlÄ±ÅŸ
    """
    now = datetime.now(timezone.utc)

    # En gÃ¼ncel aktif OTP kaydÄ±nÄ± bul (sÃ¼resi geÃ§memiÅŸ, kullanÄ±lmamÄ±ÅŸ)
    result = await db.execute(
        select(OTPRecord)
        .where(
            OTPRecord.tenant_id == tenant_id,
            OTPRecord.phone == phone,
            OTPRecord.role == OTPRole.user,
            OTPRecord.is_used == False,  # noqa: E712
            OTPRecord.expires_at > now,
        )
        .order_by(OTPRecord.created_at.desc())
        .limit(1)
    )
    record = result.scalar_one_or_none()

    if record is None:
        # OTP yok veya sÃ¼resi dolmuÅŸ
        raise HTTPException(401, {"error": "otp_not_found"})

    if record.attempt_count >= 3:
        # Zaten 3 yanlÄ±ÅŸ giriÅŸten geÃ§miÅŸ, iptal edilmiÅŸ sayÄ±lÄ±r
        raise HTTPException(401, {"error": "otp_invalid"})

    if not verify_password(code, record.code_hash):
        # YanlÄ±ÅŸ kod: deneme sayÄ±sÄ±nÄ± artÄ±r
        record.attempt_count += 1
        if record.attempt_count >= 3:
            # 3. yanlÄ±ÅŸ deneme: OTP'yi iptal et
            record.is_used = True
        await db.commit()
        raise HTTPException(401, {"error": "otp_invalid"})

    # DoÄŸru kod: OTP'yi kullanÄ±ldÄ± iÅŸaretle
    record.is_used = True
    await db.commit()

    # Bu tenant'ta bu telefon numarasÄ±yla kayÄ±tlÄ± kullanÄ±cÄ± var mÄ±?
    user_result = await db.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.phone == phone,
        )
    )
    user = user_result.scalar_one_or_none()

    if user is None:
        # Yeni kullanÄ±cÄ±: kayÄ±t iÃ§in kÄ±sa Ã¶mÃ¼rlÃ¼ JWT dÃ¶ndÃ¼r
        # Frontend bu token'Ä± alÄ±p isim/soyisim girdikten sonra complete-registration'a gÃ¶nderecek
        registration_token = create_token(
            {
                "sub": phone,
                "tenant_id": str(tenant_id),
                "type": "registration",  # Session token ile karÄ±ÅŸmamasÄ± iÃ§in tip belirlendi
            },
            expires_minutes=10,
        )
        return {"status": "new_user", "registration_token": registration_token, "user": None}

    return {"status": "returning_user", "registration_token": None, "user": user}


# â”€â”€â”€ Admin Service FonksiyonlarÄ± â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def register_admin(
    db: AsyncSession,
    tenant_id,
    email: str,
    phone: str,
    password: str,
) -> Admin:
    """
    Admin kaydÄ± oluÅŸturur (tek seferlik).

    Tenant baÅŸÄ±na yalnÄ±zca 1 admin olabilir (CLAUDE.md).
    Bu tenant iÃ§in zaten admin varsa 409 fÄ±rlatÄ±r.
    Åifre bcrypt ile hash'lenerek saklanÄ±r; plain text asla DB'ye yazÄ±lmaz.

    Returns:
        Admin: Yeni oluÅŸturulan admin nesnesi.
    """
    # Bu tenant'ta admin var mÄ±? UNIQUE constraint DB'de de var ama Ã¶nce API seviyesinde kontrol et
    existing_result = await db.execute(
        select(Admin).where(Admin.tenant_id == tenant_id)
    )
    if existing_result.scalar_one_or_none():
        # Zaten bir admin kayÄ±tlÄ± â€” ikinci kayda izin yok (CLAUDE.md: tenant baÅŸÄ±na 1 admin)
        raise HTTPException(409, {"error": "admin_already_exists"})

    admin = Admin(
        tenant_id=tenant_id,
        email=email,
        phone=phone,
        password_hash=hash_password(password),  # Åifreyi hash'le; plain text saklanmaz
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    return admin


async def send_admin_otp(db: AsyncSession, tenant_id, phone: str) -> str:
    """
    Admin telefon numarasÄ±na 6 haneli OTP gÃ¶nderir.

    KullanÄ±cÄ± OTP ile aynÄ± altyapÄ±yÄ± kullanÄ±r; yalnÄ±zca role=OTPRole.admin farkÄ± vardÄ±r.
    Bu sayede admin ve kullanÄ±cÄ± OTP'leri birbirini etkilemez.
    Rate limit: aynÄ± numaraya 60sn'de 1 OTP.

    Returns:
        code: 6 haneli OTP string (SMS iÃ§in router'a dÃ¶ner).
    """
    # Son 60 saniyede bu numaraya admin OTP gÃ¶nderilmiÅŸ mi?
    sixty_seconds_ago = datetime.now(timezone.utc) - timedelta(seconds=60)
    result = await db.execute(
        select(OTPRecord).where(
            OTPRecord.tenant_id == tenant_id,
            OTPRecord.phone == phone,
            OTPRecord.role == OTPRole.admin,  # Sadece admin OTP'leri kontrol et
            OTPRecord.is_used == False,  # noqa: E712
            OTPRecord.created_at > sixty_seconds_ago,
        )
    )
    if result.scalar_one_or_none():
        # 60 saniye dolmadan ikinci istek â†’ reddet
        raise HTTPException(429, {"error": "rate_limit_exceeded"})

    # Test/deploy ortamlarÄ±nda SMS saÄŸlayÄ±cÄ±sÄ± olmasa da giriÅŸ akÄ±ÅŸÄ±nÄ±n
    # Ã§alÄ±ÅŸabilmesi iÃ§in OTP kodunu sabit kullan.
    code = _DEFAULT_TEST_OTP_CODE
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    record = OTPRecord(
        tenant_id=tenant_id,
        phone=phone,
        code_hash=hash_password(code),  # Plain text saklanmaz (CLAUDE.md)
        role=OTPRole.admin,             # Admin rolÃ¼ â€” user ile karÄ±ÅŸmaz
        expires_at=expires_at,
        is_used=False,
        attempt_count=0,
    )
    db.add(record)
    await db.commit()

    return code


async def verify_admin_otp(
    db: AsyncSession,
    tenant_id,
    phone: str,
    code: str,
) -> Admin:
    """
    Admin OTP kodunu doÄŸrular, Admin nesnesini dÃ¶ndÃ¼rÃ¼r.

    KullanÄ±cÄ± OTP'sinin aksine "yeni kullanÄ±cÄ±" durumu yoktur:
    Admin Ã¶nce kayÄ±t olmuÅŸ olmalÄ±dÄ±r; yoksa 401 fÄ±rlatÄ±r.

    Returns:
        Admin: DoÄŸrulama baÅŸarÄ±lÄ±ysa ilgili admin nesnesi.
    """
    now = datetime.now(timezone.utc)

    # Aktif ve sÃ¼resi geÃ§memiÅŸ admin OTP'sini bul
    result = await db.execute(
        select(OTPRecord)
        .where(
            OTPRecord.tenant_id == tenant_id,
            OTPRecord.phone == phone,
            OTPRecord.role == OTPRole.admin,  # Admin OTP'si olduÄŸundan emin ol
            OTPRecord.is_used == False,  # noqa: E712
            OTPRecord.expires_at > now,
        )
        .order_by(OTPRecord.created_at.desc())
        .limit(1)
    )
    record = result.scalar_one_or_none()

    if record is None:
        # OTP yok veya sÃ¼resi dolmuÅŸ
        raise HTTPException(401, {"error": "otp_not_found"})

    if record.attempt_count >= 3:
        # 3 yanlÄ±ÅŸ denemeden geÃ§miÅŸ, iptal edilmiÅŸ sayÄ±lÄ±r
        raise HTTPException(401, {"error": "otp_invalid"})

    if not verify_password(code, record.code_hash):
        # YanlÄ±ÅŸ kod: deneme sayÄ±sÄ±nÄ± artÄ±r
        record.attempt_count += 1
        if record.attempt_count >= 3:
            # 3. yanlÄ±ÅŸ deneme: OTP'yi iptal et
            record.is_used = True
        await db.commit()
        raise HTTPException(401, {"error": "otp_invalid"})

    # DoÄŸru kod: OTP'yi kullanÄ±ldÄ± iÅŸaretle
    record.is_used = True
    await db.commit()

    # Bu tenant'taki admin'i bul (tenant_id filtresi zorunlu â€” CLAUDE.md)
    admin_result = await db.execute(
        select(Admin).where(
            Admin.tenant_id == tenant_id,
            Admin.phone == phone,
        )
    )
    admin = admin_result.scalar_one_or_none()

    if admin is None:
        # OTP doÄŸru ama bu tenant'ta admin kaydÄ± yok â€” Ã¶nce kayÄ±t gerekli
        raise HTTPException(401, {"error": "admin_not_registered"})

    return admin


async def login_admin_password(
    db: AsyncSession,
    tenant_id,
    email: str,
    password: str,
) -> Admin:
    """
    Email + ÅŸifre ile admin giriÅŸi yapar.

    Email DB'de bulunmazsa veya ÅŸifre yanlÄ±ÅŸsa 401 fÄ±rlatÄ±r.
    Ä°ki farklÄ± hata durumu iÃ§in kasÄ±tlÄ± olarak aynÄ± 401 mesajÄ± kullanÄ±lÄ±r â€”
    hangisinin yanlÄ±ÅŸ olduÄŸunu ifÅŸa etmemek iÃ§in (gÃ¼venlik prensibi).

    Returns:
        Admin: GiriÅŸ baÅŸarÄ±lÄ±ysa ilgili admin nesnesi.
    """
    # Tenant'a ait admin'i email ile ara (tenant_id filtresi zorunlu â€” CLAUDE.md)
    result = await db.execute(
        select(Admin).where(
            Admin.tenant_id == tenant_id,
            Admin.email == email,
        )
    )
    admin = result.scalar_one_or_none()

    if admin is None or not verify_password(password, admin.password_hash):
        # Email bulunamadÄ± veya ÅŸifre yanlÄ±ÅŸ â€” ikisi iÃ§in de aynÄ± hata mesajÄ± (gÃ¼venlik)
        raise HTTPException(401, {"error": "invalid_credentials"})

    return admin


async def complete_registration(
    db: AsyncSession,
    tenant_id,
    registration_token: str,
    first_name: str,
    last_name: str,
) -> User:
    """
    Yeni kullanÄ±cÄ± kayÄ±t tamamlama: registration_token doÄŸrulanÄ±r, User oluÅŸturulur.

    registration_token verify_otp'tan alÄ±nmÄ±ÅŸ, 10 dakika geÃ§erli JWT'dir.
    Token geÃ§ersizse veya tenant uyuÅŸmuyorsa 401 fÄ±rlatÄ±r.
    """
    try:
        payload = decode_token(registration_token)
    except JWTError:
        # GeÃ§ersiz imza, sÃ¼resi dolmuÅŸ veya manipÃ¼le edilmiÅŸ token
        raise HTTPException(401, {"error": "invalid_token"})

    if payload.get("type") != "registration":
        # Session token'Ä± ile kayÄ±t endpointine gelinmiÅŸ â€” reddet
        raise HTTPException(401, {"error": "invalid_token"})

    phone = payload.get("sub")

    if str(tenant_id) != payload.get("tenant_id"):
        # Token farklÄ± bir tenant iÃ§in Ã¼retilmiÅŸ
        raise HTTPException(401, {"error": "invalid_token"})

    # Idempotent: KullanÄ±cÄ± zaten oluÅŸturulmuÅŸsa (aÄŸ yeniden denemesi olabilir) mevcut kaydÄ± dÃ¶n
    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id, User.phone == phone)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    user = User(
        tenant_id=tenant_id,
        phone=phone,
        first_name=first_name,
        last_name=last_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


