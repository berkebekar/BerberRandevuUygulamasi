"""Firebase Phone Auth token verification helpers."""

import base64
import json
import logging

from fastapi import HTTPException

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _load_service_account(raw_value: str) -> dict:
    stripped = raw_value.strip()
    if not stripped:
        return {}
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        try:
            decoded = base64.b64decode(stripped).decode("utf-8")
            return json.loads(decoded)
        except Exception as exc:
            raise HTTPException(500, {"error": "firebase_service_account_invalid"}) from exc


def _get_firebase_app():
    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError as exc:
        raise HTTPException(500, {"error": "firebase_admin_not_installed"}) from exc

    settings = get_settings()
    project_id = settings.firebase_project_id.strip()
    if not project_id:
        raise HTTPException(503, {"error": "firebase_not_configured"})

    app_name = "phone-auth"
    try:
        return firebase_admin.get_app(app_name)
    except ValueError:
        options = {"projectId": project_id}
        service_account = _load_service_account(settings.firebase_service_account_json)
        if service_account:
            return firebase_admin.initialize_app(
                credentials.Certificate(service_account),
                options=options,
                name=app_name,
            )
        return firebase_admin.initialize_app(options=options, name=app_name)


def verify_firebase_phone_id_token(id_token: str) -> str:
    """Return the verified phone number from a Firebase Auth ID token."""
    try:
        from firebase_admin import auth
    except ImportError as exc:
        raise HTTPException(500, {"error": "firebase_admin_not_installed"}) from exc

    token = (id_token or "").strip()
    if not token:
        raise HTTPException(401, {"error": "firebase_token_invalid"})

    try:
        decoded = auth.verify_id_token(token, app=_get_firebase_app())
    except HTTPException:
        raise
    except Exception as exc:
        logger.info("Firebase ID token dogrulanamadi | error=%s", exc)
        raise HTTPException(401, {"error": "firebase_token_invalid"}) from exc

    provider = decoded.get("firebase", {}).get("sign_in_provider")
    phone_number = decoded.get("phone_number")
    if provider != "phone" or not phone_number:
        raise HTTPException(401, {"error": "firebase_phone_required"})
    return str(phone_number)
