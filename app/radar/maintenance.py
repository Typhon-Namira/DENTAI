from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.radar.models import RadarOpportunity, RadarOutcome, RadarRuntimeState, RadarSignal

POSITIVE_OUTCOMES = {"BOOKED", "QUALIFIED"}
OUTCOMES = {"CONTACTED", "QUALIFIED", "BOOKED", "REJECTED", "NO_RESPONSE"}


async def update_runtime_state(db: AsyncSession, key: str, value: dict[str, Any]) -> None:
    row = await db.scalar(select(RadarRuntimeState).where(RadarRuntimeState.key == key))
    if row is None:
        row = RadarRuntimeState(key=key, value=value)
        db.add(row)
    else:
        row.value = value
    await db.flush()


async def privacy_cleanup(db: AsyncSession) -> dict[str, int]:
    """Minimize retained raw signal text while preserving aggregate opportunity records."""
    settings = get_settings()
    now = datetime.now(UTC)
    ignored_cutoff = now - timedelta(days=settings.radar_ignored_retention_days)
    all_cutoff = now - timedelta(days=settings.radar_signal_retention_days)
    ignored = await db.execute(
        delete(RadarSignal).where(
            RadarSignal.is_candidate.is_(False),
            RadarSignal.created_at < ignored_cutoff,
        )
    )
    old = await db.execute(delete(RadarSignal).where(RadarSignal.created_at < all_cutoff))
    return {
        "ignored_deleted": int(ignored.rowcount or 0),
        "expired_deleted": int(old.rowcount or 0),
    }


async def record_outcome(
    db: AsyncSession,
    *,
    opportunity: RadarOpportunity,
    outcome: str,
    metadata: dict[str, Any] | None = None,
) -> RadarOutcome:
    normalized = outcome.strip().upper()
    if normalized not in OUTCOMES:
        raise ValueError("unsupported Radar outcome")
    row = RadarOutcome(
        opportunity_id=opportunity.id,
        outcome=normalized,
        occurred_at=datetime.now(UTC),
        outcome_metadata=dict(metadata or {}),
    )
    db.add(row)
    await db.flush()
    return row


async def calibration_report(db: AsyncSession) -> dict[str, Any]:
    """Return empirical conversion by score band; never invent calibration without outcomes."""
    rows = (
        await db.execute(
            select(RadarOpportunity.opportunity_score, RadarOutcome.outcome)
            .join(RadarOutcome, RadarOutcome.opportunity_id == RadarOpportunity.id)
            .order_by(RadarOutcome.occurred_at.desc())
            .limit(5000)
        )
    ).all()
    bands = {
        "90-100": [0, 0],
        "75-89": [0, 0],
        "50-74": [0, 0],
        "0-49": [0, 0],
    }
    for score, outcome in rows:
        if score >= 90:
            key = "90-100"
        elif score >= 75:
            key = "75-89"
        elif score >= 50:
            key = "50-74"
        else:
            key = "0-49"
        bands[key][1] += 1
        if outcome in POSITIVE_OUTCOMES:
            bands[key][0] += 1
    report = {
        key: {
            "positive": positive,
            "total": total,
            "observed_rate": round(positive / total, 4) if total else None,
        }
        for key, (positive, total) in bands.items()
    }
    sample_size = len(rows)
    return {
        "sample_size": sample_size,
        "ready_for_recalibration": sample_size >= 200,
        "bands": report,
        "policy": "ranking-only until sufficient observed outcomes exist",
    }


async def recent_metrics(db: AsyncSession) -> dict[str, Any]:
    since = datetime.now(UTC) - timedelta(hours=24)
    signals = int(
        await db.scalar(select(func.count(RadarSignal.id)).where(RadarSignal.created_at >= since)) or 0
    )
    candidates = int(
        await db.scalar(
            select(func.count(RadarSignal.id)).where(
                RadarSignal.created_at >= since,
                RadarSignal.is_candidate.is_(True),
            )
        )
        or 0
    )
    return {
        "signals_24h": signals,
        "candidates_24h": candidates,
        "candidate_yield": round(candidates / signals, 4) if signals else 0.0,
    }
