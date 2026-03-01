# CURSOR_PROMPTS.md — Cursor'a Atılacak Hazır Promptlar

> Her adım için iki prompt var:
> 1. **PLAN prompt** → Plan Mode'da kullan, Cursor planı anlatsın
> 2. **BUILD prompt** → Agent Mode'da kullan, Cursor kodu yazsın
>
> Önce PLAN, onaylarsan BUILD. Hiçbir adımı atlatma.

---

## ADIM 1 — Proje Yapısı & Local Ortam

### PLAN (Plan Mode'da gir)

```
docs/CLAUDE.md dosyasını oku ve içeriğini anladığını özetle.

Sonra şunu planla:

Bu projenin iskelet yapısını kuracağız. Hiç business logic yok, sadece klasör yapısı ve local çalışma ortamı.

Benden şunları istiyorum:
1. CLAUDE.md'deki klasör yapısına uygun backend ve frontend iskeletini oluştur
2. docker-compose.yml (backend + frontend + postgres servisleri)
3. Backend için requirements.txt (fastapi, sqlalchemy[asyncio], alembic, asyncpg, passlib[bcrypt], python-jose, httpx, twilio)
4. Frontend için Next.js 14 App Router kurulumu
5. .env.example dosyası (CLAUDE.md'deki environment variables listesinden)

Kod yazmadan önce yapacaklarını adım adım listele ve onaymı bekle.
```

### BUILD (Plan'ı onayladıktan sonra Agent Mode'a geç)

```
Onayladım. Şimdi uygula.

Kurallar:
- Her klasörde __init__.py veya index dosyası olsun (boş bile olsa)
- docker-compose'da servisler birbirini beklesin (depends_on)
- .env.example doldurulmuş olsun, gerçek değerler değil açıklama yazısın
- FastAPI uygulaması ayağa kalktığında GET /health → 200 dönsün
- Next.js ayağa kalktığında ana sayfa "ok" yazsın (placeholder)

Bitince terminalde docker compose up çalıştır ve her iki servisin ayakta olduğunu doğrula.
```

---

## ADIM 2 — Veritabanı & Migration'lar

### PLAN (Plan Mode)

```
docs/CLAUDE.md dosyasını oku.

Şimdi tüm veritabanı modellerini ve migration'larını kuracağız.

CLAUDE.md'deki "VERİTABANI MODELLERİ" bölümündeki her entity için:
- SQLAlchemy async model
- Alembic migration

Başlamadan önce şunları planla ve listele:
1. Hangi sırayla migration'lar oluşturulacak (FK bağımlılıkları nedeniyle sıra önemli)
2. Booking tablosundaki partial unique constraint'leri nasıl yazacaksın
3. Timezone için nasıl bir strateji izleyeceksin (TIMESTAMPTZ vs naive datetime)

Planı listele, onay bekle.
```

### BUILD (Agent Mode)

```
Onayladım. Uygula.

Dikkat edilecekler:
- Tüm UUID alanları için server-side default kullan (gen_random_uuid())
- Tüm zaman alanları TIMESTAMPTZ olsun — naive datetime YASAK
- Booking tablosunda şu iki partial unique index zorunlu:
  * UNIQUE(tenant_id, slot_time) WHERE status = 'confirmed'
  * UNIQUE(tenant_id, user_id, DATE(slot_time AT TIME ZONE 'Europe/Istanbul')) WHERE status = 'confirmed'
- Her model __repr__ metodu içersin (debug için)
- Migration'lar hem upgrade hem downgrade içersin

Bitince alembic upgrade head çalıştır ve tüm tabloların oluştuğunu doğrula.
```

---

## ADIM 3 — Tenant Middleware

### PLAN (Plan Mode)

```
docs/CLAUDE.md dosyasını oku.

Tenant middleware'i kuracağız. CLAUDE.md'deki "TENANT MIDDLEWARE" bölümüne bak.

Planla:
1. Host header'dan subdomain nasıl parse edilecek (local dev için localhost alt domainlerini de desteklemeli)
2. Tenant DB lookup nasıl yapılacak
3. Geçersiz/bulunamayan tenant için response ne olacak
4. request.state'e nasıl eklenecek
5. Test stratejisi

Planı yaz, onay bekle.
```

### BUILD (Agent Mode)

```
Onayladım. Uygula.

Gereksinimler:
- Middleware tüm /api/v1/ route'larına uygulanmalı (/health hariç)
- Local dev'de hem "berber.localhost" hem "localhost" (default tenant) çalışmalı
- Tenant bulunamazsa 404 + {"error": "tenant_not_found"} dönsün
- Tenant is_active=false ise 403 dönsün
- Her başarılı resolve için request.state.tenant_id ve request.state.tenant set edilmeli

Test yaz:
- Geçersiz subdomain → 404
- is_active=false tenant → 403
- Geçerli tenant → request.state.tenant_id set edilmiş
```

---

## ADIM 4 — Auth: User OTP

### PLAN (Plan Mode)

```
docs/CLAUDE.md dosyasını oku.

User (müşteri) auth akışını kuracağız.

Akış:
1. Kullanıcı telefon numarası girer
2. SMS ile 6 haneli OTP gönderilir
3. OTP girilir, doğrulanır
4. HTTP-only cookie set edilir
5. Kullanıcı yoksa isim/soyisim alınır ve kayıt olur

Planla:
1. OTP üretimi ve bcrypt hash stratejisi
2. Rate limiting (60sn/numara) nasıl uygulanacak
3. SMS gönderimi async nasıl çalışacak
4. Cookie yapısı (expiry, secure, httponly, samesite)
5. "Kullanıcı yok → kayıt" akışı nasıl ayrılacak

Planı yaz, onay bekle.
```

### BUILD (Agent Mode)

```
Onayladım. Uygula.

Kesin kurallar:
- OTP: 6 haneli, bcrypt ile hash'lenerek OTPRecord tablosuna yazılır
- OTP süresi: 5 dakika (expires_at = now + 5min)
- Max deneme: 3, sonra is_used=true yapılır ve 401 döner
- Rate limit: aynı telefon için 60sn geçmeden ikinci OTP isteği → 429
- SMS gönderimi: FastAPI BackgroundTask olarak, uygulama beklemesin
- SMS başarısız olsa bile OTP DB'ye yazılır, hata loglanır
- Cookie: httponly=True, secure=True (prod), samesite="lax", max_age=7 gün
- Yeni kullanıcı için /auth/user/verify-otp yanıtı {"status": "new_user"} dönsün
  (frontend isim/soyisim formu göstersin)
- Mevcut kullanıcı için {"status": "returning_user"} dönsün

Test yaz:
- Doğru OTP → 200 + cookie
- Yanlış OTP → 401, attempt_count artar
- 3 yanlış deneme → kod iptal, 401
- Süresi dolmuş OTP → 401
- 60sn içinde ikinci send-otp → 429
```

---

## ADIM 5 — Auth: Admin

### PLAN (Plan Mode)

```
docs/CLAUDE.md dosyasını oku.

Admin auth akışını kuracağız. Üç endpoint:
1. Kayıt (tek seferlik)
2. Giriş — SMS OTP
3. Giriş — email + şifre

Planla:
1. "Tek seferlik kayıt" kontrolü nasıl uygulanacak
2. Admin cookie'si ile user cookie'si nasıl ayrılacak
3. Her iki login yönteminin ortak ve farklı noktaları
4. Admin middleware — admin gerektiren route'lara nasıl uygulanacak

Planı yaz, onay bekle.
```

### BUILD (Agent Mode)

```
Onayladım. Uygula.

Kurallar:
- Kayıt: tenant başına 1 admin zorunlu (UNIQUE constraint + API kontrolü)
  İkinci kayıt denemesi → 409 + {"error": "admin_already_exists"}
- Şifre: bcrypt hash, min 8 karakter validation
- Admin OTP akışı User OTP ile aynı altyapıyı kullanır, role="admin" farkıyla
- Cookie name: admin_session (user_session'dan ayrı)
- Admin route'ları için get_current_admin() dependency yazılmalı
- Logout: her iki cookie'yi de temizlesin

Test yaz:
- İkinci admin kaydı → 409
- Yanlış şifre → 401
- Her iki login yöntemi çalışıyor
- Admin cookie ile user endpoint'e erişim → 403
```

---

## ADIM 6 — Schedule Modülü

### PLAN (Plan Mode)

```
docs/CLAUDE.md dosyasını oku. "Slot Hesaplama" bölümüne özellikle dikkat et.

Schedule modülünü kuracağız. Bu modülün kalbi slot hesaplama motorudur.

Planla:
1. Slot hesaplama fonksiyonunun imzası ve mantığı
   (girdi: tenant_id + date → çıktı: slot listesi, her slot için status)
2. BarberProfile → DayOverride → SlotBlock → Booking öncelik sırası
3. Slot status tipleri: available / booked / blocked / past
4. Haftalık görünüm için performans (7 günü tek sorguda çek)
5. Admin'in slotu kapatması ile zaten randevusu olan slot çakışması nasıl ele alınacak

Planı yaz, onay bekle.
```

### BUILD (Agent Mode)

```
Onayladım. Uygula.

Kesin kurallar:
- Slotlar DB'de SAKLANMAZ, her seferinde hesaplanır
- Geçmiş slotlar response'a dahil edilmez (slot_time < now())
- Slot status enum: available | booked | blocked | past
- Slotu kapat ama o slotta randevu varsa:
  → 409 + {"error": "slot_has_booking", "booking_id": "..."}
  → Admin önce randevuyu iptal etmeli
- DayOverride is_closed=true ise o gün hiç slot dönmez
- Admin kendi manuel randevusunu eklerken slot müsait olmalı (aynı kontroller)

Test yaz:
- Normal gün: doğru slot sayısı (örn 09:00-19:00, 30dk → 20 slot)
- DayOverride ile farklı saatler
- Kapalı günde boş liste
- Bloklu slot "blocked" dönüyor
- Dolu slot "booked" dönüyor
- Geçmiş slot "past" dönüyor
```

---

## ADIM 7 — Booking Modülü

### PLAN (Plan Mode)

```
docs/CLAUDE.md dosyasını oku. "KRİTİK BUSINESS RULES" ve "Randevu Oluşturma — ATOMIK" bölümlerine bak.

Booking modülünü kuracağız. Bu sistemin en kritik modülüdür.

Planla:
1. Transaction + SELECT FOR UPDATE akışını adım adım yaz
2. Hangi hata hangi HTTP status kodu döner
3. Admin iptal akışı (cancelled_by = 'admin', NotificationLog kaydı)
4. "Aynı gün 1 randevu" constraint'i DB'de mi, API'de mi, her ikisinde mi kontrol edilecek

Planı yaz, onay bekle.
```

### BUILD (Agent Mode)

```
Onayladım. Uygula.

Kesin kurallar:
- Randevu oluşturma TAMAMEN transaction içinde olmalı
- SELECT FOR UPDATE ile slot ve kullanıcının o günkü randevusu kilitlenmeli
- Aynı slot çakışması → 409 + {"error": "slot_taken"}
- Aynı gün ikinci randevu → 409 + {"error": "already_booked_today"}
- 7 günden sonrası → 400 + {"error": "too_far_in_future"}
- Geçmiş slot → 400 + {"error": "slot_in_past"}
- Admin iptal: status='cancelled', cancelled_by='admin'
  → NotificationLog'a kayıt yaz (message_type='booking_cancelled', status='pending')
  → SMS gönderimi MVP dışı, sadece log

Race condition testi:
- Aynı slot'a asyncio ile 10 eşzamanlı istek gönder
- Sadece 1 tanesi 200, diğerleri 409 olmalı
- Bu test geçmeden ADIM 7 tamamlanmış sayılmaz
```

---

## ADIM 8 — Notification Modülü

### PLAN (Plan Mode)

```
docs/CLAUDE.md dosyasını oku. "BİLDİRİMLER" bölümüne bak.

Notification modülünü kuracağız. MVP'de sadece OTP SMS'i var ama altyapı genişleyebilir olmalı.

Planla:
1. Provider abstraction — Twilio bugün, Netgsm yarın, geçiş nasıl olacak
2. Background task vs queue farkı — hangisini kullanacaksın, neden
3. Retry mantığı olacak mı MVP'de
4. NotificationLog yazım stratejisi (önce log, sonra SMS mi? Aynı anda mı?)

Planı yaz, onay bekle.
```

### BUILD (Agent Mode)

```
Onayladım. Uygula.

Kurallar:
- Provider interface/abstract class yaz: send_sms(phone, message) → bool
- TwilioProvider bu interface'i implement eder
- Gelecekte NetgsmProvider aynı interface'i implement edecek (şimdi yazma)
- SMS gönderimi her zaman BackgroundTask olarak çalışır
- Akış:
  1. NotificationLog kaydı oluştur (status='pending')
  2. Background'da SMS gönder
  3. Başarılı → status='sent', provider_response güncelle
  4. Hatalı → status='failed', hata logla, UYGULAMA ÇÖKMEZ
- SMS başarısız olsa bile OTP akışı devam eder (SMS opsiyonel, kritik değil)

Test yaz:
- Mock provider ile SMS gönder → log status='sent'
- Mock provider hata fırlatsın → log status='failed', exception yutulmadı ama propagate de edilmedi
```

---

## ADIM 9 — Admin Panel API

### PLAN (Plan Mode)

```
docs/CLAUDE.md dosyasını oku.

Admin dashboard endpoint'lerini kuracağız. Bunlar CLAUDE.md'deki admin endpoint listesinin geri kalanı.

Planla:
1. Dashboard'daki "günlük tıraş sayısı" nasıl hesaplanacak (hangi status'lar sayılacak)
2. Haftalık/aylık görünüm için query optimizasyonu
3. Manuel randevu ekleme — user OTP gerektirmeden admin nasıl randevu ekleyecek (müşteri telefonu ile)

Planı yaz, onay bekle.
```

### BUILD (Agent Mode)

```
Onayladım. Uygula.

Dashboard kuralları:
- Günlük tıraş sayısı = o gün status='confirmed' olan booking sayısı
- Para bilgisi HİÇBİR YERDE yok
- Admin manuel randevu eklerken telefon numarası girer:
  → User varsa mevcut user'a randevu açılır
  → User yoksa isim/soyisim de alınır, yeni user oluşturulur
  → Aynı booking constraint'leri geçerli (aynı gün 1 randevu vs.)

Test yaz:
- Dashboard doğru sayı döndürüyor
- Cancelled randevular sayıya dahil değil
```

---

## ADIM 10 — Frontend: Müşteri Akışı

### PLAN (Plan Mode)

```
docs/CLAUDE.md dosyasını oku. Frontend bölümüne bak.

Müşteri akışını Next.js 14 App Router ile kuracağız.

Planla:
1. Route yapısı (/auth, /, /confirm)
2. Cookie yönetimi — Next.js'de HTTP-only cookie nasıl okunacak
3. API çağrıları için fetch wrapper stratejisi (tenant subdomain header'ı nasıl eklenecek)
4. Mobil-first için hangi CSS yaklaşımı (Tailwind öneriyorum)
5. Loading ve error state'leri

Planı yaz, onay bekle.
```

### BUILD (Agent Mode)

```
Onayladım. Uygula.

Tasarım kuralları:
- Mobile-first: önce 375px tasarla, sonra büyüt
- Minimal UI: gereksiz animasyon yok, sade renkler
- Tailwind CSS kullan
- Her API hatasını kullanıcıya anlaşılır Türkçe mesajla göster
- Slot takvimi: günlük görünüm, slotlar grid halinde
- Boş slot: tıklanabilir, yeşil
- Dolu slot: tıklanamaz, gri
- Bloklu slot: tıklanamaz, farklı renk

Akış:
/ → cookie yoksa /auth'a yönlendir
/auth → telefon gir → OTP gir → yeni kullanıcıysa isim/soyisim → / 'e yönlendir
/ → takvim + slot seç → /confirm
/confirm → randevu özeti → "Onayla" butonu → başarı ekranı

Test: iPhone SE (375px) boyutunda tüm akış çalışmalı
```

---

## ADIM 11 — Frontend: Admin Paneli

### PLAN (Plan Mode)

```
docs/CLAUDE.md dosyasını oku.

Admin panelini kuracağız.

Planla:
1. Admin route koruması — cookie yoksa /admin/login'e yönlendir
2. Dashboard'da takvim: günlük/haftalık/aylık switch nasıl çalışacak
3. Slot yönetimi UI: slotu kapatmak/açmak
4. Manuel randevu ekleme formu

Planı yaz, onay bekle.
```

### BUILD (Agent Mode)

```
Onayladım. Uygula.

Admin panel kuralları:
- /admin/login → iki sekme: "SMS ile Giriş" ve "Şifre ile Giriş"
- Dashboard:
  - Bugünün tarihi varsayılan
  - Üstte: "Bugün X randevu" sayacı
  - Altında: randevu listesi (saat + müşteri adı)
  - Her randevunun yanında "İptal Et" butonu
- Ayarlar sayfası (/admin/settings):
  - Çalışma saati başlangıç/bitiş
  - Slot süresi (30/40/60 dk radio button)
  - Kaydet butonu
- Slot yönetimi: takvimde slota tıkla → "Kapat" seçeneği
- Manuel randevu: "+ Randevu Ekle" butonu → telefon gir → tarih/saat seç

Mobile-first, Tailwind.
```

---

## ADIM 12 — Deployment

### PLAN (Plan Mode)

```
docs/CLAUDE.md dosyasını oku. Deployment bölümüne bak.

Railway + Vercel'e deploy edeceğiz.

Planla:
1. Backend için Dockerfile
2. Railway konfigürasyonu (railway.toml veya nixpacks)
3. Vercel konfigürasyonu (next.config.js, API URL env)
4. Cookie domain güvenlik stratejisi — subdomain'e spesifik nasıl set edilecek
5. Production environment variable checklist

Planı yaz, onay bekle.
```

### BUILD (Agent Mode)

```
Onayladım. Uygula.

Deployment kuralları:
- Backend Dockerfile: multi-stage build, production image küçük olsun
- Alembic migration'ları deploy sırasında otomatik çalışsın (start komutu: alembic upgrade head && uvicorn ...)
- Cookie domain: production'da spesifik subdomain (berke.app.com), wildcard (.app.com) YASAK
- CORS: sadece kendi domain'lerine izin ver, * YASAK
- ENV=production iken:
  - Debug kapalı
  - Cookie secure=True
  - Detaylı hata mesajları kullanıcıya gitmesin

Cookie domain testi (deployment sonrası zorunlu):
1. Tenant A (berke.app.com) ile login ol, cookie al
2. Tenant B (ahmet.app.com)'dan o cookie'ye erişmeye çalış → erişilememeli
3. Bu test geçmeden deployment tamamlanmış sayılmaz

Bitince smoke test: canlı ortamda baştan sona randevu al.
```

---

## GENEL CURSOR KULLANIM REHBERİ

### Her adımda şablonu kullan

```
[Adım X başlangıcında her zaman şunu ekle:]

"docs/CLAUDE.md dosyasını oku. Şu an ADIM X üzerindeyiz.
TASKS.md'de bu adımın checkbox'larını kontrol et.
[Sonra ilgili PLAN veya BUILD prompt'unu yapıştır]"
```

### Cursor çok fazla şey yapmaya başlarsa dur

```
"Dur. Sadece şu an üzerinde çalıştığımız adımı yap.
Sonraki adımlara geçme."
```

### Cursor yanlış bir karar verirse

```
"Bu karar CLAUDE.md ile çelişiyor çünkü [sebep].
CLAUDE.md'ye uy ve tekrar planla."
```

### Adım bitince

```
"ADIM X tamamlandı. TASKS.md'deki checkbox'ları güncelle.
Bir sonraki adıma geçmeden bana bildir."
```
