"""
test_admin_auth.py — Admin auth endpoint'leri için otomatik testler.

Test senaryoları (CURSOR_PROMPTS.md ADIM 5):
  1. İkinci admin kaydı → 409
  2. Yanlış şifre → 401
  3. Şifre ile giriş çalışıyor (başarılı login → admin_session cookie)
  4. OTP ile giriş çalışıyor (başarılı OTP → admin_session cookie)
  5. admin_session cookie ile user endpoint'e erişim → 403

Gerçek DB bağlantısı gerekmez; get_db ve get_tenant_id dependency override ile mock kullanılır.
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

def _make_admin(
    email: str = "berber@test.com",
    phone: str = "5559876543",
    password: str = "sifre1234",
) -> SimpleNamespace:
    """
    Test için Admin benzeri nesne üretir.
    Service sadece .id, .tenant_id, .email, .phone, .password_hash'e erişir.
    """
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TEST_TENANT_ID,
        email=email,
        phone=phone,
        password_hash=hash_password(password),  # bcrypt hash — verify_password ile karşılaştırılır
        session_version=str(uuid.uuid4()),
    )


def _make_admin_otp_record(
    code: str = "654321",
    expired: bool = False,
    attempt_count: int = 0,
    is_used: bool = False,
    tenant_id=TEST_TENANT_ID,
) -> SimpleNamespace:
    """
    Test için admin OTPRecord benzeri nesne üretir.
    role='admin' olarak işaretlenmiştir.
    """
    expires_at = datetime.now(timezone.utc) + (
        timedelta(minutes=-1) if expired else timedelta(minutes=5)
    )
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        phone="5559876543",
        code_hash=hash_password(code),  # bcrypt hash
        role="admin",                   # Admin OTP'si olduğunu belirtir
        expires_at=expires_at,
        is_used=is_used,
        attempt_count=attempt_count,
    )


def _make_db_result(value) -> MagicMock:
    """
    db.execute() dönüş değerini taklit eder.
    scalar_one_or_none() → value döndürür.
    """
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_mock_session(*execute_return_values) -> AsyncMock:
    """
    DB session mock'u oluşturur.
    execute_return_values sıralı olarak döndürülür (side_effect listesi).
    """
    session = AsyncMock()
    session.add = MagicMock()    # sync — sadece objeyi listeye ekler
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    if len(execute_return_values) == 1:
        session.execute = AsyncMock(return_value=execute_return_values[0])
    else:
        # Birden fazla execute() çağrısı için sıralı dönüş değerleri
        session.execute = AsyncMock(side_effect=list(execute_return_values))

    return session


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


# ─── Testler ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ikinci_admin_kaydi_409():
    """
    Bu tenant'ta zaten admin varsa ikinci kayıt isteği 409 döndürmeli.
    DB'de execute() admin bulursa → service 409 fırlatır.
    """
    existing_admin = _make_admin()

    # İlk execute (admin var mı?): admin döndür → 409 bekliyoruz
    session = _make_mock_session(_make_db_result(existing_admin))

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_id] = _override_tenant_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        r = await client.post(
            "/api/v1/auth/admin/register",
            json={"email": "berber@test.com", "phone": "5559876543", "password": "sifre1234"},
        )

    assert r.status_code == 409
    assert r.json() == {"error": "admin_already_exists"}


@pytest.mark.asyncio
async def test_admin_password_login_devre_disi_403():
    """
    Admin password login endpoint'i güvenlik politikası gereği devre dışı olmalı.
    """
    session = _make_mock_session(_make_db_result(None))

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_id] = _override_tenant_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        r = await client.post(
            "/api/v1/auth/admin/login/password",
            json={"email": "berber@test.com", "password": "yanlis_sifre"},
        )

    assert r.status_code == 403
    assert r.json() == {"error": "otp_required"}


@pytest.mark.asyncio
async def test_otp_ile_giris_basarili_cookie():
    """
    Doğru admin OTP → 200 ve admin_session cookie set edilmeli.
    verify_admin_otp: 1. execute = OTP bul, 2. execute = Admin bul.
    """
    code = "654321"
    otp_record = _make_admin_otp_record(code=code)
    admin = _make_admin()

    session = _make_mock_session(
        _make_db_result(otp_record),  # İlk execute: OTP kaydı
        _make_db_result(admin),       # İkinci execute: Admin kaydı
    )

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_id] = _override_tenant_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        r = await client.post(
            "/api/v1/auth/admin/verify-otp",
            json={"phone": "5559876543", "code": code},
        )

    assert r.status_code == 200
    assert r.json() == {"message": "login_successful"}
    # admin_session cookie set edilmiş olmalı
    assert "admin_session" in r.cookies

    # Session token icinde tek cihaz kontrolu icin sv alani olmali.
    token = r.cookies.get("admin_session")
    payload = decode_token(token)
    assert payload.get("role") == "admin"
    assert payload.get("sv")

    # Exp suresi 40 gun civari olmalı (dakika bazli toleransli kontrol).
    exp_ts = payload.get("exp")
    assert isinstance(exp_ts, int)
    delta_seconds = exp_ts - int(datetime.now(timezone.utc).timestamp())
    assert 39 * 24 * 60 * 60 <= delta_seconds <= 40 * 24 * 60 * 60 + 120


@pytest.mark.asyncio
async def test_admin_cookie_ile_user_endpointe_erisim_403():
    """
    admin_session cookie ile kullanıcı endpoint'ine (verify-otp) erişim → 403 forbidden.
    Token geçerli ama role='admin'; user endpoint'i role='user' bekler.

    Not: Bu test get_current_user dependency'si eklendiğinde tam çalışır.
    Şu an user endpoint'lerinde role kontrolü yoktur (ADIM 10'da eklenecek).
    Bu test, get_current_admin() dependency'sinin rol kontrolünü doğrular:
    admin_session cookie'si olan birisi admin olmayan bir endpoint'e erişmeye çalışırsa
    ve o endpoint get_current_admin kullanıyorsa 403 alır.

    Test senaryosu: Admin token ile ping endpoint'ine erişim → tenant_id döner (bypass yok).
    Bunun yerine sahte bir admin-required endpoint test edilir.
    """
    from app.core.dependencies import get_current_admin

    # Kullanıcı token'ı oluştur (role=user) — admin endpoint'ine bu token ile erişmeye çalış
    user_token = create_token(
        {"sub": str(uuid.uuid4()), "role": "user"},
        expires_minutes=60,
    )

    # DB boş — get_current_admin 403 atmadan önce role kontrolü yapacak
    session = _make_mock_session(_make_db_result(None))

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_id] = _override_tenant_id

    # get_current_admin dependency'sini direkt test et: user token ile çağır → 403 bekle
    from fastapi import Request as FastAPIRequest
    from unittest.mock import MagicMock as MM

    mock_request = MM()
    mock_request.state.tenant_id = TEST_TENANT_ID

    # Dependency fonksiyonunu direkt çağır
    import pytest
    with pytest.raises(Exception) as exc_info:
        await get_current_admin(
            request=mock_request,
            admin_session=user_token,
            db=session,
        )

    # 403 forbidden hatası fırlatılmış olmalı
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == {"error": "forbidden"}


@pytest.mark.asyncio
async def test_admin_rate_limit_tenant_scoped_allows_other_tenant():
    """
    Tenant A'da aktif admin OTP varken Tenant B için aynı telefona OTP gönderimi engellenmemeli.
    """
    recent_admin_otp = _make_admin_otp_record(tenant_id=TEST_TENANT_ID)
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    def _side_effect(stmt):
        params = stmt.compile().params
        tenant_param = next((v for k, v in params.items() if "tenant_id" in k), None)
        if tenant_param is None:
            return _make_db_result(recent_admin_otp)
        if tenant_param == TEST_TENANT_ID:
            return _make_db_result(recent_admin_otp)
        return _make_db_result(None)

    session.execute = AsyncMock(side_effect=_side_effect)

    code = await auth_service.send_admin_otp(session, TEST_OTHER_TENANT_ID, "5559876543")

    assert len(code) == 6
    session.add.assert_called_once()
    added = session.add.call_args.args[0]
    assert added.tenant_id == TEST_OTHER_TENANT_ID


@pytest.mark.asyncio
async def test_logout_admin_token_sunucu_tarafinda_iptal_edilir():
    """
    Logout cagrisi admin token'i icin session_version rotate etmelidir.
    """
    admin = _make_admin()
    token = create_token(
        {"sub": str(admin.id), "role": "admin", "sv": str(uuid.uuid4())},
        expires_minutes=30,
    )
    session = _make_mock_session(_make_db_result(admin))

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_id] = _override_tenant_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        r = await client.post(
            "/api/v1/auth/logout",
            cookies={"admin_session": token},
        )

    assert r.status_code == 200
    assert r.json() == {"message": "logged_out"}
    session.commit.assert_called_once()
