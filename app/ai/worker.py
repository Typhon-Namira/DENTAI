"""Dedicated DENTAI V5 analysis worker; run with ``python -m app.ai.worker``."""
import asyncio
import os
import socket
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from ai_engine.inference.dentai_unified_v5_onnx import Engine
from app.ai.jobs import claim_next_analysis, heartbeat, schedule_retry
from app.ai.providers import DENTAIRealOPGProvider
from app.clinic_resolution.service import resolver
from app.core.config import get_settings
from app.database.control_models import ClinicRegistry
from app.database.models import AIAnalysis, AIStatus, DentalFinding, FindingReview, XRay
from app.database.sessions import ControlSession
from app.outreach.service import schedule_analysis_outreach
from app.storage.providers import storage_provider


async def _heartbeat_loop(session_factory, analysis_id, worker_id, interval):
    while True:
        await asyncio.sleep(interval)
        async with session_factory() as heartbeat_session:
            if not await heartbeat(heartbeat_session, analysis_id, worker_id):
                return


async def process_one(session, session_factory, worker_id: str) -> bool:
    job = await claim_next_analysis(session, worker_id)
    if job is None:
        return False
    interval = get_settings().ai_worker_heartbeat_seconds
    beat = asyncio.create_task(_heartbeat_loop(session_factory, job.id, worker_id, interval))
    try:
        xray = await session.get(XRay, job.xray_id)
        if xray is None:
            raise RuntimeError("XRAY_NOT_FOUND")
        image_bytes = await storage_provider().read(xray.storage_key)
        prior = await session.scalar(
            select(AIAnalysis.structured_result)
            .where(AIAnalysis.patient_id == job.patient_id, AIAnalysis.status == AIStatus.COMPLETED)
            .order_by(AIAnalysis.completed_at.desc()).limit(1)
        )
        result = await DENTAIRealOPGProvider().analyze_xray(
            patient_context={"patient_id": str(job.patient_id)}, xray_reference=str(xray.id),
            image_bytes=image_bytes, prior_analysis=prior,
        )
        job.provider, job.model_name, job.model_version = (
            result.provider,
            result.model_name,
            result.model_version,
        )
        job.analysis_schema_version, job.structured_result = (
            result.schema_version,
            result.structured_result,
        )
        job.status, job.completed_at, job.error_code = AIStatus.COMPLETED, datetime.now(UTC), None
        created_findings = []
        for item in result.findings:
            finding = DentalFinding(
                patient_id=job.patient_id,
                analysis_id=job.id,
                source="AI",
                review_status=FindingReview.PENDING,
                **item,
            )
            session.add(finding)
            created_findings.append(finding)
        await session.flush()
        await schedule_analysis_outreach(session, job, created_findings)
        await session.commit()
    except Exception as exc:
        await session.rollback()
        failed = await session.get(AIAnalysis, job.id)
        if failed:
            await schedule_retry(session, failed, type(exc).__name__.upper())
    finally:
        beat.cancel()
        try:
            await beat
        except asyncio.CancelledError:
            pass
    return True


async def run() -> None:
    settings = get_settings()
    # Startup/release gate: hashes, exact filenames, and all ONNX sessions before any claim.
    Engine(settings.ai_model_artifact_path, settings.ai_model_manifest_path)
    worker_id = os.getenv("AI_WORKER_ID", f"{socket.gethostname()}-{uuid.uuid4().hex[:12]}")
    while True:
        did_work = False
        async with ControlSession() as control:
            query = select(ClinicRegistry).where(ClinicRegistry.is_active.is_(True))
            clinics = (await control.scalars(query)).all()
            for row in clinics:
                clinic = await resolver.by_id(control, row.id)
                session_factory = resolver.session_factory(clinic)
                async with session_factory() as session:
                    did_work = await process_one(session, session_factory, worker_id) or did_work
        if not did_work:
            await asyncio.sleep(settings.ai_worker_poll_seconds)


if __name__ == "__main__":
    asyncio.run(run())
