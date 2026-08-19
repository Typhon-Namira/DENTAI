from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.auth.dependencies import AuthContext, current_context, roles
from app.core.config import get_settings
from app.core.errors import AppError
from app.database.models import Role
from app.radar.connections import (
    activate_connection,
    connection_by_id,
    connection_public,
    create_connection,
    decrypt_credentials,
    disconnect_connection,
    encrypt_credentials,
)
from app.radar.maintenance import calibration_report, recent_metrics, record_outcome
from app.radar.models import RadarConnection, RadarOpportunity, RadarSourceCandidate

router = APIRouter(prefix="/radar", tags=["patient-radar-connections"])


class MetaStartIn(BaseModel):
    platform: str = Field(pattern="^(FACEBOOK|INSTAGRAM)$")


class MetaCompleteIn(BaseModel):
    code: str = Field(min_length=3, max_length=3000)
    state: str = Field(min_length=10, max_length=500)


class TelegramStartIn(BaseModel):
    phone: str = Field(min_length=6, max_length=40)


class TelegramCompleteIn(BaseModel):
    code: str = Field(min_length=2, max_length=20)
    password: str | None = Field(default=None, max_length=300)


class OutcomeIn(BaseModel):
    outcome: str
    metadata: dict[str, Any] = Field(default_factory=dict)


def _collector_headers() -> dict[str, str]:
    token = get_settings().radar_collector_token
    return {"Authorization": f"Bearer {token}"} if token else {}


def _collector_url(path: str) -> str:
    base = get_settings().radar_collector_url
    if not base:
        raise AppError("RADAR_COLLECTOR_NOT_CONFIGURED", "Radar collector is not configured.", 503)
    return base.rstrip("/") + path


@router.get("/connections")
async def list_connections(ctx: Annotated[AuthContext, Depends(current_context)]):
    rows = list(
        (
            await ctx.session.scalars(
                select(RadarConnection).order_by(RadarConnection.updated_at.desc())
            )
        ).all()
    )
    return [connection_public(row) for row in rows]


@router.post("/connections/meta/start")
async def meta_start(
    payload: MetaStartIn,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER))],
):
    settings = get_settings()
    if not settings.radar_meta_app_id or not settings.radar_meta_redirect_uri:
        raise AppError("RADAR_META_NOT_CONFIGURED", "Meta Radar authorization is not configured.", 503)
    connection = await create_connection(ctx.session, platform=payload.platform)
    state = f"{connection.id}.{connection.auth_nonce}"
    scopes = ["pages_show_list", "pages_read_engagement"]
    if payload.platform == "INSTAGRAM":
        scopes += ["instagram_basic", "instagram_manage_comments"]
    query = urlencode(
        {
            "client_id": settings.radar_meta_app_id,
            "redirect_uri": settings.radar_meta_redirect_uri,
            "state": state,
            "response_type": "code",
            "scope": ",".join(scopes),
        }
    )
    await ctx.session.commit()
    return {
        "connection": connection_public(connection),
        "authorization_url": f"https://www.facebook.com/{settings.radar_meta_api_version}/dialog/oauth?{query}",
        "state": state,
        "read_only": True,
    }


@router.post("/connections/{connection_id}/meta/complete")
async def meta_complete(
    connection_id: uuid.UUID,
    payload: MetaCompleteIn,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER))],
):
    settings = get_settings()
    connection = await connection_by_id(ctx.session, connection_id)
    expected = f"{connection.id}.{connection.auth_nonce}"
    if connection.provider != "META_GRAPH" or payload.state != expected:
        raise AppError("RADAR_META_STATE_INVALID", "Meta authorization state is invalid.", 409)
    if not all((settings.radar_meta_app_id, settings.radar_meta_app_secret, settings.radar_meta_redirect_uri)):
        raise AppError("RADAR_META_NOT_CONFIGURED", "Meta Radar authorization is not configured.", 503)
    params = {
        "client_id": settings.radar_meta_app_id,
        "client_secret": settings.radar_meta_app_secret,
        "redirect_uri": settings.radar_meta_redirect_uri,
        "code": payload.code,
    }
    base = f"https://graph.facebook.com/{settings.radar_meta_api_version}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            token_response = await client.get(f"{base}/oauth/access_token", params=params)
            token_response.raise_for_status()
            token_data = token_response.json()
            user_token = str(token_data["access_token"])
            me_response = await client.get(
                f"{base}/me",
                params={"fields": "id,name", "access_token": user_token},
            )
            me_response.raise_for_status()
            me = me_response.json()
            pages_response = await client.get(
                f"{base}/me/accounts",
                params={
                    "fields": "id,name,access_token,instagram_business_account{id,username}",
                    "access_token": user_token,
                },
            )
            pages_response.raise_for_status()
            pages_data = list(pages_response.json().get("data") or [])
    except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
        raise AppError("RADAR_META_AUTH_FAILED", "Meta authorization could not be completed.", 409) from exc

    pages = [
        {
            "id": str(page.get("id") or ""),
            "name": str(page.get("name") or ""),
            "access_token": str(page.get("access_token") or ""),
            "instagram_business_account": page.get("instagram_business_account"),
        }
        for page in pages_data
        if page.get("id") and page.get("access_token")
    ]
    instagram_ids = [
        str(page["instagram_business_account"]["id"])
        for page in pages
        if isinstance(page.get("instagram_business_account"), dict)
        and page["instagram_business_account"].get("id")
    ]
    expires_in = int(token_data.get("expires_in") or 0)
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_in) if expires_in else None
    await activate_connection(
        ctx.session,
        connection,
        credentials={
            "access_token": user_token,
            "pages": pages,
            "instagram_user_id": instagram_ids[0] if instagram_ids else None,
        },
        account_external_id=str(me.get("id") or "") or None,
        account_display=str(me.get("name") or "") or None,
        scopes=[],
        expires_at=expires_at,
        metadata={"pages": len(pages), "instagram_accounts": len(instagram_ids)},
    )
    await ctx.session.commit()
    return connection_public(connection)


@router.post("/connections/telegram/start")
async def telegram_start(
    payload: TelegramStartIn,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER))],
):
    connection = await create_connection(ctx.session, platform="TELEGRAM")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                _collector_url("/v1/auth/telegram/start"),
                headers=_collector_headers(),
                json={"phone": payload.phone},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise AppError("RADAR_TELEGRAM_AUTH_FAILED", "Telegram authorization could not start.", 409) from exc
    connection.encrypted_credentials = encrypt_credentials(
        {
            "phone": payload.phone,
            "session": data["session"],
            "phone_code_hash": data["phone_code_hash"],
        }
    )
    connection.connection_metadata = {"read_only": True, "next": data.get("next", "CODE")}
    await ctx.session.commit()
    return {"connection": connection_public(connection), "next": data.get("next", "CODE")}


@router.post("/connections/{connection_id}/telegram/complete")
async def telegram_complete(
    connection_id: uuid.UUID,
    payload: TelegramCompleteIn,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER))],
):
    connection = await connection_by_id(ctx.session, connection_id)
    if connection.platform != "TELEGRAM" or connection.status != "CONNECTING":
        raise AppError("RADAR_TELEGRAM_STATE_INVALID", "Telegram connection is not awaiting login.", 409)
    pending = decrypt_credentials(connection.encrypted_credentials)
    request = {**pending, "code": payload.code, "password": payload.password}
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            response = await client.post(
                _collector_url("/v1/auth/telegram/complete"),
                headers=_collector_headers(),
                json=request,
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise AppError("RADAR_TELEGRAM_AUTH_FAILED", "Telegram authorization could not complete.", 409) from exc
    if data.get("next") == "PASSWORD":
        connection.encrypted_credentials = encrypt_credentials({**pending, "session": data["session"]})
        connection.connection_metadata = {"read_only": True, "next": "PASSWORD"}
        await ctx.session.commit()
        return {"connection": connection_public(connection), "next": "PASSWORD"}
    await activate_connection(
        ctx.session,
        connection,
        credentials={"session": data["session"]},
        account_external_id=str(data.get("account_external_id") or "") or None,
        account_display=str(data.get("account_display") or "") or None,
        metadata={"next": "ACTIVE"},
    )
    await ctx.session.commit()
    return {"connection": connection_public(connection), "next": "ACTIVE"}


@router.delete("/connections/{connection_id}")
async def disconnect(
    connection_id: uuid.UUID,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER))],
):
    connection = await connection_by_id(ctx.session, connection_id)
    await disconnect_connection(ctx.session, connection)
    await ctx.session.commit()
    return connection_public(connection)


@router.get("/source-candidates")
async def source_candidates(
    ctx: Annotated[AuthContext, Depends(current_context)],
    limit: int = 100,
):
    rows = list(
        (
            await ctx.session.scalars(
                select(RadarSourceCandidate)
                .order_by(RadarSourceCandidate.candidate_score.desc())
                .limit(max(1, min(limit, 500)))
            )
        ).all()
    )
    return rows


@router.post("/opportunities/{opportunity_id}/outcomes")
async def opportunity_outcome(
    opportunity_id: uuid.UUID,
    payload: OutcomeIn,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER))],
):
    opportunity = await ctx.session.get(RadarOpportunity, opportunity_id)
    if not opportunity:
        raise AppError("RADAR_OPPORTUNITY_NOT_FOUND", "Patient opportunity was not found.", 404)
    try:
        row = await record_outcome(
            ctx.session,
            opportunity=opportunity,
            outcome=payload.outcome,
            metadata=payload.metadata,
        )
    except ValueError as exc:
        raise AppError("RADAR_OUTCOME_INVALID", "Unsupported Radar outcome.", 422) from exc
    await ctx.session.commit()
    return {"id": str(row.id), "outcome": row.outcome, "occurred_at": row.occurred_at}


@router.get("/calibration")
async def calibration(ctx: Annotated[AuthContext, Depends(current_context)]):
    return await calibration_report(ctx.session)


@router.get("/metrics")
async def metrics(ctx: Annotated[AuthContext, Depends(current_context)]):
    return await recent_metrics(ctx.session)
