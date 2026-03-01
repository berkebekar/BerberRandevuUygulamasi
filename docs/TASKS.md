# TASKS.md — Geliştirme İlerleme Takibi
# Single Barber Appointment System — MVP

> Kurallar:
> - Bir adım bitmeden sonrakine geçme
> - Her adımda Cursor'a sadece O adımı ver
> - Tamamlanan adımı [x] yap, tarihi yaz
> - Sorun çıkarsa adımın altına not düş

---

## ADIM 1 — Proje Yapısı & Local Ortam
**Hedef:** Her iki servis local'de ayağa kalksın.

- [x] Backend klasör yapısı oluşturuldu (`/backend/app/modules/...`) — 2026-02-23
- [x] Frontend klasör yapısı oluşturuldu (`/frontend/app/...`) — 2026-02-23
- [x] `docker-compose.yml` yazıldı (backend + frontend + postgres) — 2026-02-23
- [x] `requirements.txt` hazırlandı (fastapi, sqlalchemy, alembic, asyncpg, python-jose, passlib, httpx) — 2026-02-23
- [x] `package.json` hazırlandı (next.js 14) — 2026-02-23
- [x] `.env.example` dosyası oluşturuldu — 2026-02-23
- [x] `docker compose up` ile her iki servis ayağa kalktı — Backend (localhost:8000) ve frontend (localhost:3000) "ok" ile çalışıyor.

**Cursor'a verilecek prompt özeti:**
> "CLAUDE.md dosyasını oku. ADIM 1'i uygula. Sadece proje iskeletini ve docker-compose'u oluştur, business logic yazma."

---

## ADIM 2 — Veritabanı & Migration'lar
**Hedef:** Tüm tablolar migration ile oluşsun, up/down çalışsın.

- [x] Alembic kuruldu ve konfigüre edildi
- [x] `Tenant` modeli ve migration'ı yazıldı
- [x] `Admin` modeli ve migration'ı yazıldı
- [x] `User` modeli ve migration'ı yazıldı
- [x] `BarberProfile` modeli ve migration'ı yazıldı
- [x] `DayOverride` modeli ve migration'ı yazıldı
- [x] `SlotBlock` modeli ve migration'ı yazıldı
- [x] `Booking` modeli ve migration'ı yazıldı (partial unique index'ler dahil)
- [x] `OTPRecord` modeli ve migration'ı yazıldı
- [x] `NotificationLog` modeli ve migration'ı yazıldı
- [x] `alembic upgrade head` başarıyla çalıştı — Migration CAST düzeltmesi yapıldı; çalıştırıp tablolar oluştuysanız tamamlandı
- [x] `alembic downgrade base` başarıyla çalıştı — İsteğe bağlı; geri alıp tekrar upgrade ile doğrulayabilirsiniz

**Cursor'a verilecek prompt özeti:**
> "CLAUDE.md'deki tüm modelleri SQLAlchemy async modelleri olarak yaz. Her model için Alembic migration oluştur. Booking tablosundaki partial unique constraint'lere özellikle dikkat et."

---

## ADIM 3 — Tenant Middleware
**Hedef:** Geçersiz subdomain 404 dönsün, geçerli subdomain request'e tenant_id eklesin.

- [x] Subdomain parse fonksiyonu yazıldı — 2026-02-24
- [x] Tenant DB lookup yazıldı — 2026-02-24
- [x] Middleware FastAPI'ye eklendi — 2026-02-24
- [x] Test: `test-tenant.localhost` → 404 ✓ — 2026-02-24
- [x] Test: Geçerli subdomain → `request.state.tenant_id` set ✓ — 2026-02-24
- [x] Test: Tüm sorgularda tenant_id filtresi zorunlu ✓ — 2026-02-24

**Cursor'a verilecek prompt özeti:**
> "CLAUDE.md'deki Tenant Middleware bölümünü uygula. Host header'dan subdomain parse et. Test yaz: geçersiz subdomain 404 dönmeli."

---

## ADIM 4 — Auth: User OTP Akışı
**Hedef:** Müşteri telefon → OTP → cookie akışı çalışsın.

- [x] `POST /api/v1/auth/user/send-otp` yazıldı — 2026-02-24
- [x] OTP üretimi (6 haneli) ve bcrypt hash ile DB'ye kayıt — 2026-02-24
- [x] Twilio SMS gönderimi (async, non-blocking) — 2026-02-24 (dev: log, prod: ADIM 8)
- [x] Rate limit: aynı numaraya 60sn'de 1 kod — 2026-02-24
- [x] `POST /api/v1/auth/user/verify-otp` yazıldı — 2026-02-24
- [x] OTP doğrulama: hash kontrolü + süre + deneme sayısı — 2026-02-24
- [x] Başarılı doğrulamada HTTP-only cookie set edildi — 2026-02-24
- [x] User yoksa otomatik kayıt (ilk girişte isim/soyisim alınır) — 2026-02-24 (complete-registration endpoint)
- [x] Test: Doğru OTP → 200 + cookie ✓ — 2026-02-24
- [x] Test: Yanlış OTP 3 kez → kod iptal ✓ — 2026-02-24
- [x] Test: Süresi dolmuş OTP → 401 ✓ — 2026-02-24
- [x] Test: 60sn rate limit → 429 ✓ — 2026-02-24

**Cursor'a verilecek prompt özeti:**
> "CLAUDE.md'deki User Auth akışını uygula. OTP plain text saklanmaz. SMS async gönderilir. Rate limit zorunlu. HTTP-only cookie."

---

## ADIM 5 — Auth: Admin Akışı
**Hedef:** Admin kayıt ve her iki giriş yöntemi çalışsın.

- [x] `POST /api/v1/auth/admin/register` yazıldı (tek seferlik)
- [x] `POST /api/v1/auth/admin/login/otp` yazıldı
- [x] `POST /api/v1/auth/admin/login/password` yazıldı
- [x] `POST /api/v1/auth/logout` yazıldı
- [x] Admin ve User cookie'leri farklı scope'ta ✓
- [x] Test: İkinci admin kaydı denemesi → 409 ✓
- [x] Test: Yanlış şifre → 401 ✓
- [x] Test: Her iki login yöntemi çalışıyor ✓

**Cursor'a verilecek prompt özeti:**
> "CLAUDE.md'deki Admin Auth akışını uygula. Bir tenant'ta yalnızca 1 admin olabilir. İki giriş yöntemi: SMS OTP ve email+şifre."

---

## ADIM 6 — Schedule Modülü
**Hedef:** Slot hesaplama motoru ve admin takvim ayarları çalışsın.

- [x] `GET/PUT /api/v1/admin/schedule/settings` yazıldı
- [x] `POST /api/v1/admin/schedule/override` yazıldı
- [x] `POST/DELETE /api/v1/admin/slots/block` yazıldı
- [x] Slot hesaplama motoru yazıldı:
  - BarberProfile → varsayılan saatler
  - DayOverride → günlük override (varsa)
  - SlotBlock → kapalı slotlar
  - Booking → dolu slotlar
- [x] `GET /api/v1/slots?date=YYYY-MM-DD` yazıldı
- [x] `GET /api/v1/slots/week?start=YYYY-MM-DD` yazıldı
- [x] Test: Normal gün slotları doğru hesaplanıyor ✓
- [x] Test: DayOverride olan günde farklı saatler ✓
- [x] Test: Kapalı günde slot dönmüyor ✓
- [x] Test: Bloklu slot 'blocked' dönüyor ✓
- [x] Test: Geçmiş slotlar 'past' statüsünde dönüyor ✓

**Cursor'a verilecek prompt özeti:**
> "CLAUDE.md'deki Schedule modülünü uygula. Slotlar DB'de saklanmaz, her seferinde hesaplanır. Slot hesaplama sırası: BarberProfile → DayOverride → SlotBlock → Booking."

---

## ADIM 7 — Booking Modülü
**Hedef:** Atomik randevu oluşturma, race condition koruması, iptal.

- [x] `POST /api/v1/bookings` yazıldı — transaction + SELECT FOR UPDATE — 2026-02-25
- [x] `GET /api/v1/bookings/my` yazıldı — 2026-02-25
- [x] `GET /api/v1/bookings?date=YYYY-MM-DD` yazıldı (admin) — 2026-02-25
- [x] `DELETE /api/v1/bookings/{id}` yazıldı (admin iptal) — 2026-02-25
- [x] `POST /api/v1/admin/bookings` yazıldı (manuel randevu) — 2026-02-25
- [x] Admin iptal → NotificationLog'a kayıt (SMS MVP dışı) — 2026-02-25
- [x] Test: Aynı slot'a iki eşzamanlı istek → sadece 1 başarılı ✓ — 2026-02-25
- [x] Test: Aynı gün ikinci randevu → 409 ✓ — 2026-02-25
- [x] Test: 7 günden sonrası → 400 ✓ — 2026-02-25
- [x] Test: Geçmiş slot → 400 ✓ — 2026-02-25
- [x] Test: Bloklu slot → 409 ✓ — 2026-02-25

**Cursor'a verilecek prompt özeti:**
> "CLAUDE.md'deki Booking atomik işlem bölümünü uygula. SELECT FOR UPDATE zorunlu. Tüm business rule'ları API katmanında kontrol et, frontend'e güvenme."

---

## ADIM 8 — Notification Modülü
**Hedef:** SMS async gönderilsin, hata uygulamayı çökmez, log'a düşsün.

- [x] Twilio SMS servisi yazıldı — 2026-02-25
- [x] Background task olarak entegre edildi (FastAPI BackgroundTasks) — 2026-02-25
- [x] Başarılı gönderim → NotificationLog status='sent' — 2026-02-25
- [x] Hatalı gönderim → NotificationLog status='failed', uygulama çalışmaya devam eder — 2026-02-25
- [x] Sağlayıcı config'den değiştirilebilir (Netgsm'e geçiş kolay) — 2026-02-25
- [x] Test: Geçersiz numara → log'a düşer, 500 vermez ✓ — 2026-02-25

**Cursor'a verilecek prompt özeti:**
> "CLAUDE.md'deki Notification modülünü uygula. SMS async ve non-blocking. Hata olursa NotificationLog'a yaz, uygulamayı çökertme."

---

## ADIM 9 — Admin Panel API
**Hedef:** Admin dashboard endpoint'leri çalışsın.

- [x] `GET /api/v1/admin/dashboard?date=YYYY-MM-DD` yazıldı — 2026-02-25
  - Günlük tıraş sayısı (sadece sayı, para yok)
  - O günün randevu listesi
- [x] `POST /api/v1/admin/bookings` telefon tabanlı hale getirildi (find-or-create user) — 2026-02-25
- [x] Test: Dashboard doğru sayı döndürüyor ✓ — 2026-02-25
- [x] Test: Cancelled randevular sayıya dahil değil ✓ — 2026-02-25

**Cursor'a verilecek prompt özeti:**
> "Admin dashboard endpoint'lerini yaz. Sadece tıraş sayısı — para bilgisi yok. CLAUDE.md'deki admin endpoint listesine bak."

---

## ADIM 10 — Frontend: Müşteri Akışı
**Hedef:** Mobil'de müşteri randevu alabilsin.

- [x] `/auth` — telefon girişi + OTP ekranı — 2026-02-25
- [x] `/` — takvim + slot seçim ekranı — 2026-02-25
- [x] `/confirm` — randevu onay ekranı — 2026-02-25
- [x] Mobile-first CSS (önce 375px) — Tailwind v4, max-w-sm — 2026-02-25
- [x] API hata mesajları kullanıcıya gösteriliyor — lib/api.ts Türkçe mesajlar — 2026-02-25
- [x] Cookie ile oturum yönetimi çalışıyor — (customer)/layout.tsx auth guard — 2026-02-25
- [x] Test: iPhone SE boyutunda end-to-end randevu alındı ✓

**Cursor'a verilecek prompt özeti:**
> "Müşteri akışını Next.js 14 App Router ile yaz. Mobile-first, minimal UI. Akış: telefon → OTP → takvim → slot seç → onayla."

---

## ADIM 11 — Frontend: Admin Paneli
**Hedef:** Admin tüm işlemlerini panelden yapabilsin.

- [x] `/admin/login` — OTP ve şifre giriş ekranı
- [x] `/admin` — dashboard (günlük özet + takvim)
- [x] `/admin/settings` — çalışma saatleri + slot süresi ayarı
- [x] Slot kapatma / a�ma UI
- [x] Manuel randevu ekleme UI
- [x] Randevu iptal UI
- [ ] Test: Admin tüm işlemleri tamamlayabiliyor ✓

**Cursor'a verilecek prompt özeti:**
> "Admin panelini Next.js 14 ile yaz. İki ayrı login yöntemi. Dashboard, takvim yönetimi, ayarlar ekranları. CLAUDE.md'deki admin yetkilerine bak."

---

## ADIM 12 — Deployment
**Hedef:** Railway + Vercel'de MVP canlıya alınsın.

- [x] `Dockerfile` backend için yazıldı
- [ ] Railway'de PostgreSQL ve backend deploy edildi
- [ ] Vercel'de frontend deploy edildi
- [ ] Environment variable'lar production'da set edildi
- [ ] Twilio production'da test edildi (gerçek SMS)
- [ ] Cookie domain testi yapıldı:
  - [ ] Tenant A'nın cookie'si Tenant B'ye erişemiyor ✓
  - [ ] Wildcard cookie kullanılmıyor ✓
- [ ] Smoke test: Canlı ortamda baştan sona randevu alındı ✓

**Cursor'a verilecek prompt özeti:**
> "Railway ve Vercel için deployment konfigürasyonunu hazırla. Cookie domain güvenliğini test et. CLAUDE.md'deki environment variables listesini kullan."

---

## TAMAMLANAN ADIMLAR
*(Her adım bitince buraya taşı)*

Henüz tamamlanan adım yok.

---

## NOTLAR & KARARLAR
*(Geliştirme sırasında alınan kararları buraya yaz)*

- Stack kararı: FastAPI + PostgreSQL + Next.js
- SMS MVP: Twilio trial → production'da Netgsm
- Deployment MVP: Railway (free tier) + Vercel (free tier)
- Slot hesaplama: DB'de saklanmaz, runtime'da hesaplanır
- Cookie domain: subdomain'e spesifik, wildcard yasak

+++++
Tüm tenantları görebileceğim bir panel hazırla(berber ekle,sil,düzenle)

