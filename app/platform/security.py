import hmac
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.errors import AppError

_admin_bearer = HTTPBearer(auto_error=False)


def platform_admin_configured() -> bool:
    settings = get_settings()
    return bool(settings.platform_admin_email and settings.platform_admin_password)


def authenticate_platform_admin(email: str, password: str) -> str:
    settings = get_settings()
    configured_email = (settings.platform_admin_email or "").strip().lower()
    configured_password = settings.platform_admin_password or ""
    if not configured_email or not configured_password:
        raise AppError(
            "PLATFORM_ADMIN_NOT_CONFIGURED",
            "Platform administration is not configured on this deployment.",
            503,
        )
    if not hmac.compare_digest(email.strip().lower(), configured_email) or not hmac.compare_digest(
        password, configured_password
    ):
        raise AppError("INVALID_ADMIN_CREDENTIALS", "Invalid platform admin credentials.", 401)
    now = datetime.now(UTC)
    payload = {
        "sub": configured_email,
        "scope": "platform_admin",
        "type": "platform_admin",
        "iat": now,
        "exp": now + timedelta(minutes=settings.platform_admin_token_minutes),
    }
    return jwt.encode(payload, settings.access_token_secret, algorithm="HS256")


def decode_platform_admin_token(token: str) -> str:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.access_token_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise AppError("INVALID_ADMIN_SESSION", "Platform admin session is invalid or expired.", 401) from exc
    if payload.get("type") != "platform_admin" or payload.get("scope") != "platform_admin":
        raise AppError("INVALID_ADMIN_SESSION", "Platform admin session is invalid.", 401)
    email = str(payload.get("sub") or "").lower()
    configured = (settings.platform_admin_email or "").strip().lower()
    if not configured or not hmac.compare_digest(email, configured):
        raise AppError("INVALID_ADMIN_SESSION", "Platform admin session is no longer valid.", 401)
    return email


async def require_platform_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_admin_bearer)],
) -> str:
    if not credentials:
        raise AppError("ADMIN_AUTH_REQUIRED", "Platform admin authentication is required.", 401)
    return decode_platform_admin_token(credentials.credentials)
