import hashlib
import hmac
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import verify_password
from app.core.config import get_settings
from app.core.errors import AppError
from app.database.control_models import (
    SalesManager,
    SalesManagerActivity,
    SalesManagerSession,
)
from app.database.sessions import control_session

SALES_SESSION_HOURS = 10
SALES_SESSION_KIND = "platform_sales_manager"


def _signing_key() -> str:
    settings = get_settings()
    return hmac.new(
        settings.app_secret.encode(),
        b"platform-sales-manager-session",
        hashlib.sha256,
    ).hexdigest()


def _request_identity(request: Request) -> tuple[str | None, str | None]:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    raw_ip = forwarded or (request.client.host if request.client else "")
    if raw_ip:
        secret = get_settings().app_secret.encode()
        ip_hash = hashlib.sha256(secret + raw_ip.encode()).hexdigest()[:40]
    else:
        ip_hash = None
    return ip_hash, request.headers.get("user-agent", "")[:500] or None


def make_sales_session_token(manager: SalesManager, session_id: uuid.UUID) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(manager.id),
        "sid": str(session_id),
        "ver": manager.token_version,
        "type": SALES_SESSION_KIND,
        "iat": now,
        "exp": now + timedelta(hours=SALES_SESSION_HOURS),
    }
    return jwt.encode(payload, _signing_key(), algorithm="HS256")


def decode_sales_session_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, _signing_key(), algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise AppError(
            "SALES_MANAGER_AUTH_REQUIRED",
            "Sales manager session is invalid or expired.",
            401,
        ) from exc
    if payload.get("type") != SALES_SESSION_KIND:
        raise AppError(
            "SALES_MANAGER_AUTH_REQUIRED",
            "Sales manager session is invalid or expired.",
            401,
        )
    return payload


@dataclass
class SalesManagerContext:
    manager: SalesManager
    session_row: SalesManagerSession
    db: AsyncSession
    ip_hash: str | None
    user_agent: str | None


async def authenticate_sales_manager(
    db: AsyncSession,
    request: Request,
    *,
    identifier: str,
    password: str,
) -> tuple[SalesManager, SalesManagerSession, str]:
    from sqlalchemy import or_, select

    value = identifier.strip().casefold()
    manager = await db.scalar(
        select(SalesManager).where(
            or_(
                SalesManager.email == value,
                SalesManager.username == value,
            )
        )
    )
    if not manager or not manager.is_active or not verify_password(password, manager.password_hash):
        raise AppError(
            "SALES_MANAGER_LOGIN_INVALID",
            "The email, username or password is incorrect.",
            401,
        )
    now = datetime.now(UTC)
    ip_hash, user_agent = _request_identity(request)
    session_row = SalesManagerSession(
        manager_id=manager.id,
        started_at=now,
        last_seen_at=now,
        ip_hash=ip_hash,
        user_agent=user_agent,
    )
    db.add(session_row)
    await db.flush()
    manager.last_login_at = now
    manager.updated_at = now
    db.add(
        SalesManagerActivity(
            manager_id=manager.id,
            session_id=session_row.id,
            action="LOGIN",
            entity_type="SESSION",
            entity_id=str(session_row.id),
            details={},
            ip_hash=ip_hash,
            user_agent=user_agent,
        )
    )
    token = make_sales_session_token(manager, session_row.id)
    return manager, session_row, token


async def require_sales_manager(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    db: Annotated[AsyncSession, Depends(control_session)] = None,
) -> SalesManagerContext:
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not supplied:
        raise AppError(
            "SALES_MANAGER_AUTH_REQUIRED",
            "Sales manager authentication is required.",
            401,
        )
    payload = decode_sales_session_token(supplied)
    try:
        manager_id = uuid.UUID(str(payload["sub"]))
        session_id = uuid.UUID(str(payload["sid"]))
    except (KeyError, ValueError) as exc:
        raise AppError(
            "SALES_MANAGER_AUTH_REQUIRED",
            "Sales manager session is invalid or expired.",
            401,
        ) from exc
    manager = await db.get(SalesManager, manager_id)
    session_row = await db.get(SalesManagerSession, session_id)
    if (
        not manager
        or not manager.is_active
        or manager.token_version != payload.get("ver")
        or not session_row
        or session_row.manager_id != manager.id
        or session_row.ended_at is not None
    ):
        raise AppError(
            "SALES_MANAGER_AUTH_REQUIRED",
            "Sales manager session is invalid or expired.",
            401,
        )
    now = datetime.now(UTC)
    session_row.last_seen_at = now
    ip_hash, user_agent = _request_identity(request)
    return SalesManagerContext(manager, session_row, db, ip_hash, user_agent)


async def record_sales_activity(
    ctx: SalesManagerContext,
    *,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    details: dict | None = None,
) -> None:
    ctx.db.add(
        SalesManagerActivity(
            manager_id=ctx.manager.id,
            session_id=ctx.session_row.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
            ip_hash=ctx.ip_hash,
            user_agent=ctx.user_agent,
        )
    )
