import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AuthContext, current_context
from app.auth.schemas import LoginRequest, LogoutRequest, MeResponse, RefreshRequest, TokenPair
from app.auth.security import (
    decode_token,
    make_access_token,
    make_refresh_token,
    token_digest,
    verify_password,
)
from app.clinic_resolution.service import resolver
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.rate_limit import sensitive_limit
from app.database.models import AuditLog, RefreshSession, User
from app.database.sessions import control_session

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def pair(user, clinic_id):
    return make_access_token(user.id, clinic_id, user.token_version), make_refresh_token(
        user.id, clinic_id, user.token_version
    )


@router.post(
    "/login", response_model=TokenPair, dependencies=[Depends(sensitive_limit("login", 10, 60))]
)
async def login(body: LoginRequest, control: Annotated[AsyncSession, Depends(control_session)]):
    clinic = await resolver.by_slug(control, body.clinic_slug)
    factory = resolver.session_factory(clinic)
    async with factory() as db, db.begin():
        user = await db.scalar(
            select(User).where(
                or_(User.email == body.identifier.lower(), User.username == body.identifier)
            )
        )
        if not user or not user.is_active or not verify_password(body.password, user.password_hash):
            db.add(
                AuditLog(
                    actor_user_id=user.id if user else None,
                    actor_role=user.role.value if user else None,
                    action="LOGIN_FAILURE",
                    entity_type="User",
                    entity_id=str(user.id) if user else None,
                    audit_metadata={},
                )
            )
            await db.commit()
            raise AppError("INVALID_CREDENTIALS", "Invalid clinic or credentials.", 401)
        access, refresh = pair(user, clinic.id)
        db.add(
            RefreshSession(
                user_id=user.id,
                token_hash=token_digest(refresh),
                expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
            )
        )
        user.last_login_at = datetime.now(UTC)
        db.add(
            AuditLog(
                actor_user_id=user.id,
                actor_role=user.role.value,
                action="LOGIN_SUCCESS",
                entity_type="User",
                entity_id=str(user.id),
                audit_metadata={},
            )
        )
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.access_token_minutes * 60,
        )


@router.post(
    "/refresh",
    response_model=TokenPair,
    dependencies=[Depends(sensitive_limit("refresh", 30, 60))],
)
async def refresh(body: RefreshRequest, control: Annotated[AsyncSession, Depends(control_session)]):
    payload = decode_token(body.refresh_token, "refresh")
    clinic = await resolver.by_id(control, uuid.UUID(payload["clinic"]))
    factory = resolver.session_factory(clinic)
    async with factory() as db, db.begin():
        session = await db.scalar(
            select(RefreshSession)
            .where(
                RefreshSession.token_hash == token_digest(body.refresh_token),
                RefreshSession.revoked_at.is_(None),
            )
            .with_for_update()
        )
        user = await db.get(User, uuid.UUID(payload["sub"]))
        if (
            not session
            or session.expires_at.replace(tzinfo=UTC) <= datetime.now(UTC)
            or not user
            or not user.is_active
            or user.token_version != payload["ver"]
        ):
            raise AppError("INVALID_SESSION", "Refresh session is invalid.", 401)
        session.revoked_at = datetime.now(UTC)
        access, new_refresh = pair(user, clinic.id)
        db.add(
            RefreshSession(
                user_id=user.id,
                token_hash=token_digest(new_refresh),
                expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
            )
        )
        return TokenPair(
            access_token=access,
            refresh_token=new_refresh,
            expires_in=settings.access_token_minutes * 60,
        )


@router.post("/logout", status_code=204)
async def logout(body: LogoutRequest):
    # Resolve the clinic from the signed refresh token, never from request clinic input.
    payload = decode_token(body.refresh_token, "refresh")
    from app.database.sessions import ControlSession

    async with ControlSession() as control:
        clinic = await resolver.by_id(control, uuid.UUID(payload["clinic"]))
        factory = resolver.session_factory(clinic)
    async with factory() as db, db.begin():
        await db.execute(
            update(RefreshSession)
            .where(RefreshSession.token_hash == token_digest(body.refresh_token))
            .values(revoked_at=datetime.now(UTC))
        )


@router.get("/me", response_model=MeResponse)
async def me(ctx: Annotated[AuthContext, Depends(current_context)]):
    return MeResponse(
        id=str(ctx.user.id),
        clinic_id=str(ctx.clinic.id),
        username=ctx.user.username,
        email=ctx.user.email,
        role=ctx.user.role.value,
        branch_scope=[str(x) for x in ctx.branch_ids],
    )
