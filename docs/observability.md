# Minimal Observability Standard

## Request-Level

- Every request has `x-request-id` (incoming or generated)
- Response echoes `x-request-id`
- Structured log includes:
  - `request_id`
  - `method`
  - `path`
  - `status`
  - `duration_ms`

## Error-Level

- Unhandled exceptions log stack trace server-side
- Client receives generic `server_error` payload

## Operational Rule

- Production incidents must be traceable by `x-request-id`
- Smoke tests should validate `x-request-id` propagation
