from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.radar.collector import RadarCollectorError
from app.radar.discovery import record_discoveries, refresh_source_quality
from app.radar.funnel import run_funnel
from app.radar.models import RadarSource
from app.radar.runtime_collector import collect_source
from app.radar.service import complete_source_poll, fail_source_poll, ingest_signal


async def mark_manual_claim(db: AsyncSession, source: RadarSource, *, worker_id: str) -> None:
    metadata = dict(source.source_metadata or {})
    now = datetime.now(UTC)
    metadata.update(
        runtime_state="CLAIMED",
        claimed_by=worker_id,
        claimed_at=now.isoformat(),
        last_error_code=None,
        last_error=None,
    )
    source.source_metadata = metadata
    source.next_check_at = now + timedelta(seconds=get_settings().radar_claim_seconds)
    await db.flush()


async def poll_registered_source(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    source: RadarSource,
) -> dict[str, Any]:
    started = time.perf_counter()
    metadata = dict(source.source_metadata or {})
    metadata["runtime_state"] = "POLLING"
    source.source_metadata = metadata
    await db.flush()

    try:
        collected = await collect_source(clinic_id=str(clinic_id), source=source, db=db)
        funnel = await run_funnel(db, source=source, collected=collected.signals)
        new_count = 0
        candidate_count = 0
        for item, classification in zip(funnel.signals, funnel.classifications, strict=True):
            result = await ingest_signal(
                db,
                clinic_id=clinic_id,
                source=source,
                external_signal_id=item.external_signal_id,
                signal_type=item.signal_type,
                text=item.text,
                context_text=item.context_text,
                source_url=item.source_url,
                author_external_id=item.author_external_id,
                author_display=item.author_display,
                author_profile_url=item.author_profile_url,
                observed_at=item.observed_at,
                published_at=item.published_at,
                classification=classification,
            )
            if not result.duplicate:
                new_count += 1
            if classification.candidate:
                candidate_count += 1

        discovered_created = 0
        discovered_promoted = 0
        if collected.discovered_sources:
            discovered_created, discovered_promoted = await record_discoveries(
                db, parent=source, discovered=collected.discovered_sources
            )
        await refresh_source_quality(db, source)

        duration_ms = int((time.perf_counter() - started) * 1000)
        source_meta = dict(source.source_metadata or {})
        source_meta["funnel"] = {
            "raw": len(collected.signals),
            "duplicates_skipped": funnel.duplicates_skipped,
            "semantic_candidates": funnel.semantic_candidates,
            "cheap_rejected": funnel.cheap_rejected,
        }
        source_meta["discovery"] = {
            "seen": len(collected.discovered_sources),
            "created": discovered_created,
            "auto_promoted": discovered_promoted,
        }
        source.source_metadata = source_meta
        await complete_source_poll(
            db,
            source,
            collector=collected.collector,
            signal_count=len(collected.signals),
            new_signal_count=new_count,
            duration_ms=duration_ms,
            source_revision=collected.source_revision,
        )
        return {
            "source_id": str(source.id),
            "status": "HEALTHY",
            "collector": collected.collector,
            "signals_seen": len(collected.signals),
            "new_signals": new_count,
            "candidate_signals": candidate_count,
            "duplicates_skipped": funnel.duplicates_skipped,
            "semantic_candidates": funnel.semantic_candidates,
            "discovered_sources": discovered_created,
            "auto_promoted_sources": discovered_promoted,
            "duration_ms": duration_ms,
        }
    except RadarCollectorError as exc:
        await fail_source_poll(
            db,
            source,
            error_code=exc.code,
            safe_error=str(exc),
            retryable=exc.retryable,
        )
        return {
            "source_id": str(source.id),
            "status": "ERROR" if exc.retryable else "ACTION_REQUIRED",
            "error_code": exc.code,
            "error": str(exc),
            "retryable": exc.retryable,
        }
    except Exception as exc:
        await fail_source_poll(
            db,
            source,
            error_code="RADAR_POLL_FAILED",
            safe_error=type(exc).__name__,
            retryable=True,
        )
        return {
            "source_id": str(source.id),
            "status": "ERROR",
            "error_code": "RADAR_POLL_FAILED",
            "error": "Source poll failed.",
            "retryable": True,
        }
