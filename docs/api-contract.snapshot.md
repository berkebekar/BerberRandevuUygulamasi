# API Contract Snapshot (2026-03-14)

Bu dosya davranis korunumu icin referans snapshot'tir.

## Endpoint Gruplari

- `/health`
- `/api/v1/ping`
- `/api/v1/auth/*`
- `/api/v1/users/*`
- `/api/v1/admin/*`
- `/api/v1/slots*`
- `/api/v1/bookings*`
- `/api/v1/notifications` (router var, endpoint yok)
- `/api/v1/superadmin/*`

## Error Code Snapshot

Ortak kullanilan error kodlari:

- `tenant_not_found`
- `tenant_inactive`
- `tenant_deleted`
- `tenant_required`
- `not_authenticated`
- `invalid_token`
- `session_revoked`
- `forbidden`
- `admin_not_found`
- `super_admin_not_found`
- `super_admin_inactive`
- `subdomain_already_exists`
- `subdomain_invalid`
- `admin_email_already_exists`
- `admin_phone_already_exists`
- `phone_invalid`
- `slot_taken`
- `slot_blocked`
- `slot_has_booking`
- `slot_already_blocked`
- `block_not_found`
- `invalid_slot`
- `slot_in_past`
- `too_far_in_future`
- `additional_booking_confirmation_required`
- `daily_booking_limit_exceeded`
- `booking_not_found`
- `booking_cancellation_window_passed`
- `booking_not_started`
- `override_not_found`
- `override_has_confirmed_bookings`
- `otp_not_found`
- `otp_invalid`
- `rate_limit_exceeded`
- `otp_required`
- `server_error`
