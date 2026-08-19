from __future__ import annotations

import json
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.radar.models import RadarConnection

CONNECTION_STATUSES = {"CONNECTING", "ACTIVE", "EXPIRED", "ERROR", "DISCONNECTED"}
PLATFORM_PROVIDERS = {
    "FACEBOOK": "META_GRAPH",
    "INSTAGRAM": "META_GRAPH",
    "TELEGRAM": "TELEGRAM_MTPROTO",
}


def _fernet() -> Fernet:
    key = get_settings().radar_session_encryption_key
    if not key:
        if get_settings().app_env in {"development", "test"}:
            # Deliberately derive nothing from APP_SECRET; production must provide an isolated key.
            raise AppError(
                "RADAR_SESSION_KEY_MISSING",
                "Radar session encryption is not configured.",
                503,
            )
        raise RuntimeError("RADAR_SESSION_ENCRYPTION_KEY is required")
    return Fernet(key.encode())


def encrypt_credentials(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    return _fernet().encrypt(raw).decode()


def decrypt_credentials(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        raw = _fernet().decrypt(value.encode())
        parsed = json.loads(raw.decode())
    except (InvalidToken, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise AppError("RADAR_SESSION_INVALID", "Radar authorization is unavailable.", 503) from exc
    if not isinstance(parsed, dict):
        raise AppError("RADAR_SESSION_INVALID", "Radar authorization is unavailable.", 503)
    return parsed


async def create_connection(db: AsyncSession, *, platform: str) -> RadarConnection:
    normalized = platform.strip().upper()
    provider = PLATFORM_PROVIDERS.get(normalized)
    if not provider:
        raise AppError("RADAR_CONNECTION_PLATFORM_INVALID", "Unsupported Radar connection.", 422)
    connection = RadarConnection(
        platform=normalized,
        provider=provider,
        status="CONNECTING",
        auth_nonce=secrets.token_urlsafe(32),
        connection_metadata={"read_only": True},
    )
    db.add(connection)
    await db.flush()
    return connection


async def activate_connection(
    db: AsyncSession,
    connection: RadarConnection,
    *,
    credentials: dict[str, Any],
    account_external_id: str | None = None,
    account_display: str | None = None,
    scopes: list[str] | None = None,
    expires_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> RadarConnection:
    connection.encrypted_credentials = encrypt_credentials(credentials)
    connection.account_external_id = account_external_id
    connection.account_display = account_display
    connection.scopes = list(scopes or [])
    connection.expires_at = expires_at
    connection.status = "ACTIVE"
    connection.last_health_at = datetime.now(UTC)
    connection.last_error_code = None
    connection.last_error = None
    connection.auth_nonce = None
    merged = dict(connection.connection_metadata or {})
    merged.update(metadata or {})
    merged["read_only"] = True
    connection.connection_metadata = merged
    await db.flush()
    return connection


async def disconnect_connection(db: AsyncSession, connection: RadarConnection) -> None:
    connection.encrypted_credentials = None
    connection.status = "DISCONNECTED"
    connection.auth_nonce = None
    connection.last_health_at = datetime.now(UTC)
    await db.flush()


async def active_connection(db: AsyncSession, platform: str) -> RadarConnection | None:
    now = datetime.now(UTC)
    connection = await db.scalar(
        select(RadarConnection)
        .where(
            RadarConnection.platform == platform.strip().upper(),
            RadarConnection.status == "ACTIVE",
        )
        .order_by(RadarConnection.updated_at.desc())
        .limit(1)
    )
    if connection and connection.expires_at and connection.expires_at <= now:
        connection.status = "EXPIRED"
        await db.flush()
        return None
    return connection


def connection_public(connection: RadarConnection) -> dict[str, Any]:
    return {
        "id": str(connection.id),
        "platform": connection.platform,
        "provider": connection.provider,
        "status": connection.status,
        "account_external_id": connection.account_external_id,
        "account_display": connection.account_display,
        "scopes": list(connection.scopes or []),
        "expires_at": connection.expires_at,
        "last_health_at": connection.last_health_at,
        "last_error_code": connection.last_error_code,
        "last_error": connection.last_error,
        "metadata": dict(connection.connection_metadata or {}),
        "created_at": connection.created_at,
        "updated_at": connection.updated_at,
    }


async def connection_by_id(db: AsyncSession, connection_id: uuid.UUID) -> RadarConnection:
    connection = await db.get(RadarConnection, connection_id)
    if not connection:
        raise AppError("RADAR_CONNECTION_NOT_FOUND", "Radar connection was not found.", 404)
    return connection
