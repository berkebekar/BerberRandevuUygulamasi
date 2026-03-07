# PROD Migration 005 ve E2E Test Runbook

Bu dokuman, canli ortamda "ayni user ayni gun max 3 randevu" kuralina gecis icin
adim adim migration ve dogrulama rehberidir.

## 1) Database'de ne degisti?

Bu release'de **tek DB degisikligi** var:

- Kaldirilan index:
  - `ix_bookings_tenant_user_date_confirmed`
- Korunan index:
  - `ix_bookings_tenant_slot_confirmed`

Yani:
- Yeni tablo/kolon yok.
- Veri tasima/backfill yok.
- Sadece "ayni user + ayni gun tek randevu" zorunlulugu DB seviyesinden kaldirildi.

Migration dosyasi:
- `backend/alembic/versions/005_remove_daily_unique_booking_limit.py`

## 2) Canliya cikis sirasi (onerilen)

En guvenli sira:

1. **DB migration (Neon)**
2. **Backend deploy (Render)**
3. **Frontend deploy (Vercel)**

Not:
- Migration once calisirsa eski backend yine guvenli sekilde calisir (service zaten ayni gun ikinci randevuyu engeller).
- Backend once acilip migration gecikirse ikinci/ucuncu randevuda DB tarafinda cakisma alabilirsiniz.

## 3) Neon migration adimlari

### 3.1 Pre-check (index var mi?)

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'bookings'
  AND indexname IN (
    'ix_bookings_tenant_slot_confirmed',
    'ix_bookings_tenant_user_date_confirmed'
  )
ORDER BY indexname;
```

Beklenen (migration oncesi):
- Her iki index de listelenmeli.

### 3.2 Migration calistir

Render shell veya migration job icinden:

```bash
alembic upgrade head
```

### 3.3 Post-check (dogrulama)

Ayni sorguyu tekrar calistirin:

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'bookings'
  AND indexname IN (
    'ix_bookings_tenant_slot_confirmed',
    'ix_bookings_tenant_user_date_confirmed'
  )
ORDER BY indexname;
```

Beklenen (migration sonrasi):
- `ix_bookings_tenant_slot_confirmed` var
- `ix_bookings_tenant_user_date_confirmed` yok

## 4) Rollback plani

Sorun olursa:

1. Backend'i bir onceki stabil release'e alin.
2. Alembic downgrade calistirin:

```bash
alembic downgrade 004_weekly_closed_days
```

Bu downgrade, kaldirilan index'i tekrar olusturur.

## 5) Uctan uca manuel test (customer akisi)

Test verisi:
- Ayni user ile ayni gun 4 farkli uygun slot secin.

### Senaryo A - 1. randevu

1. User login olsun.
2. 1. slotu secip onaylasin.

Beklenen:
- Randevu olusur.
- Hata yok.

### Senaryo B - 2. randevu (modal zorunlu)

1. Ayni user ayni gun 2. slotu secsin.
2. Once modalda "Vazgec" deyin.
3. Tekrar deneyip bu kez "Evet, Devam Et" deyin.

Beklenen:
- Modal metninde sayi gorunsun (ornek `1/3`).
- Vazgec'te randevu olusmasin.
- Onay verince randevu olussun.

### Senaryo C - 3. randevu (modal zorunlu)

1. Ayni user 3. slotu denesin.
2. Modal acilsin, sayi `2/3` gorunsun.
3. Onay verince randevu olussun.

### Senaryo D - 4. randevu (limit)

1. Ayni user 4. slotu denesin.

Beklenen:
- Randevu olusmaz.
- UI mesaji: `Ayni gun icin 3'ten fazla randevu alamazsiniz.`

### Senaryo E - API dogrulama

`GET /api/v1/bookings/my` yanitinda ayni gun icin:
- `status=confirmed` toplam 3 kayit olmali.

## 6) Hata kodu beklentileri

Booking create endpoint (`POST /api/v1/bookings`) icin:

- 2. veya 3. randevu onaysiz denemede:
  - `409 additional_booking_confirmation_required`
  - payload icinde `current_count`, `max_allowed`

- 4. randevu denemesinde:
  - `409 daily_booking_limit_exceeded`
  - payload icinde `current_count`, `max_allowed`
