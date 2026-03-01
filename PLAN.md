# Proje Kodunu Okuma Planı (Backend Önce, Devops Dahil)

**Özet**
- Önce proje yapısını ve çalışma mantığını (Docker/compose) anlıyoruz.
- Sonra backend akışını “giriş noktası → altyapı → veri modeli → iş akışları” sırasıyla okuyoruz.
- En son frontend’i “global yapı → API bağlantısı → sayfalar → bileşenler” şeklinde ele alıyoruz.
- Her dosyayı okurken standart bir not şablonu kullanıyoruz: “Bu dosya ne yapar? Girdiler/çıktılar? Yan etkiler? Kim çağırıyor?”

**Public API/Interface Değişiklikleri**
- Yok (sadece okuma planı).

---

## 1) Genel Çerçeve ve Çalıştırma Mantığı
Amaç: Proje nasıl ayakta duruyor, servisler nasıl konuşuyor, temel beklenti ne?

Okuma sırası:
1. `README.md`
   - Projenin amacı ve çalıştırma adımları.
   - Servis sırası ve health endpoint.
2. `docker-compose.yml`
   - `db`, `backend`, `frontend` servisleri; environment değişkenleri; portlar.
3. `backend/Dockerfile`, `frontend/Dockerfile`
   - Container içinde uygulama nasıl başlıyor?
4. `railway.toml` (varsa deploy/host bilgisi için).

Not şablonu:
- “Bu dosya hangi servisi etkiliyor?”
- “Hangi ortam değişkenleri kritik?”

---

## 2) Backend Giriş Noktası ve Altyapı (Core)
Amaç: Backend’e istek nasıl giriyor, ayarlar ve DB bağlantısı nasıl kuruluyor?

Okuma sırası:
1. `backend/app/main.py`
   - FastAPI app oluşturma, middleware, router kayıtları.
2. `backend/app/core/config.py`
   - Ayarların kaynağı: `.env`, varsayılanlar.
3. `backend/app/core/database.py`
   - DB session/engine nasıl kuruluyor.
4. `backend/app/core/security.py`
   - Kimlik doğrulama yardımcıları (JWT vb).
5. `backend/app/core/dependencies.py`
   - Endpoint’lerde kullanılan `Depends` fonksiyonları (auth, db, tenant).

Not şablonu:
- “Bu dosyadaki temel fonksiyonlar neler?”
- “Endpoint’lere hangi ortak kurallar uygulanıyor?”

---

## 3) Middleware
Amaç: Tüm isteklerde otomatik çalışan kurallar.

Okuma sırası:
1. `backend/app/middleware/tenant_middleware.py`
   - Tenant (subdomain) nasıl çözümleniyor?
   - Hangi path’ler muaf?

Not şablonu:
- “İstek başına hangi ekstra veri ekleniyor?”
- “Hangi hataları üretiyor olabilir?”

---

## 4) Veri Modeli (Models)
Amaç: Veritabanı tabloları ve ilişkiler.

Okuma sırası:
1. `backend/app/models/base.py`
2. `backend/app/models/enums.py`
3. `backend/app/models/tenant.py`
4. `backend/app/models/user.py`
5. `backend/app/models/admin.py`
6. `backend/app/models/barber_profile.py`
7. `backend/app/models/booking.py`
8. `backend/app/models/day_override.py`
9. `backend/app/models/slot_block.py`
10. `backend/app/models/notification_log.py`
11. `backend/app/models/otp_record.py`
12. `backend/app/models/__init__.py`

Not şablonu:
- “Bu modelin alanları neler?”
- “Başka modellerle ilişki var mı?”
- “Bu model hangi iş akışlarında kullanılır?”

---

## 5) Modüller (İş Akışları)
Amaç: Her iş alanını bağımsız ve tam görmek.

Her modül için okuma sırası (standart):
1. `schemas.py` (gelen/verilen veri)
2. `service.py` (iş mantığı)
3. `router.py` (endpoint’ler)
4. `__init__.py` (varsa)

Modüller:
1. `backend/app/modules/auth`
2. `backend/app/modules/user`
3. `backend/app/modules/admin`
4. `backend/app/modules/schedule`
5. `backend/app/modules/booking`
6. `backend/app/modules/notification`
7. `backend/app/modules/tenant` (varsa endpoint mantığı)

Not şablonu:
- “Bu modül hangi ihtiyacı çözüyor?”
- “Veri akışı: Router → Service → DB”
- “Başka modüllerle bağımlılığı var mı?”

---

## 6) Alembic (Migration)
Amaç: DB şeması değişimleri nasıl yönetiliyor?

Okuma sırası:
1. `backend/alembic.ini`
2. `backend/alembic/env.py`
3. `backend/alembic/versions/*`

Not şablonu:
- “Migration otomatik mi, manuel mi?”
- “Hangi tabloları yaratıyor/değiştiriyor?”

---

## 7) Backend Testler
Amaç: Sistemin doğrulanma mantığını görmek.

Okuma sırası:
1. `backend/tests/*`

Not şablonu:
- “Test senaryoları hangi akışları kapsıyor?”
- “Eksik kritik akış var mı?”

---

## 8) Frontend Altyapı ve Global Yapı
Amaç: Sayfa düzeni ve global stil/konfig.

Okuma sırası:
1. `frontend/next.config.js`
2. `frontend/tsconfig.json`
3. `frontend/app/layout.tsx`
4. `frontend/app/globals.css`

Not şablonu:
- “Genel layout nasıl?”
- “Global stiller ve fontlar nerede?”

---

## 9) Frontend Veri Erişimi
Amaç: API ile nasıl konuşuluyor?

Okuma sırası:
1. `frontend/lib/api.ts`

Not şablonu:
- “API çağrıları tek merkezde mi?”
- “Base URL ve hata yönetimi nasıl?”

---

## 10) Frontend Sayfalar (Route Groups)
Amaç: Ekran bazlı akışları görmek.

Okuma sırası:
1. `frontend/app/auth/*`
2. `frontend/app/(customer)/*`
3. `frontend/app/admin/*`

Not şablonu:
- “Bu sayfa hangi API’yi çağırıyor?”
- “Hangi component’leri kullanıyor?”

---

## 11) UI Bileşenleri
Amaç: Tekrarlayan UI parçalarını öğrenmek.

Okuma sırası:
1. `frontend/components/index.ts`
2. `frontend/components/*` (tek tek)

Not şablonu:
- “Bileşen hangi input props alıyor?”
- “Hangi sayfalar bunu kullanıyor?”

---

## 12) Akışları Baştan Sona İzleme (Pratik)
Amaç: Tam bir senaryoyu baştan sona takip etmek.

Örnek akışlar:
1. “Kullanıcı OTP ile giriş”
2. “Randevu oluşturma”
3. “Admin tarafında slot yönetimi”

İzleme adımı:
- Frontend sayfa → API çağrısı → Backend router → service → model/DB → response → UI.

---

## Test Senaryoları ve Kabul Kriterleri
- Her modül için “router → service → model” zincirini okuyup özetleyebilmek.
- Bir uçtan uca akışta hangi dosyaların devreye girdiğini söyleyebilmek.
- DB tablolarının uygulamadaki işlevini tarif edebilmek.

---

## Varsayımlar ve Varsayılanlar
- Backend önce okunacak.
- Devops/çalıştırma dosyaları kapsama dahil.
- Okuma sırasında dosya içi yorumlar temel rehber kabul edilecek.

