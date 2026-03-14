# Production Smoke Tests

## 1) Platform

1. `GET /health` => `200 {"status":"ok"}`
2. `GET /api/v1/ping` with valid tenant host => `tenant_id` present
3. `GET /api/v1/ping` with invalid tenant host => `tenant_not_found`

## 2) Auth

1. User OTP send/verify flow works
2. Admin OTP send/verify flow works
3. Password login endpoint returns `otp_required` by design
4. Logout invalidates old session cookie

## 3) Booking + Schedule

1. Slot list renders for today
2. Booking creation works for valid slot
3. Booking conflict returns `slot_taken`
4. Blocked slot returns `slot_blocked`
5. User cancellation window rule works

## 4) Admin

1. Overview endpoint returns bookings + slots + blocks
2. Block/unblock slot operations work
3. Manual booking flow works
4. no_show <-> confirmed transitions work

## 5) Super Admin

1. Login/logout works
2. Tenant list and detail endpoints work
3. Tenant status update syncs `status` + `is_active`
4. Impersonation start/stop works
