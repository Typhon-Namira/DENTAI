"""Tenant-aware Patient Radar production worker.

Run as a dedicated Railway service with: ``python -m app.radar.worker``.
"""
from __future__ import annotations

import asyncio
import os
import socket
import time
import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select

from app.clinic_resolution.service import resolver
from app.core.config import get_settings
from app.database.control_models import ClinicRegistry
from app.database.sessions import ControlSession, dispose_control_engine
from app.radar.maintenance import privacy_cleanup, update_runtime_state
from app.radar.models import RadarSource
from app.radar.operations import poll_registered_source
from app.radar.service import claim_due_source

logger = structlog.get_logger(__name__)


async def _claim_one(row: ClinicRegistry, *, worker_id: str) -> tuple[uuid.UUID, uuid.UUID] | None:
    async with ControlSession() as control:
        clinic = await resolver.by_id(control, row.id)
    session_factory = resolver.session_factory(clinic)
    async with session_factory() as session:
        source = await claim_due_source(session, worker_id=worker_id)
        if source is None:
            return None
        source_id = source.id
        await session.commit()
    return clinic.id, source_id


async def _process_claim(clinic_id: uuid.UUID, source_id: uuid.UUID, *, worker_id: str) -> bool:
    async with ControlSession() as control:
        clinic = await resolver.by_id(control, clinic_id)
    session_factory = resolver.session_factory(clinic)
    async with session_factory() as session:
        source = await session.get(RadarSource, source_id)
        if source is None:
            return False
        result = await poll_registered_source(session, clinic_id=clinic.id, source=source)
        await update_runtime_state(
            session,
            f"worker:{worker_id}",
            {
                "worker_id": worker_id,
                "heartbeat_at": datetime.now(UTC).isoformat(),
                "last_source_id": str(source_id),
                "last_status": result.get("status"),
                "last_new_signals": result.get("new_signals", 0),
            },
        )
        await session.commit()
        await logger.ainfo(
            "radar_source_polled",
            clinic_id=str(clinic.id),
            source_id=str(source_id),
            status=result.get("status"),
            new_signals=result.get("new_signals", 0),
        )
        return True


async def _maintenance(row: ClinicRegistry, *, worker_id: str) -> None:
    async with ControlSession() as control:
        clinic = await resolver.by_id(control, row.id)
    session_factory = resolver.session_factory(clinic)
    async with session_factory() as session:
        cleanup = await privacy_cleanup(session)
        await update_runtime_state(
            session,
            f"worker:{worker_id}",
            {
                "worker_id": worker_id,
                "heartbeat_at": datetime.now(UTC).isoformat(),
                "maintenance": cleanup,
            },
        )
        await session.commit()


async def run() -> None:
    settings = get_settings()
    if not settings.radar_enabled:
        await logger.awarning("radar_worker_disabled")
        return
    worker_id = os.getenv("RADAR_WORKER_ID", f"{socket.gethostname()}-{uuid.uuid4().hex[:10]}")
    concurrency = max(1, min(32, settings.radar_worker_concurrency))
    await logger.ainfo("radar_worker_started", worker_id=worker_id, concurrency=concurrency)
    last_maintenance = 0.0
    try:
        while True:
            async with ControlSession() as control:
                clinics = list(
                    (
                        await control.scalars(
                            select(ClinicRegistry).where(ClinicRegistry.is_active.is_(True))
                        )
                    ).all()
                )
            claims: list[tuple[uuid.UUID, uuid.UUID]] = []
            for row in clinics:
                while len(claims) < concurrency:
                    try:
                        claim = await _claim_one(row, worker_id=worker_id)
                    except Exception as exc:
                        await logger.aerror(
                            "radar_worker_claim_failed",
                            clinic_id=str(row.id),
                            error=type(exc).__name__,
                        )
                        break
                    if claim is None:
                        break
                    claims.append(claim)
                if len(claims) >= concurrency:
                    break

            if claims:
                results = await asyncio.gather(
                    *(
                        _process_claim(clinic_id, source_id, worker_id=worker_id)
                        for clinic_id, source_id in claims
                    ),
                    return_exceptions=True,
                )
                for result in results:
                    if isinstance(result, Exception):
                        await logger.aerror("radar_worker_task_failed", error=type(result).__name__)
            else:
                await asyncio.sleep(settings.radar_worker_poll_seconds)

            now = time.monotonic()
            if now - last_maintenance >= settings.radar_cleanup_interval_seconds:
                for row in clinics:
                    try:
                        await _maintenance(row, worker_id=worker_id)
                    except Exception as exc:
                        await logger.aerror(
                            "radar_worker_maintenance_failed",
                            clinic_id=str(row.id),
                            error=type(exc).__name__,
                        )
                last_maintenance = now
    finally:
        await resolver.dispose_all()
        await dispose_control_engine()
        await logger.ainfo("radar_worker_stopped", worker_id=worker_id)


if __name__ == "__main__":
    asyncio.run(run())
