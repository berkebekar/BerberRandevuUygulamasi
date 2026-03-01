# CLAUDE.md — Single Barber Appointment System
# Cursor'un Ana Referans Dosyası

> Bu dosyayı her prompt'ta oku. Buradaki kararlar değiştirilemez.
> Eğer bir şey bu dosyayla çelişiyorsa, DUR ve kullanıcıya sor.

---

## NASIL DAVRANACAKSIN — TEMEL KURALLAR

Bu bir **production uygulamasıdır.** Demo değil, tutorial değil, oyuncak proje değil.

### Öncelik sırası (her zaman bu sırayla düşün)
1. Doğruluk — yanlış çalışan kod yoktur
2. Veri tutarlılığı — sessiz veri bozulması kabul edilemez
3. Race condition güvenliği — özellikle booking işlemlerinde
4. Sadelik — akıllı görünen ama riskli çözüm yerine sıkıcı ama kanıtlanmış çözüm
5. Sıfır sessiz hata — her hata loglanır veya kullanıcıya döner

### Kod yazmadan önce
- Belirsiz bir şey varsa → **DUR, sor**
- Bir karar ileride sistemi bozabilecekse → **uyar, sonra uygula**
- Bu dosyayla çelişen bir istek gelirse → **reddet, açıkla**

### Her zaman yap
- Her modülü kendi klasöründe tut (router / service / schema ayrı dosyalar)
- Her DB sorgusuna tenant_id filtresi ekle — istisnasız
- Business rule'ları API (service) katmanında kontrol et, frontend'e güvenme
- Hata mesajları anlamlı olsun — "something went wrong" kabul edilmez
- Her kritik işlemi logla

### Asla yapma
- Frontend validation'a güvenme
- Plain text şifre veya OTP saklama
- Tenant filtresi olmadan DB sorgusu çalıştırma
- Booking işlemini transaction dışında yapma
- MVP dışı özellik kodlama — sadece yorum olarak belirt

### Kod üretim sırası (her adımda bu sırayı izle)
1. Veri modelini/schema'yı yaz
2. Service katmanını yaz (business logic)
3. Router'ı yaz (HTTP katmanı)
4. Test yaz
5. Çalıştır, geç

---

## YORUM SATIRI KURALLARI — KESİNLİKLE UYULACAK

Bu proje aynı zamanda bir öğrenme sürecidir.
Yazdığın her kodun yanına Türkçe yorum satırı ekle.

### Ne zaman yorum yazacaksın
- Her dosyanın en üstüne: bu dosya ne işe yarar, sistemdeki rolü nedir
- Her class/fonksiyon tanımının üstüne: ne yapar, neden var, ne döner
- Her önemli satırın yanına veya üstüne: bu satır ne yapıyor, neden bu şekilde yazıldı
- Her if/else bloğuna: bu koşul neden kontrol ediliyor
- Her DB sorgusuna: ne arıyor, neden bu şekilde yazıldı
- Her hata fırlatılan yere: bu hata neden fırlatılıyor, ne anlama geliyor
- Her config veya sabit değere: bu değer ne anlama geliyor, neden bu seçildi

### Yorum tonu
- Sade ve anlaşılır Türkçe
- Sadece "ne yapıyor" değil, "neden böyle yapıyor" da açıkla
- Teknik terim kullanmak zorundaysan yanına parantez içinde açıkla
  Örnek: # transaction başlatıyoruz (transaction: ya hepsi olur ya hiçbiri)

### Doğru yorum örneği — böyle yaz

```python
# =============================================
# booking/service.py
# Randevu oluşturma ve yönetim işlemleri.
# Bu dosya sistemin en kritik parçasıdır —
# çift randevu oluşmasını buradaki kurallar engeller.
# =============================================

async def create_booking(db, tenant_id, user_id, slot_time):
    # Bu fonksiyon bir randevu oluşturur.
    # 'async' kullanıyoruz çünkü veritabanı işlemi bitene kadar
    # sunucunun başka isteklere de bakabilmesi gerekiyor.

    async with db.begin() as transaction:
        # transaction başlatıyoruz.
        # transaction = ya hepsi başarılı olur, ya hiçbiri olmaz.
        # Örnek: randevu yazılırken elektrik giderse yarım kayıt oluşmaz.

        existing = await db.execute(
            select(Booking)
            .where(Booking.slot_time == slot_time)
            .with_for_update()  # bu satır o kaydı kilitler —
                                # aynı anda başka biri de aynı slotu almaya
                                # çalışırsa sırada bekletilir, çift randevu olmaz
        )

        if existing.scalar():
            raise HTTPException(409)
            # 409 = "Conflict" (çakışma) HTTP kodu.
            # Slot dolu olduğu için işlemi durduruyoruz.
```

### Yanlış yorum örneği — böyle yazma

```python
async def create_booking(db, tenant_id, user_id, slot_time):
    # randevu oluştur
    async with db.begin():
        existing = await db.execute(...)
        if existing.scalar():
            raise HTTPException(409)  # hata
```

Bu kurala her dosyada, her fonksiyonda istisnasız uy.

---

---

## PROJE NE?

Tek bir berber için mobil uyumlu web tabanlı randevu sistemi.
Gelecekte SaaS'a dönüşebilecek şekilde tasarlanmış.

---

## TEK SATIR KURAL

Bir özellik MVP olarak bu dosyada açıkça belirtilmemişse → KODLAMA **YOK**. Sadece yorum satırı olarak dokümante et.

---

## ASLA İHLAL EDİLMEYECEK KISITLAR

```
- Berber sayısı      : TAM OLARAK 1
- Aynı anda müşteri  : TAM OLARAK 1
- Slot başına randevu: TAM OLARAK 1
- Günlük müşteri     : 1 müşteri = max 1 randevu/gün
- Ödeme              : YOK
- Çoklu berber       : YOK
- Otomatik slot kaydırma : YOK
- Timezone           : SADECE Europe/Istanbul (UTC+3, sabit)
- Native mobil app   : YOK
```

---

## TECH STACK

```
Backend  : FastAPI (Python 3.12+)
Database : PostgreSQL 15+
ORM      : SQLAlchemy (async) + Alembic (migrations)
Frontend : Next.js 14 (App Router)
SMS      : Twilio (MVP) — config'den değiştirilebilir
Deploy   : Railway (backend + DB) + Vercel (frontend)
```

---

## PROJE KLASÖR YAPISI

```
/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/          # config, security, db bağlantısı
│   │   ├── middleware/    # tenant resolver
│   │   ├── modules/
│   │   │   ├── auth/
│   │   │   ├── user/
│   │   │   ├── admin/
│   │   │   ├── tenant/
│   │   │   ├── schedule/
│   │   │   ├── booking/
│   │   │   └── notification/
│   │   └── models/        # SQLAlchemy modelleri
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── (customer)/    # Müşteri akışı
│   │   └── admin/         # Admin paneli
│   └── components/
├── docs/
│   ├── CLAUDE.md          # Bu dosya
│   ├── TASKS.md           # İlerleme takibi
│   └── ARCHITECTURE.md    # Mimari kararlar
└── docker-compose.yml     # Local geliştirme
```

---

## KULLANICI ROLLERİ

### Admin (Berber)
- Sistemde TAM OLARAK 1 admin vardır
- **Kayıt:** email + telefon + şifre (tek seferlik)
- **Giriş Yol 1:** telefon → SMS OTP
- **Giriş Yol 2:** email + şifre
- Session: HTTP-only cookie

### User (Müşteri)
- **Giriş/Kayıt:** telefon → SMS OTP (tek akış)
- Session: HTTP-only cookie
- Cookie geçerliyse OTP istenmez

---

## VERİTABANI MODELLERİ

### Tenant
```
id            UUID PK
subdomain     VARCHAR UNIQUE NOT NULL
name          VARCHAR NOT NULL
is_active     BOOLEAN DEFAULT true
created_at    TIMESTAMPTZ NOT NULL
```

### Admin
```
id            UUID PK
tenant_id     UUID FK→Tenant  [UNIQUE — tenant başına 1 admin]
email         VARCHAR UNIQUE NOT NULL
phone         VARCHAR UNIQUE NOT NULL
password_hash VARCHAR NOT NULL
created_at    TIMESTAMPTZ NOT NULL
```

### User
```
id            UUID PK
tenant_id     UUID FK→Tenant
phone         VARCHAR NOT NULL
first_name    VARCHAR NOT NULL
last_name     VARCHAR NOT NULL
created_at    TIMESTAMPTZ NOT NULL
[UNIQUE: tenant_id + phone]
```

### BarberProfile
```
id                    UUID PK
tenant_id             UUID FK→Tenant  [UNIQUE]
slot_duration_minutes INTEGER NOT NULL  -- 30 | 40 | 60
work_start_time       TIME NOT NULL     -- örn: 09:00
work_end_time         TIME NOT NULL     -- örn: 19:00
updated_at            TIMESTAMPTZ NOT NULL
```

### DayOverride
```
id               UUID PK
tenant_id        UUID FK→Tenant
date             DATE NOT NULL
is_closed        BOOLEAN DEFAULT false
work_start_time  TIME NULLABLE
work_end_time    TIME NULLABLE
[UNIQUE: tenant_id + date]
```

### SlotBlock
```
id          UUID PK
tenant_id   UUID FK→Tenant
blocked_at  TIMESTAMPTZ NOT NULL  -- TR timezone
reason      VARCHAR NULLABLE
created_at  TIMESTAMPTZ NOT NULL
[UNIQUE: tenant_id + blocked_at]
```

### Booking
```
id           UUID PK
tenant_id    UUID FK→Tenant
user_id      UUID FK→User
slot_time    TIMESTAMPTZ NOT NULL  -- TR timezone
status       ENUM: confirmed | cancelled
cancelled_by ENUM NULLABLE: admin | user
created_at   TIMESTAMPTZ NOT NULL
updated_at   TIMESTAMPTZ NOT NULL

[UNIQUE: tenant_id + slot_time]        WHERE status='confirmed'
[UNIQUE: tenant_id + user_id + date]   WHERE status='confirmed'
```

### OTPRecord
```
id            UUID PK
phone         VARCHAR NOT NULL
code_hash     VARCHAR NOT NULL  -- bcrypt, plain text SAKLANMAZ
role          ENUM: user | admin
expires_at    TIMESTAMPTZ NOT NULL  -- +5 dakika
is_used       BOOLEAN DEFAULT false
attempt_count INTEGER DEFAULT 0
created_at    TIMESTAMPTZ NOT NULL
```

### NotificationLog
```
id                UUID PK
tenant_id         UUID FK→Tenant
recipient_phone   VARCHAR NOT NULL
message_type      ENUM: otp | booking_created | booking_cancelled
status            ENUM: sent | failed | pending
provider_response JSONB NULLABLE
created_at        TIMESTAMPTZ NOT NULL
```

---

## API ENDPOINT LİSTESİ

Tüm endpoint'ler: `GET|POST|PUT|DELETE /api/v1/...`
Tenant her request'te subdomain'den resolve edilir.

### Auth
```
POST /auth/user/send-otp          # Public
POST /auth/user/verify-otp        # Public
POST /auth/admin/register         # Public (tek seferlik)
POST /auth/admin/login/otp        # Public
POST /auth/admin/login/password   # Public
POST /auth/logout                 # Cookie
```

### Slots
```
GET /slots?date=YYYY-MM-DD        # User | Admin
GET /slots/week?start=YYYY-MM-DD  # User | Admin
```

### Booking
```
POST   /bookings                  # User — atomik işlem
GET    /bookings/my               # User
GET    /bookings?date=YYYY-MM-DD  # Admin
DELETE /bookings/{id}             # Admin — iptal
```

### Admin Panel
```
GET  /admin/dashboard?date=YYYY-MM-DD   # Admin
GET  /admin/schedule/settings           # Admin
PUT  /admin/schedule/settings           # Admin
POST /admin/schedule/override           # Admin
POST /admin/slots/block                 # Admin
DEL  /admin/slots/block/{id}            # Admin
POST /admin/bookings                    # Admin — manuel randevu
```

---

## KRİTİK BUSINESS RULES

### Randevu Oluşturma — ATOMIK
```sql
BEGIN
  SELECT ... FROM bookings
    WHERE tenant_id=? AND slot_time=? AND status='confirmed'
    FOR UPDATE              -- kilitle
  → Varsa: ROLLBACK → 409

  SELECT ... FROM slot_blocks
    WHERE tenant_id=? AND blocked_at=?
    FOR UPDATE
  → Varsa: ROLLBACK → 409

  INSERT INTO bookings (...)
COMMIT
```

### OTP Kuralları
- Süre: 5 dakika
- Max deneme: 3 (sonra is_used=true, geçersiz)
- Rate limit: aynı numaraya 60sn'de 1 kod
- Hash: bcrypt — plain text asla saklanmaz

### Slot Hesaplama
- Slotlar DB'de saklanmaz, her seferinde hesaplanır
- Kaynak: BarberProfile → DayOverride (varsa) → SlotBlock → Booking
- Geçmiş slotlar listelenmez

---

## TENANT MIDDLEWARE

Her request şu sırayı izler:
```
1. Host header → subdomain parse
2. DB'de tenant ara
3. Bulunamazsa → 404
4. Bulunursa → request.state.tenant_id set et
5. Devam et
```

**Hiçbir DB sorgusu tenant_id filtresi olmadan çalışmaz.**

---

## BİLDİRİMLER (MVP)

MVP'de SMS sadece OTP içindir.

SMS gönderimi her zaman:
- async olmalı (background task)
- non-blocking olmalı
- hata toleranslı olmalı (uygulama çökmemeli)
- NotificationLog'a yazılmalı (başarı veya hata)

---

## GÜVENLİK KURALLARI

```
✓ HTTP-only cookie — JS erişimi yok
✓ OTP: 3 hatalı denemede iptal
✓ OTP rate limit: 60sn/numara
✓ Cookie domain: spesifik subdomain (wildcard .app.com YASAK)
✓ Tüm validation API'de — frontend'e güvenilmez
✓ bcrypt: şifre ve OTP hash için
✓ Parameterized queries — SQL injection yok
✓ Tenant izolasyonu: her sorguda tenant_id zorunlu
```

---

## MVP DIŞI — KODLAMA (Sadece Dokümante Et)

```
- Randevu oluşturuldu SMS'i (müşteriye)
- Kullanıcı randevu iptali
- İptal edildi SMS'i (admin'e)
- Ciro takibi (para)
- İstatistik dashboard
- Tema özelleştirme
- SaaS ödeme modeli
- Gecikme bildirimi
- Otomatik slot kaydırma
- CRM müşteri profilleri
```

---

## ENVIRONMENT VARIABLES

```env
DATABASE_URL=
SECRET_KEY=          # min 32 char random string
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
APP_DOMAIN=          # örn: app.com
ALLOWED_SUBDOMAINS=  # virgülle ayrılmış liste
ENV=                 # development | production
```

---

*Son güncelleme: v1.0 — MVP*
