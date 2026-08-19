from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.radar.collector import (
    CollectedSignal,
    CollectorResult,
    RadarCollectorError,
    collect_builtin,
)
from app.radar.connections import active_connection, decrypt_credentials


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


async def _remote(
    *,
    clinic_id: str,
    source: Any,
    db: AsyncSession,
) -> CollectorResult:
    settings = get_settings()
    if not settings.radar_collector_url:
        raise RadarCollectorError(
            "RADAR_AUTH_SESSION_REQUIRED",
            f"{source.platform.title()} requires the authorized collector service.",
            retryable=False,
        )
    connection = await active_connection(db, source.platform)
    if connection is None:
        raise RadarCollectorError(
            "RADAR_AUTH_SESSION_REQUIRED",
            f"{source.platform.title()} authorization must be connected or renewed.",
            retryable=False,
        )
    credentials = decrypt_credentials(connection.encrypted_credentials)
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.radar_collector_token:
        headers["Authorization"] = f"Bearer {settings.radar_collector_token}"
    payload = {
        "clinic_id": clinic_id,
        "source": {
            "id": str(source.id),
            "platform": source.platform,
            "external_source_id": source.external_source_id,
            "source_type": source.source_type,
            "name": source.name,
            "handle": source.handle,
            "source_url": source.source_url,
            "metadata": source.source_metadata or {},
        },
        "authorization": {
            "provider": connection.provider,
            "credentials": credentials,
        },
        "limits": {"max_items": settings.radar_max_items_per_poll},
        "mode": "read_only",
    }
    try:
        async with httpx.AsyncClient(timeout=settings.radar_collector_timeout_seconds) as client:
            response = await client.post(
                settings.radar_collector_url.rstrip("/") + "/v1/collect",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException as exc:
        raise RadarCollectorError("RADAR_COLLECTOR_TIMEOUT", "Authorized collector timed out.") from exc
    except httpx.HTTPStatusError as exc:
        retryable = exc.response.status_code >= 500 or exc.response.status_code in {408, 429}
        code = (
            "RADAR_AUTH_SESSION_REQUIRED"
            if exc.response.status_code in {401, 403, 409}
            else "RADAR_COLLECTOR_HTTP_ERROR"
        )
        raise RadarCollectorError(code, "Authorized collector rejected the source.", retryable=retryable) from exc
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise RadarCollectorError(
            "RADAR_COLLECTOR_INVALID_RESPONSE",
            "Authorized collector response was invalid.",
        ) from exc

    now = datetime.now(UTC)
    signals: list[CollectedSignal] = []
    for raw in list(data.get("signals") or [])[: settings.radar_max_items_per_poll]:
        text = _clean(raw.get("text"))
        if not text:
            continue
        published_at = None
        if raw.get("published_at"):
            try:
                published_at = datetime.fromisoformat(str(raw["published_at"]).replace("Z", "+00:00"))
            except ValueError:
                pass
        signals.append(
            CollectedSignal(
                external_signal_id=str(raw.get("external_signal_id")) if raw.get("external_signal_id") else None,
                signal_type=str(raw.get("signal_type") or "COMMENT").upper(),
                text=text[:20_000],
                context_text=_clean(raw.get("context_text"))[:30_000] or None,
                source_url=str(raw.get("source_url") or source.source_url)[:1500],
                author_external_id=str(raw.get("author_external_id")) if raw.get("author_external_id") else None,
                author_display=_clean(raw.get("author_display"))[:300] or None,
                author_profile_url=str(raw.get("author_profile_url"))[:1000] if raw.get("author_profile_url") else None,
                observed_at=now,
                published_at=published_at,
            )
        )
    connection.last_health_at = now
    connection.last_error_code = None
    connection.last_error = None
    await db.flush()
    return CollectorResult(
        signals=signals,
        discovered_sources=list(data.get("discovered_sources") or [])[:100],
        collector=str(data.get("collector") or "authorized"),
        fetched_at=now,
        source_revision=str(data.get("source_revision")) if data.get("source_revision") else None,
    )


async def collect_source(*, clinic_id: str, source: Any, db: AsyncSession) -> CollectorResult:
    platform = source.platform.strip().upper()
    metadata = source.source_metadata or {}
    if platform in {"INSTAGRAM", "FACEBOOK"} or metadata.get("collector") == "remote":
        return await _remote(clinic_id=clinic_id, source=source, db=db)
    try:
        return await collect_builtin(platform, source.source_url)
    except RadarCollectorError as exc:
        if exc.code == "RADAR_AUTH_SESSION_REQUIRED" and get_settings().radar_collector_url:
            return await _remote(clinic_id=clinic_id, source=source, db=db)
        raise
