"""
error_logging.py - Global error logging helper'lari.
"""

from __future__ import annotations

import json
from typing import Any

from starlette.requests import Request

from app.core.database import AsyncSessionLocal
from app.models.error_log import ErrorLog

_SENSITIVE_HEADER_KEYS = {"authorization", "cookie", "set-cookie", "x-api-key"}
_SENSITIVE_BODY_KEYS = {"password", "token", "code", "otp", "secret"}
_BODY_CHAR_LIMIT = 4096


def should_log_error_status(status_code: int) -> bool:
    """5xx + kritik 4xx (401/403/409) loglanir."""
    return status_code >= 500 or status_code in {401, 403, 409}


def _mask_headers(headers: dict[str, str]) -> dict[str, str]:
    masked: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() in _SENSITIVE_HEADER_KEYS:
            masked[key] = "***"
        else:
            masked[key] = value
    return masked


def _mask_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        masked: dict[str, Any] = {}
        for key, item in value.items():
            if any(token in key.lower() for token in _SENSITIVE_BODY_KEYS):
                masked[key] = "***"
            else:
                masked[key] = _mask_json_value(item)
        return masked
    if isinstance(value, list):
        return [_mask_json_value(item) for item in value]
    return value


def _truncate_text(value: str, limit: int = _BODY_CHAR_LIMIT) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}...[truncated]"


async def _build_masked_request_meta(request: Request) -> dict[str, Any]:
    body_preview: str | dict[str, Any] | None = None
    try:
        body_bytes = await request.body()
        if body_bytes:
            raw_text = body_bytes.decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw_text)
                if isinstance(parsed, (dict, list)):
                    body_preview = _mask_json_value(parsed)
                else:
                    body_preview = _truncate_text(str(parsed))
            except json.JSONDecodeError:
                body_preview = _truncate_text(raw_text)
    except Exception:
        body_preview = None

    return {
        "headers": _mask_headers(dict(request.headers.items())),
        "query_params": dict(request.query_params.items()),
        "body": body_preview,
        "client_host": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }


async def log_error_best_effort(
    request: Request,
    *,
    status_code: int,
    error_code: str | None,
    message: str,
    stack_trace: str | None = None,
) -> None:
    """
    Log yazimi best-effort calisir; hata olursa ana response akisini bozmaz.
    """
    if not should_log_error_status(status_code):
        return

    try:
        tenant_id = getattr(request.state, "tenant_id", None)
        request_id = getattr(request.state, "request_id", None)
        request_meta = await _build_masked_request_meta(request)
        async with AsyncSessionLocal() as db:
            db.add(
                ErrorLog(
                    tenant_id=tenant_id,
                    request_id=request_id,
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=status_code,
                    error_code=error_code,
                    message=_truncate_text(message),
                    stack_trace=_truncate_text(stack_trace) if stack_trace else None,
                    request_meta_json=request_meta,
                )
            )
            await db.commit()
    except Exception:
        return
