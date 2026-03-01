# Berber Randevu Uygulaması (Iskelet)

CLAUDE.md'deki klasör yapısına uygun iskelet; business logic yok.

## Çalıştırma

1. **Docker Desktop'ı açın** (Windows) ve tamamen başlamasını bekleyin. "Sistem belirtilen dosyayı bulamıyor" / `dockerDesktopLinuxEngine` hatası, Docker daemon kapalı olduğunda oluşur.
2. Proje kökünde:
   ```bash
   docker compose up --build
   ```
2. **Backend:** http://localhost:8000/health → `{"status":"ok"}` (200)
3. **Frontend:** http://localhost:3000 → ana sayfada "ok" yazar

## Servis sırası (depends_on)

- `db` (PostgreSQL 15) → `backend` bağlanır
- `backend` (FastAPI) → `frontend` başlamadan önce hazır olur

## Ortam değişkenleri

`.env.example` dosyasını kopyalayıp `.env` yapın; gerçek değerleri doldurun. Docker Compose ile başlatırken backend için `DATABASE_URL` ve `SECRET_KEY` compose içinde tanımlı (geliştirme için yeterli).

## Backend test

```bash
cd backend
pip install -r requirements.txt
pytest
```

## Klasör yapısı

- `backend/app`: main, core, middleware, modules (auth, user, admin, tenant, schedule, booking, notification), models
- `backend/alembic`: migration iskeleti
- `frontend/app`: layout, ana sayfa (ok), (customer), admin
- `frontend/components`: index.ts
