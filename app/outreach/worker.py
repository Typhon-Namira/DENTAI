"""Run due DENTAI WhatsApp reminders with python -m app.outreach.worker."""

import asyncio
import os
import socket
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select

from app.clinic_resolution.service import resolver
from app.core.config import get_settings
from app.database.control_models import ClinicRegistry
from app.database.models import (
    AIAnalysis,
    DentalFinding,
    Patient,
    WhatsAppOutreach,
    WhatsAppOutreachStatus,
    XRay,
)
from app.database.sessions import ControlSession
from app.outreach.images import finding_crop
from app.outreach.whatsapp_client import WhatsAppServiceClient, WhatsAppServiceError

PERMANENT_ERRORS = {
    "WHATSAPP_PHONE_REQUIRED",
    "PHONE_NOT_ON_WHATSAPP",
    "INVALID_PHONE",
    "IMAGE_SIZE_INVALID",
}


async def recover_stale_claims(session) -> int:
    """Recover pre-dispatch claims and quarantine ambiguous post-dispatch claims."""
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.whatsapp_claim_timeout_seconds)
    rows = (
        await session.scalars(
            select(WhatsAppOutreach)
            .where(
                WhatsAppOutreach.status.in_(
                    [WhatsAppOutreachStatus.CLAIMED, WhatsAppOutreachStatus.SENDING]
                ),
                WhatsAppOutreach.claimed_at.is_not(None),
                WhatsAppOutreach.claimed_at < cutoff,
            )
            .with_for_update(skip_locked=True)
        )
    ).all()
    for row in rows:
        if row.status == WhatsAppOutreachStatus.CLAIMED and row.dispatch_started_at is None:
            row.status = WhatsAppOutreachStatus.SCHEDULED
            row.retry_at = datetime.now(UTC)
            row.safe_error = "STALE_CLAIM_RECOVERED"
            row.worker_id = None
            row.claimed_at = None
        else:
            row.status = WhatsAppOutreachStatus.SEND_UNKNOWN
            row.safe_error = "SEND_OUTCOME_UNKNOWN"
            row.failed_at = datetime.now(UTC)
    if rows:
        await session.commit()
    return len(rows)


async def claim_due(session, worker_id: str):
    await recover_stale_claims(session)
    now = datetime.now(UTC)
    row = await session.scalar(
        select(WhatsAppOutreach)
        .where(
            WhatsAppOutreach.status.in_(
                [WhatsAppOutreachStatus.SCHEDULED, WhatsAppOutreachStatus.QUEUED]
            ),
            WhatsAppOutreach.scheduled_send_at <= now,
            or_(WhatsAppOutreach.retry_at.is_(None), WhatsAppOutreach.retry_at <= now),
        )
        .order_by(WhatsAppOutreach.scheduled_send_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if row:
        row.status = WhatsAppOutreachStatus.CLAIMED
        row.worker_id = worker_id
        row.claimed_at = now
        row.dispatch_started_at = None
        row.attempt_count += 1
        await session.commit()
    return row


def _schedule_retry(row, seconds: int, code: str) -> None:
    row.status = WhatsAppOutreachStatus.SCHEDULED
    row.retry_at = datetime.now(UTC) + timedelta(seconds=seconds)
    row.safe_error = code
    row.worker_id = None
    row.claimed_at = None
    row.dispatch_started_at = None


def _mark_permanent_failure(row, code: str) -> None:
    row.status = WhatsAppOutreachStatus.FAILED
    row.safe_error = code
    row.failed_at = datetime.now(UTC)


async def process_due(
    session, clinic_id, worker_id: str, service: WhatsAppServiceClient | None = None
) -> bool:
    row = await claim_due(session, worker_id)
    if row is None:
        return False
    service = service or WhatsAppServiceClient()
    settings = get_settings()
    dispatch_started = False
    try:
        patient = await session.get(Patient, row.patient_id)
        if patient is None or not patient.whatsapp_phone:
            raise WhatsAppServiceError("WHATSAPP_PHONE_REQUIRED", 409)
        connection = await service.status(clinic_id)
        if not connection.get("connected"):
            raise WhatsAppServiceError("WHATSAPP_CONNECTION_REQUIRED", 409)
        validation = await service.validate_phone(clinic_id, patient.whatsapp_phone)
        if not validation.get("registered"):
            raise WhatsAppServiceError("PHONE_NOT_ON_WHATSAPP", 422)

        image = None
        if row.include_image and row.finding_id:
            finding = await session.get(DentalFinding, row.finding_id)
            analysis = await session.get(AIAnalysis, row.analysis_id)
            xray = await session.get(XRay, analysis.xray_id) if analysis else None
            image = await finding_crop(xray, finding) if xray and finding else None

        row.status = WhatsAppOutreachStatus.SENDING
        row.dispatch_started_at = datetime.now(UTC)
        row.safe_error = None
        await session.commit()
        dispatch_started = True

        result = (
            await service.send_image_message(
                clinic_id, patient.whatsapp_phone, row.message, image
            )
            if image
            else await service.send_message(clinic_id, patient.whatsapp_phone, row.message)
        )
        row.status = WhatsAppOutreachStatus.SENT
        row.provider_message_id = result.get("message_id")
        row.sent_at = datetime.now(UTC)
        row.retry_at = None
        row.safe_error = None
    except WhatsAppServiceError as exc:
        if dispatch_started:
            row.status = WhatsAppOutreachStatus.SEND_UNKNOWN
            row.safe_error = "SEND_OUTCOME_UNKNOWN"
            row.failed_at = datetime.now(UTC)
        elif exc.code in PERMANENT_ERRORS:
            _mark_permanent_failure(row, exc.code)
        elif exc.code == "WHATSAPP_CONNECTION_REQUIRED":
            _schedule_retry(row, settings.whatsapp_connection_retry_seconds, exc.code)
        elif row.attempt_count < settings.whatsapp_max_attempts:
            delay_seconds = 60 * (2 ** min(row.attempt_count, 6))
            _schedule_retry(row, delay_seconds, exc.code)
        else:
            _mark_permanent_failure(row, exc.code)
    await session.commit()
    return True


async def run() -> None:
    settings = get_settings()
    worker_id = os.getenv("WHATSAPP_WORKER_ID", f"{socket.gethostname()}-{uuid.uuid4().hex[:12]}")
    while True:
        did_work = False
        async with ControlSession() as control:
            clinics = (
                await control.scalars(
                    select(ClinicRegistry).where(ClinicRegistry.is_active.is_(True))
                )
            ).all()
            for registry in clinics:
                clinic = await resolver.by_id(control, registry.id)
                async with resolver.session_factory(clinic)() as session:
                    did_work = await process_due(session, clinic.id, worker_id) or did_work
        if not did_work:
            await asyncio.sleep(settings.whatsapp_worker_poll_seconds)


if __name__ == "__main__":
    asyncio.run(run())
