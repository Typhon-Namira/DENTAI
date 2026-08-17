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
    AIAnalysis, DentalFinding, Patient, WhatsAppOutreach, WhatsAppOutreachStatus, XRay,
)
from app.database.sessions import ControlSession
from app.outreach.images import finding_crop
from app.outreach.whatsapp_client import WhatsAppServiceClient, WhatsAppServiceError


async def claim_due(session, worker_id: str):
    now = datetime.now(UTC)
    row = await session.scalar(
        select(WhatsAppOutreach).where(
            WhatsAppOutreach.status.in_([
                WhatsAppOutreachStatus.SCHEDULED, WhatsAppOutreachStatus.QUEUED
            ]),
            WhatsAppOutreach.scheduled_send_at <= now,
            or_(WhatsAppOutreach.retry_at.is_(None), WhatsAppOutreach.retry_at <= now),
        ).order_by(WhatsAppOutreach.scheduled_send_at)
        .with_for_update(skip_locked=True).limit(1)
    )
    if row:
        row.status = WhatsAppOutreachStatus.SENDING
        row.worker_id = worker_id
        row.claimed_at = now
        row.attempt_count += 1
        await session.commit()
    return row


async def process_due(session, clinic_id, worker_id: str,
                      service: WhatsAppServiceClient | None = None) -> bool:
    row = await claim_due(session, worker_id)
    if row is None:
        return False
    service = service or WhatsAppServiceClient()
    settings = get_settings()
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
        if row.include_image and row.finding_id:
            finding = await session.get(DentalFinding, row.finding_id)
            analysis = await session.get(AIAnalysis, row.analysis_id)
            xray = await session.get(XRay, analysis.xray_id) if analysis else None
            image = await finding_crop(xray, finding) if xray and finding else None
            result = (
                await service.send_image_message(
                    clinic_id, patient.whatsapp_phone, row.message, image
                ) if image else
                await service.send_message(clinic_id, patient.whatsapp_phone, row.message)
            )
        else:
            result = await service.send_message(
                clinic_id, patient.whatsapp_phone, row.message
            )
        row.status = WhatsAppOutreachStatus.SENT
        row.provider_message_id = result.get("message_id")
        row.sent_at = datetime.now(UTC)
        row.safe_error = None
    except WhatsAppServiceError as exc:
        row.safe_error = exc.code
        if exc.code == "WHATSAPP_CONNECTION_REQUIRED":
            row.status = WhatsAppOutreachStatus.SCHEDULED
            row.retry_at = datetime.now(UTC) + timedelta(
                seconds=settings.whatsapp_connection_retry_seconds
            )
        elif row.attempt_count < settings.whatsapp_max_attempts:
            row.status = WhatsAppOutreachStatus.SCHEDULED
            row.retry_at = datetime.now(UTC) + timedelta(
                minutes=2 ** min(row.attempt_count, 6)
            )
        else:
            row.status = WhatsAppOutreachStatus.FAILED
            row.failed_at = datetime.now(UTC)
    await session.commit()
    return True


async def run() -> None:
    settings = get_settings()
    worker_id = os.getenv(
        "WHATSAPP_WORKER_ID", f"{socket.gethostname()}-{uuid.uuid4().hex[:12]}"
    )
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
                    did_work = (
                        await process_due(session, clinic.id, worker_id) or did_work
                    )
        if not did_work:
            await asyncio.sleep(settings.whatsapp_worker_poll_seconds)


if __name__ == "__main__":
    asyncio.run(run())
