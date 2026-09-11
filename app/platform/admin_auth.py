import hmac
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import Settings, get_settings
from app.core.errors import AppError

ADMIN_SESSION_HOURS = 8
ADMIN_TOKEN_TYPE = "platform_admin"


def _settings(value: Settings | None = None) -> Settings:
    return value or get_settings()


def _configured(settings: Settings) -> bool:
    return bool(settings.platform_admin_email and settings.platform_admin_password)


def authenticate_platform_admin(
    email: str,
    password: str,
    *,
    settings: Settings | None = None,
) -> str:
    config = _settings(settings)
    if not _configured(config):
        raise AppError(
            "PLATFORM_ADMIN_NOT_CONFIGURED",
            "Platform administration is unavailable.",
            503,
        )

    expected_email = (config.platform_admin_email or "").strip().casefold()
    supplied_email = email.strip().casefold()
    expected_password = config.platform_admin_password or ""
    credentials_match = hmac.compare_digest(supplied_email, expected_email) and hmac.compare_digest(
        password,
        expected_password,
    )
    if not credentials_match:
        raise AppError(
            "PLATFORM_ADMIN_AUTH_REQUIRED",
            "The administrator email or password is incorrect.",
            401,
        )

    now = datetime.now(UTC)
    payload = {
        "sub": expected_email,
        "type": ADMIN_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(hours=ADMIN_SESSION_HOURS),
    }
    return jwt.encode(payload, config.app_secret, algorithm="HS256")


def verify_platform_admin_session(
    token: str,
    *,
    settings: Settings | None = None,
) -> str:
    config = _settings(settings)
    if not _configured(config):
        raise AppError(
            "PLATFORM_ADMIN_NOT_CONFIGURED",
            "Platform administration is unavailable.",
            503,
        )
    if not token:
        raise AppError(
            "PLATFORM_ADMIN_AUTH_REQUIRED",
            "Platform administrator authentication is required.",
            401,
        )
    try:
        payload = jwt.decode(token, config.app_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise AppError(
            "PLATFORM_ADMIN_AUTH_REQUIRED",
            "Platform administrator session is invalid or expired.",
            401,
        ) from exc

    expected_email = (config.platform_admin_email or "").strip().casefold()
    token_email = str(payload.get("sub") or "").strip().casefold()
    if payload.get("type") != ADMIN_TOKEN_TYPE or not hmac.compare_digest(
        token_email,
        expected_email,
    ):
        raise AppError(
            "PLATFORM_ADMIN_AUTH_REQUIRED",
            "Platform administrator session is invalid or expired.",
            401,
        )
    return expected_email
