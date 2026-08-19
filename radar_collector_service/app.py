from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession

app = FastAPI(title="DENTAI Radar Authorized Collector", version="1.0")
SERVICE_TOKEN = os.getenv("RADAR_COLLECTOR_TOKEN", "")
TELEGRAM_API_ID = int(os.getenv("RADAR_TELEGRAM_API_ID", "0") or 0)
TELEGRAM_API_HASH = os.getenv("RADAR_TELEGRAM_API_HASH", "")
META_API_VERSION = os.getenv("RADAR_META_API_VERSION", "v24.0")


def require_token(authorization: str | None) -> None:
    if SERVICE_TOKEN and authorization != f"Bearer {SERVICE_TOKEN}":
        raise HTTPException(status_code=401, detail="unauthorized")


class TelegramStart(BaseModel):
    phone: str = Field(min_length=6, max_length=40)


class TelegramComplete(BaseModel):
    phone: str
    code: str
    phone_code_hash: str
    session: str
    password: str | None = None


class CollectRequest(BaseModel):
    clinic_id: str
    source: dict[str, Any]
    authorization: dict[str, Any]
    limits: dict[str, int] = Field(default_factory=dict)
    mode: str


@app.get("/health")
async def health(authorization: str | None = Header(default=None)):
    require_token(authorization)
    return {"status": "ok", "read_only": True}


@app.post("/v1/auth/telegram/start")
async def telegram_start(payload: TelegramStart, authorization: str | None = Header(default=None)):
    require_token(authorization)
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        raise HTTPException(status_code=503, detail="telegram_api_not_configured")
    client = TelegramClient(StringSession(), TELEGRAM_API_ID, TELEGRAM_API_HASH)
    await client.connect()
    try:
        sent = await client.send_code_request(payload.phone)
        return {
            "session": client.session.save(),
            "phone_code_hash": sent.phone_code_hash,
            "next": "CODE",
        }
    finally:
        await client.disconnect()


@app.post("/v1/auth/telegram/complete")
async def telegram_complete(
    payload: TelegramComplete,
    authorization: str | None = Header(default=None),
):
    require_token(authorization)
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        raise HTTPException(status_code=503, detail="telegram_api_not_configured")
    client = TelegramClient(StringSession(payload.session), TELEGRAM_API_ID, TELEGRAM_API_HASH)
    await client.connect()
    try:
        try:
            await client.sign_in(
                phone=payload.phone,
                code=payload.code,
                phone_code_hash=payload.phone_code_hash,
            )
        except SessionPasswordNeededError:
            if not payload.password:
                return {
                    "session": client.session.save(),
                    "phone_code_hash": payload.phone_code_hash,
                    "next": "PASSWORD",
                }
            await client.sign_in(password=payload.password)
        me = await client.get_me()
        return {
            "session": client.session.save(),
            "next": "ACTIVE",
            "account_external_id": str(me.id),
            "account_display": " ".join(part for part in (me.first_name, me.last_name) if part),
        }
    finally:
        await client.disconnect()


def _telegram_entity(source: dict[str, Any]) -> str:
    handle = str(source.get("handle") or "").lstrip("@")
    if handle:
        return handle
    parsed = urlparse(str(source.get("source_url") or ""))
    parts = [part for part in parsed.path.split("/") if part and part != "s"]
    if not parts:
        raise HTTPException(status_code=422, detail="telegram_source_invalid")
    return parts[0]


async def collect_telegram(source: dict[str, Any], credentials: dict[str, Any], max_items: int):
    session = str(credentials.get("session") or "")
    if not session or not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        raise HTTPException(status_code=409, detail="telegram_session_required")
    client = TelegramClient(StringSession(session), TELEGRAM_API_ID, TELEGRAM_API_HASH)
    await client.connect()
    signals: list[dict[str, Any]] = []
    try:
        if not await client.is_user_authorized():
            raise HTTPException(status_code=409, detail="telegram_session_expired")
        entity = await client.get_entity(_telegram_entity(source))
        async for message in client.iter_messages(entity, limit=max_items):
            text = (message.message or "").strip()
            if not text:
                continue
            sender = await message.get_sender()
            sender_id = str(getattr(sender, "id", "")) or None
            display = " ".join(
                part
                for part in (
                    getattr(sender, "first_name", None),
                    getattr(sender, "last_name", None),
                    getattr(sender, "title", None),
                )
                if part
            ) or None
            signals.append(
                {
                    "external_signal_id": str(message.id),
                    "signal_type": "MESSAGE",
                    "text": text,
                    "context_text": None,
                    "source_url": str(source.get("source_url") or ""),
                    "author_external_id": sender_id,
                    "author_display": display,
                    "published_at": message.date.astimezone(UTC).isoformat() if message.date else None,
                }
            )
    finally:
        await client.disconnect()
    return {"signals": signals, "discovered_sources": [], "collector": "telegram_mtproto"}


async def _graph_get(path: str, token: str, params: dict[str, Any]) -> dict[str, Any]:
    params = {**params, "access_token": token}
    async with httpx.AsyncClient(timeout=25) as client:
        response = await client.get(
            f"https://graph.facebook.com/{META_API_VERSION}/{path.lstrip('/')}",
            params=params,
        )
    if response.status_code in {401, 403}:
        raise HTTPException(status_code=409, detail="meta_session_expired")
    if response.status_code == 429:
        raise HTTPException(status_code=429, detail="meta_rate_limited")
    if response.is_error:
        raise HTTPException(status_code=502, detail="meta_graph_error")
    return response.json()


async def collect_facebook(source: dict[str, Any], credentials: dict[str, Any], max_items: int):
    token = str(credentials.get("access_token") or "")
    source_id = str(source.get("external_source_id") or "")
    if not token or not source_id:
        raise HTTPException(status_code=409, detail="meta_authorization_required")
    data = await _graph_get(
        f"{source_id}/feed",
        token,
        {
            "limit": min(max_items, 100),
            "fields": "id,message,created_time,permalink_url,comments.limit(100){id,message,created_time,from{id,name}}",
        },
    )
    signals: list[dict[str, Any]] = []
    for post in data.get("data", []):
        context = str(post.get("message") or "")
        for comment in ((post.get("comments") or {}).get("data") or []):
            text = str(comment.get("message") or "").strip()
            if not text:
                continue
            author = comment.get("from") or {}
            signals.append(
                {
                    "external_signal_id": str(comment.get("id") or ""),
                    "signal_type": "COMMENT",
                    "text": text,
                    "context_text": context,
                    "source_url": str(post.get("permalink_url") or source.get("source_url") or ""),
                    "author_external_id": str(author.get("id") or "") or None,
                    "author_display": str(author.get("name") or "") or None,
                    "published_at": comment.get("created_time"),
                }
            )
            if len(signals) >= max_items:
                break
        if len(signals) >= max_items:
            break
    return {"signals": signals, "discovered_sources": [], "collector": "meta_graph_facebook"}


async def collect_instagram(source: dict[str, Any], credentials: dict[str, Any], max_items: int):
    token = str(credentials.get("access_token") or "")
    connected_ig_id = str(credentials.get("instagram_user_id") or "")
    handle = str(source.get("handle") or "").lstrip("@")
    if not token or not connected_ig_id:
        raise HTTPException(status_code=409, detail="instagram_authorization_required")
    if handle and str(source.get("external_source_id") or "") != connected_ig_id:
        discovery = await _graph_get(
            connected_ig_id,
            token,
            {
                "fields": f"business_discovery.username({handle}){{id,username,media.limit(25){{id,caption,permalink,timestamp,comments.limit(100){{id,text,timestamp,username}}}}}}"
            },
        )
        media = ((discovery.get("business_discovery") or {}).get("media") or {}).get("data", [])
    else:
        data = await _graph_get(
            f"{connected_ig_id}/media",
            token,
            {"limit": 25, "fields": "id,caption,permalink,timestamp,comments.limit(100){id,text,timestamp,username}"},
        )
        media = data.get("data", [])
    signals: list[dict[str, Any]] = []
    for post in media:
        context = str(post.get("caption") or "")
        for comment in ((post.get("comments") or {}).get("data") or []):
            text = str(comment.get("text") or "").strip()
            if not text:
                continue
            username = str(comment.get("username") or "") or None
            signals.append(
                {
                    "external_signal_id": str(comment.get("id") or ""),
                    "signal_type": "COMMENT",
                    "text": text,
                    "context_text": context,
                    "source_url": str(post.get("permalink") or source.get("source_url") or ""),
                    "author_external_id": username,
                    "author_display": username,
                    "published_at": comment.get("timestamp"),
                }
            )
            if len(signals) >= max_items:
                break
        if len(signals) >= max_items:
            break
    return {"signals": signals, "discovered_sources": [], "collector": "meta_graph_instagram"}


@app.post("/v1/collect")
async def collect(payload: CollectRequest, authorization: str | None = Header(default=None)):
    require_token(authorization)
    if payload.mode != "read_only":
        raise HTTPException(status_code=422, detail="read_only_required")
    platform = str(payload.source.get("platform") or "").upper()
    credentials = dict(payload.authorization.get("credentials") or {})
    max_items = max(1, min(int(payload.limits.get("max_items") or 100), 500))
    if platform == "TELEGRAM":
        return await collect_telegram(payload.source, credentials, max_items)
    if platform == "FACEBOOK":
        return await collect_facebook(payload.source, credentials, max_items)
    if platform == "INSTAGRAM":
        return await collect_instagram(payload.source, credentials, max_items)
    raise HTTPException(status_code=422, detail="unsupported_platform")
