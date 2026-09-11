from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import Settings
from app.core.errors import AppError
from app.platform.admin_auth import (
    ADMIN_TOKEN_TYPE,
    authenticate_platform_admin,
    verify_platform_admin_session,
)


def admin_settings() -> Settings:
    return Settings(
        app_secret="a" * 48,
        platform_admin_email="Admin@Teta2.com",
        platform_admin_password="correct horse battery staple",
    )


def test_admin_login_accepts_case_insensitive_email_and_returns_session() -> None:
    settings = admin_settings()

    token = authenticate_platform_admin(
        "admin@teta2.com",
        "correct horse battery staple",
        settings=settings,
    )

    assert verify_platform_admin_session(token, settings=settings) == "admin@teta2.com"


def test_admin_login_rejects_wrong_password() -> None:
    with pytest.raises(AppError) as error:
        authenticate_platform_admin(
            "admin@teta2.com",
            "wrong password",
            settings=admin_settings(),
        )

    assert error.value.status_code == 401


def test_admin_login_requires_configured_credentials() -> None:
    with pytest.raises(AppError) as error:
        authenticate_platform_admin(
            "admin@teta2.com",
            "anything",
            settings=Settings(app_secret="a" * 48),
        )

    assert error.value.status_code == 503


def test_admin_session_rejects_expired_token() -> None:
    settings = admin_settings()
    expired = jwt.encode(
        {
            "sub": "admin@teta2.com",
            "type": ADMIN_TOKEN_TYPE,
            "iat": datetime.now(UTC) - timedelta(hours=10),
            "exp": datetime.now(UTC) - timedelta(hours=1),
        },
        settings.app_secret,
        algorithm="HS256",
    )

    with pytest.raises(AppError) as error:
        verify_platform_admin_session(expired, settings=settings)

    assert error.value.status_code == 401


def test_old_static_admin_token_is_not_a_valid_session() -> None:
    with pytest.raises(AppError) as error:
        verify_platform_admin_session("legacy-static-token", settings=admin_settings())

    assert error.value.status_code == 401
