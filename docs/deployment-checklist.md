# Deployment Checklist

## Pre-Deploy

- Migrations up-to-date (`alembic upgrade head`)
- Backend tests/lint/typecheck passed
- Frontend lint/typecheck/build passed
- `.private-docs/CLAUDE.md` updated for behavior changes

## Environment

Backend:
- `DATABASE_URL`
- `SECRET_KEY`
- `ENV=production`
- `APP_DOMAIN`
- `ALLOWED_SUBDOMAINS`
- `TWILIO_*` (if real SMS is enabled)
- `SUPER_ADMIN_SESSION_SECRET` (recommended)

Frontend:
- `BACKEND_URL`
- `NEXT_PUBLIC_API_URL` (optional)

## Runtime Checks

- `GET /health` returns 200
- Tenant host routing works (`tenant_not_found` for invalid subdomain)
- Auth cookie domain/secure/samesite are correct
- Admin dashboard loads and can block/unblock slots
- Super admin login and tenant list endpoints work
