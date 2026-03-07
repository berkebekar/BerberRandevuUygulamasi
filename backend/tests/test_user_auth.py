"""
test_user_auth.py — User OTP auth endpoint'leri için otomatik testler.

Test senaryoları (CURSOR_PROMPTS.md ADIM 4):
  1. Doğru OTP + mevcut kullanıcı → 200 + cookie
  2. Yanlış OTP → 401, attempt_count artar
  3. 3 yanlış deneme → kod iptal (is_used=True), 401
  4. Süresi dolmuş OTP → 401
  5. 60sn rate limit → 429

Gerçek DB bağlantısı gerekmez; get_db dependency override ile mock kullanılır.
Middleware bypass: localhost base_url → dev modda tenant çözümlemesi yapılmaz.
"""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_token, decode_token, hash_password
from app.main import app
from app.modules.auth import service as auth_service
from app.modules.auth.router import get_tenant_id

# Tüm testlerde kullanılacak sabit tenant UUID
TEST_TENANT_ID = uuid.uuid4()
TEST_OTHER_TENANT_ID = uuid.uuid4()


# ─── Yardımcı Fabrika Fonksiyonlar ───────────────────────────────────────────

def _make_otp_record(
    code: str = "123456",
    expired: bool = False,
    attempt_count: int = 0,
    is_used: bool = False,
    tenant_id=TEST_TENANT_ID,
) -> SimpleNamespace:
    """
    Test için OTPRecord benzeri nesne üretir.
    SQLAlchemy mapper'ı atlamak için SimpleNamespace kullanılır.
    Service sadece .code_hash, .attempt_count, .is_used, .expires_at'e erişir.
    """
    expires_at = datetime.now(timezone.utc) + (
        timedelta(minutes=-1) if expired else timedelta(minutes=5)
    )
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        phone="5551234567",
        code_hash=hash_password(code),  # bcrypt hash — verify_password ile karşılaştırılır
        role="user",
        expires_at=expires_at,
        is_used=is_used,
        attempt_count=attempt_count,
    )


def _make_user(phone: str = "5551234567") -> SimpleNamespace:
    """Test için User benzeri nesne üretir."""
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TEST_TENANT_ID,
        phone=phone,
        first_name="Test",
        last_name="Kullanici",
        session_version=str(uuid.uuid4()),
    )


def _make_db_result(value) -> MagicMock:
    """
    db.execute() dönüş değerini taklit eder.
    scalar_one_or_none() → value döndürür.
    """
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


# ─── Test Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_dependency_overrides():
    """
    Her test başlamadan önce ve bittikten sonra dependency_overrides'ı temizler.
    Testlerin birbirini etkilememesi için zorunludur.
    """
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


async def _override_tenant_id():
    """get_tenant_id dependency'sini test tenant ID'siyle değiştirir."""
    return TEST_TENANT_ID


def _make_mock_session(*execute_return_values) -> AsyncMock:
    """
    DB session mock'u oluşturur.
    execute_return_values sıralı olarak döndürülür (side_effect listesi).
    """
    session = AsyncMock()
    session.add = MagicMock()   # sync — sadece objeyi listeye ekler
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    if len(execute_return_values) == 1:
        session.execute = AsyncMock(return_value=execute_return_values[0])
    else:
        # Birden fazla execute() çağrısı için sıralı dönüş değerleri
        session.execute = AsyncMock(side_effect=list(execute_return_values))

    return session


# ─── Testler ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dogru_otp_mevcut_kullanici_200_cookie():
    """
    Doğru OTP + mevcut kullanıcı → 200 ve user_session cookie set edilmeli.
    verify_otp: 1. execute = OTP bul, 2. execute = User bul.
    """
    code = "123456"
    otp_record = _make_otp_record(code=code)
    user = _make_user()

    session = _make_mock_session(
        _make_db_result(otp_record),  # İlk execute: OTP kaydı
        _make_db_result(user),        # İkinci execute: User kaydı
    )

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_id] = _override_tenant_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        r = await client.post(
            "/api/v1/auth/user/verify-otp",
            json={"phone": "5551234567", "code": code},
        )

    assert r.status_code == 200
    assert r.json()["status"] == "returning_user"
    # HTTP-only cookie set edilmeli
    assert "user_session" in r.cookies
    token = r.cookies.get("user_session")
    payload = decode_token(token)
    assert payload.get("role") == "user"
    assert payload.get("sv")
    exp_ts = payload.get("exp")
    assert isinstance(exp_ts, int)
    delta_seconds = exp_ts - int(datetime.now(timezone.utc).timestamp())
    assert 39 * 24 * 60 * 60 <= delta_seconds <= 40 * 24 * 60 * 60 + 120


@pytest.mark.asyncio
async def test_yanlis_otp_401_attempt_count_artar():
    """
    Yanlış OTP → 401 ve attempt_count 1 artmalı.
    OTP is_used=False kalmalı (henüz 3 deneme dolmadı).
    """
    # Doğru kod "999999", biz "111111" göndereceğiz → yanlış
    otp_record = _make_otp_record(code="999999", attempt_count=0)

    session = _make_mock_session(_make_db_result(otp_record))

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_id] = _override_tenant_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        r = await client.post(
            "/api/v1/auth/user/verify-otp",
            json={"phone": "5551234567", "code": "111111"},
        )

    assert r.status_code == 401
    assert r.json() == {"error": "otp_invalid"}
    assert otp_record.attempt_count == 1   # Bir arttı
    assert otp_record.is_used is False     # Henüz iptal edilmedi


@pytest.mark.asyncio
async def test_uc_yanlis_deneme_kodu_iptal_401():
    """
    3. yanlış deneme → is_used=True olmalı (OTP iptal), 401 dönmeli.
    attempt_count=2 ile başlayan record'a bir yanlış daha gönderilir.
    """
    otp_record = _make_otp_record(code="999999", attempt_count=2)

    session = _make_mock_session(_make_db_result(otp_record))

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_id] = _override_tenant_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        r = await client.post(
            "/api/v1/auth/user/verify-otp",
            json={"phone": "5551234567", "code": "111111"},
        )

    assert r.status_code == 401
    assert r.json() == {"error": "otp_invalid"}
    assert otp_record.attempt_count == 3  # 2 → 3
    assert otp_record.is_used is True     # İptal edildi


@pytest.mark.asyncio
async def test_suresi_dolmus_otp_401():
    """
    Süresi dolmuş OTP → DB sorgusu kayıt döndürmez (WHERE expires_at > now filtresi) → 401.
    """
    session = _make_mock_session(
        _make_db_result(None)  # OTP bulunamadı (süresi dolmuş veya kullanılmış)
    )

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_id] = _override_tenant_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        r = await client.post(
            "/api/v1/auth/user/verify-otp",
            json={"phone": "5551234567", "code": "123456"},
        )

    assert r.status_code == 401
    assert r.json() == {"error": "otp_not_found"}


@pytest.mark.asyncio
async def test_rate_limit_60sn_429():
    """
    60sn içinde ikinci send-otp isteği → 429 rate_limit_exceeded.
    DB'de yakın zamanda oluşturulmuş aktif OTP kaydı bulunuyor.

    Neden get_tenant_id override gerekiyor?
    send-otp endpoint'i tenant_id dependency'si kullanıyor.
    Override edilmezse middleware tenant bulamaz → 400 döner, 429 asla görülmez.
    """
    recent_otp = _make_otp_record()  # Aktif, kullanılmamış bir OTP var

    session = _make_mock_session(
        _make_db_result(recent_otp)  # Rate limit sorgusu: kayıt bulundu → 429
    )

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_id] = _override_tenant_id  # Eksikti — 400 yerine 429 görmek için zorunlu

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        r = await client.post(
            "/api/v1/auth/user/send-otp",
            json={"phone": "5551234567"},
        )

    assert r.status_code == 429
    assert r.json() == {"error": "rate_limit_exceeded"}


@pytest.mark.asyncio
async def test_rate_limit_tenant_scoped_allows_other_tenant():
    """
    Tenant A'da aktif OTP varken Tenant B için aynı telefona OTP gönderimi engellenmemeli.
    Bu test doğrudan service katmanını çağırır ve sorguda tenant filtresi olup olmadığını doğrular.
    """
    recent_otp = _make_otp_record(tenant_id=TEST_TENANT_ID)
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    def _side_effect(stmt):
        params = stmt.compile().params
        tenant_param = next((v for k, v in params.items() if "tenant_id" in k), None)
        if tenant_param is None:
            # Tenant filtresi yoksa bilinçli olarak rate limit'e düşür.
            return _make_db_result(recent_otp)
        if tenant_param == TEST_TENANT_ID:
            return _make_db_result(recent_otp)
        return _make_db_result(None)

    session.execute = AsyncMock(side_effect=_side_effect)

    code = await auth_service.send_otp(session, TEST_OTHER_TENANT_ID, "5551234567")

    assert len(code) == 6
    session.add.assert_called_once()
    added = session.add.call_args.args[0]
    assert added.tenant_id == TEST_OTHER_TENANT_ID


@pytest.mark.asyncio
async def test_verify_otp_cross_tenant_not_found():
    """
    Tenant A'da üretilmiş OTP, Tenant B context'inde doğrulanamamalı.
    """
    otp_record = _make_otp_record(code="123456", tenant_id=TEST_TENANT_ID)
    session = AsyncMock()

    def _side_effect(stmt):
        params = stmt.compile().params
        tenant_param = next((v for k, v in params.items() if "tenant_id" in k), None)
        if tenant_param is None:
            # Tenant filtresi yoksa bilinçli olarak kaydı döndür.
            return _make_db_result(otp_record)
        if tenant_param == TEST_TENANT_ID:
            return _make_db_result(otp_record)
        return _make_db_result(None)

    session.execute = AsyncMock(side_effect=_side_effect)
    session.commit = AsyncMock()

    with pytest.raises(Exception) as exc_info:
        await auth_service.verify_otp(
            session,
            TEST_OTHER_TENANT_ID,
            "5551234567",
            "123456",
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == {"error": "otp_not_found"}


@pytest.mark.asyncio
async def test_logout_user_token_sunucu_tarafinda_iptal_edilir():
    """
    Logout cagrisi geldiginde user token decode edilir ve session_version rotate edilir.
    """
    user_id = uuid.uuid4()
    token = create_token(
        {"sub": str(user_id), "role": "user", "sv": str(uuid.uuid4())},
        expires_minutes=30,
    )
    user = _make_user()
    user.id = user_id

    session = _make_mock_session(_make_db_result(user))

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_id] = _override_tenant_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        r = await client.post(
            "/api/v1/auth/logout",
            cookies={"user_session": token},
        )

    assert r.status_code == 200
    assert r.json() == {"message": "logged_out"}
    session.commit.assert_called_once()
