# Berber Randevu Uygulaması

Multi-tenant (subdomain bazlı) randevu sistemi.

- Backend: FastAPI + SQLAlchemy (async) + Alembic + PostgreSQL
- Frontend: Next.js 14 (App Router, TypeScript)
- Zaman dilimi: `Europe/Istanbul`
- Kimlik doğrulama: HTTP-only cookie (`user_session`, `admin_session`, `superadmin_session`)

## Hızlı Başlangıç

1. Docker Desktop'ı başlatın.
2. Proje kökünde çalıştırın:
   ```bash
   docker compose up --build
   ```
3. Sağlık kontrolü:
   - Backend: `http://localhost:8000/health`
   - Frontend: `http://localhost:3000`

## Temel API

- Sistem: `/health`, `/api/v1/ping`
- Auth: `/api/v1/auth/*`
- User: `/api/v1/users/*`
- Admin: `/api/v1/admin/*`
- Schedule/Booking: `/api/v1/slots*`, `/api/v1/bookings*`
- Super Admin: `/api/v1/superadmin/*`

Detaylı envanter ve iş kuralları için `.private-docs/CLAUDE.md` dosyasına bakın.

## Lokal Test ve Kontroller

### Backend
```bash
cd backend
pip install -r requirements.txt
ruff check app tests
black --check app tests
mypy app
pytest
```

### Frontend
```bash
cd frontend
npm ci
npm run lint
npm run typecheck
npm run build
```

## Ortam Değişkenleri

Örnek değerler için `.env.example` dosyasını kullanın.

Öne çıkan backend değişkenleri:
- `DATABASE_URL`
- `SECRET_KEY`
- `ENV` (`development` / `production`)
- `APP_DOMAIN`
- `ALLOWED_SUBDOMAINS`
- `SUPER_ADMIN_SESSION_SECRET` (opsiyonel)
- `SUPER_ADMIN_COOKIE_NAME` (opsiyonel)

Öne çıkan frontend değişkenleri:
- `NEXT_PUBLIC_API_URL` (opsiyonel)
- `BACKEND_URL` (rewrite hedefi)
