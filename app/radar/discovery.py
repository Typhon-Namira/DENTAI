from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.radar.engine import source_rank
from app.radar.models import RadarSignal, RadarSource, RadarSourceCandidate

_ARMENIA_MARKERS = (
    "armenia",
    "armenian",
    "yerevan",
    "gyumri",
    "vanadzor",
    "հայաստան",
    "երևան",
    "ереван",
    "армения",
)


def source_external_id(platform: str, url: str) -> str:
    return hashlib.sha256(
        f"{platform.strip().upper()}|{url.strip()}".encode()
    ).hexdigest()[:48]


def _handle(url: str) -> str | None:
    parsed = urlparse(url)
    parts = [item for item in parsed.path.split("/") if item and item != "s"]
    return parts[0][:300] if parts else None


def score_discovered_source(
    parent: RadarSource,
    candidate: dict[str, Any],
    *,
    repeats: int = 1,
) -> int:
    url = str(candidate.get("source_url") or "")
    haystack = (
        f"{url} {candidate.get('name') or ''} {candidate.get('handle') or ''}"
    ).casefold()
    score = 35
    score += int(parent.armenia_relevance * 0.25)
    score += min(15, max(0, repeats - 1) * 3)
    if any(marker in haystack for marker in _ARMENIA_MARKERS):
        score += 20
    if str(candidate.get("platform") or "").upper() in {
        "INSTAGRAM",
        "FACEBOOK",
        "TELEGRAM",
    }:
        score += 5
    return max(0, min(100, score))


async def record_discoveries(
    db: AsyncSession,
    *,
    parent: RadarSource,
    discovered: list[dict[str, Any]],
) -> tuple[int, int]:
    """Upsert discovered graph nodes and auto-promote sufficiently strong candidates."""
    created = 0
    promoted = 0
    now = datetime.now(UTC)
    threshold = get_settings().radar_discovery_auto_promote_score
    for raw in discovered[:100]:
        platform = str(raw.get("platform") or "WEB").strip().upper()
        url = str(raw.get("source_url") or "").strip()
        if not url.startswith(("http://", "https://")):
            continue
        external_id = str(
            raw.get("external_source_id") or source_external_id(platform, url)
        )[:300]
        if await db.scalar(
            select(RadarSource.id).where(
                RadarSource.platform == platform,
                RadarSource.external_source_id == external_id,
            )
        ):
            continue
        candidate = await db.scalar(
            select(RadarSourceCandidate).where(
                RadarSourceCandidate.platform == platform,
                RadarSourceCandidate.external_source_id == external_id,
            )
        )
        handle = str(raw.get("handle") or _handle(url) or "")[:300] or None
        name = str(
            raw.get("name") or handle or urlparse(url).hostname or "Discovered source"
        )[:300]
        if candidate is None:
            candidate = RadarSourceCandidate(
                platform=platform,
                external_source_id=external_id,
                source_type=str(raw.get("source_type") or "WEB_SOURCE").upper()[:40],
                name=name,
                handle=handle,
                source_url=url[:1000],
                location_hint="Armenia" if parent.armenia_relevance >= 65 else None,
                language_hints=list(parent.language_hints or []),
                discovered_from_source_id=parent.id,
                state="NEW",
                candidate_score=score_discovered_source(parent, raw),
                discovery_count=1,
                last_discovered_at=now,
                evidence={"parent_source_id": str(parent.id), "read_only": True},
            )
            db.add(candidate)
            await db.flush()
            created += 1
        else:
            candidate.discovery_count += 1
            candidate.last_discovered_at = now
            candidate.candidate_score = score_discovered_source(
                parent,
                raw,
                repeats=candidate.discovery_count,
            )
        if candidate.state == "NEW" and candidate.candidate_score >= threshold:
            score, priority, interval = source_rank(
                max(parent.armenia_relevance, float(candidate.candidate_score)),
                max(30.0, parent.engagement_score * 0.75),
                max(25.0, parent.dental_signal_probability * 0.60),
            )
            db.add(
                RadarSource(
                    platform=platform,
                    external_source_id=external_id,
                    source_type=candidate.source_type,
                    name=candidate.name,
                    handle=candidate.handle,
                    source_url=candidate.source_url,
                    language_hints=candidate.language_hints,
                    location_hint=candidate.location_hint,
                    armenia_relevance=max(
                        parent.armenia_relevance,
                        float(candidate.candidate_score),
                    ),
                    engagement_score=max(30.0, parent.engagement_score * 0.75),
                    dental_signal_probability=max(
                        25.0,
                        parent.dental_signal_probability * 0.60,
                    ),
                    source_score=score,
                    priority=priority,
                    monitoring_interval_minutes=interval,
                    next_check_at=now,
                    source_metadata={
                        "discovered": True,
                        "candidate_id": str(candidate.id),
                    },
                )
            )
            candidate.state = "AUTO_PROMOTED"
            promoted += 1
    await db.flush()
    return created, promoted


async def refresh_source_quality(db: AsyncSession, source: RadarSource) -> None:
    """Re-rank a source from recent observed yield instead of frontend defaults."""
    lookback = datetime.now(UTC) - timedelta(
        days=get_settings().radar_source_quality_lookback_days
    )
    rows = (
        await db.execute(
            select(
                func.count(RadarSignal.id),
                func.sum(case((RadarSignal.is_candidate.is_(True), 1), else_=0)),
                func.avg(RadarSignal.location_match),
            ).where(
                RadarSignal.source_id == source.id,
                RadarSignal.observed_at >= lookback,
            )
        )
    ).one()
    total = int(rows[0] or 0)
    candidates = int(rows[1] or 0)
    location_avg = float(rows[2] or 0.0)
    if total:
        source.dental_signal_probability = max(
            0.0,
            min(100.0, candidates / total * 100.0),
        )
        source.armenia_relevance = max(
            source.armenia_relevance * 0.4,
            min(100.0, location_avg * 100.0),
        )
        runtime = dict(source.source_metadata or {})
        seen = int(runtime.get("last_signal_count") or total)
        new = int(runtime.get("last_new_signal_count") or candidates)
        activity = min(
            100.0,
            30.0
            + min(50.0, seen / max(1, total) * 50.0)
            + min(20.0, new * 2.0),
        )
        source.engagement_score = activity
    score, priority, interval = source_rank(
        source.armenia_relevance,
        source.engagement_score,
        source.dental_signal_probability,
        active=source.is_active,
    )
    source.source_score = score
    source.priority = priority
    source.monitoring_interval_minutes = interval
    await db.flush()
