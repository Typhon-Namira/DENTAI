"""Tenant-aware Patient Radar monitoring worker.

Run as a dedicated service with: ``python -m app.radar.worker``.
"""
from __future__ import annotations

import asyncio
import os
import socket
import uuid

import structlog
from sqlalchemy import select

from app.clinic_resolution.service import resolver
from app.core.config import get_settings
from app.database.control_models import ClinicRegistry
from app.database.sessions import ControlSession
from app.radar.models import RadarSource
from app.radar.operations import poll_registered_source
from app.radar.service import claim_due_source

logger = structlog.get_logger(__name__)


async def process_clinic(control, row: ClinicRegistry, *, worker_id: str) -> bool:
    clinic = await resolver.by_id(control, row.id)
    session_factory = resolver.session_factory(clinic)
    async with session_factory() as session:
        source = await claim_due_source(session, worker_id=worker_id)
        if source is None:
            return False
        source_id = source.id
        await session.commit()

    async with session_factory() as session:
        source = await session.get(RadarSource, source_id)
        if source is None:
            return False
        result = await poll_registered_source(
            session,
            clinic_id=clinic.id,
            source=source,
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


async def run() -> None:
    settings = get_settings()
    worker_id = os.getenv("RADAR_WORKER_ID", f"{socket.gethostname()}-{uuid.uuid4().hex[:10]}")
    await logger.ainfo("radar_worker_started", worker_id=worker_id)
    while True:
        did_work = False
        async with ControlSession() as control:
            clinics = (
                await control.scalars(
                    select(ClinicRegistry).where(ClinicRegistry.is_active.is_(True))
                )
            ).all()
            for row in clinics:
                try:
                    did_work = await process_clinic(control, row, worker_id=worker_id) or did_work
                except Exception as exc:
                    await logger.aerror(
                        "radar_worker_clinic_failed",
                        clinic_id=str(row.id),
                        error=type(exc).__name__,
                    )
        if not did_work:
            await asyncio.sleep(settings.radar_worker_poll_seconds)


if __name__ == "__main__":
    asyncio.run(run())
