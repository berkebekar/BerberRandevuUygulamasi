# Admin Endpoint Checklist (Postman / curl)

Bu liste hizli smoke-check icindir. Tam API referansi degildir.

## Ortak Notlar

1. Auth cookie tabanlidir: `admin_session`.
2. Tenant icin dogru host/subdomain gereklidir.
3. Postman'da cookie jar acik olmali.
4. `curl` kullaniyorsan cookie dosyasi kullan:
   - `-c admin.cookies` (kaydet)
   - `-b admin.cookies` (gonder)

## Endpoint Kontrolleri

### 1) POST /api/v1/auth/admin/send-otp
- Minimal request:
```bash
curl -X POST "$BASE/api/v1/auth/admin/send-otp" ^
  -H "Content-Type: application/json" ^
  -d "{\"phone\":\"905551112233\"}"
```
- Beklenen: `200`
- Kritik hata: `429` (rate limit)

### 2) POST /api/v1/auth/admin/verify-otp
- Minimal request:
```bash
curl -X POST "$BASE/api/v1/auth/admin/verify-otp" ^
  -H "Content-Type: application/json" ^
  -c admin.cookies ^
  -d "{\"phone\":\"905551112233\",\"code\":\"123456\"}"
```
- Beklenen: `200`, `admin_session` cookie set
- Kritik hata: `401` (gecersiz/expired OTP)

### 3) POST /api/v1/auth/admin/login/password
- Minimal request:
```bash
curl -X POST "$BASE/api/v1/auth/admin/login/password" ^
  -H "Content-Type: application/json" ^
  -c admin.cookies ^
  -d "{\"email\":\"admin@example.com\",\"password\":\"secret\"}"
```
- Beklenen: `200`, `admin_session` cookie set
- Kritik hata: `401` (yanlis email/sifre)

### 4) GET /api/v1/admin/dashboard?date=YYYY-MM-DD
- Minimal request:
```bash
curl "$BASE/api/v1/admin/dashboard?date=2026-02-26" ^
  -b admin.cookies
```
- Beklenen: `200` (`confirmed_count`, `bookings`)
- Kritik hata: `401` (cookie yok/gecersiz)

### 5) GET /api/v1/admin/schedule/settings
- Minimal request:
```bash
curl "$BASE/api/v1/admin/schedule/settings" ^
  -b admin.cookies
```
- Beklenen: `200` (object veya `null`)
- Kritik hata: `401`

### 6) PUT /api/v1/admin/schedule/settings
- Minimal request:
```bash
curl -X PUT "$BASE/api/v1/admin/schedule/settings" ^
  -H "Content-Type: application/json" ^
  -b admin.cookies ^
  -d "{\"slot_duration_minutes\":30,\"work_start_time\":\"09:00\",\"work_end_time\":\"19:00\"}"
```
- Beklenen: `200`
- Kritik hata: `422` (gecersiz saat/sure)

### 7) GET /api/v1/slots?date=YYYY-MM-DD
- Minimal request:
```bash
curl "$BASE/api/v1/slots?date=2026-02-26" ^
  -b admin.cookies
```
- Beklenen: `200` (`slots` listesi)
- Kritik hata: `400/404` (tenant/host problemi)

### 8) GET /api/v1/admin/slots/blocks?date=YYYY-MM-DD
- Minimal request:
```bash
curl "$BASE/api/v1/admin/slots/blocks?date=2026-02-26" ^
  -b admin.cookies
```
- Beklenen: `200` (`blocks` listesi, `id` + `blocked_at`)
- Kritik hata: `401`

### 9) POST /api/v1/admin/slots/block
- Minimal request:
```bash
curl -X POST "$BASE/api/v1/admin/slots/block" ^
  -H "Content-Type: application/json" ^
  -b admin.cookies ^
  -d "{\"slot_datetime\":\"2026-02-26T10:00:00+03:00\"}"
```
- Beklenen: `201` (`id`, `blocked_at`)
- Kritik hata: `409` (`slot_has_booking`, `slot_already_blocked`)

### 10) DELETE /api/v1/admin/slots/block/{block_id}
- Minimal request:
```bash
curl -X DELETE "$BASE/api/v1/admin/slots/block/<BLOCK_ID>" ^
  -b admin.cookies
```
- Beklenen: `200`
- Kritik hata: `404` (`block_not_found`)

### 11) POST /api/v1/admin/bookings
- Minimal request:
```bash
curl -X POST "$BASE/api/v1/admin/bookings" ^
  -H "Content-Type: application/json" ^
  -b admin.cookies ^
  -d "{\"slot_time\":\"2026-02-26T11:00:00+03:00\",\"phone\":\"905551112233\"}"
```
- Beklenen: `201`
- Kritik hata: `422` (`missing_user_info`), `409` (slot conflict)

### 12) DELETE /api/v1/bookings/{booking_id}
- Minimal request:
```bash
curl -X DELETE "$BASE/api/v1/bookings/<BOOKING_ID>" ^
  -b admin.cookies
```
- Beklenen: `200`
- Kritik hata: `404` (kayit yok/zaten iptal)
