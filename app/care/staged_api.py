import uuid
from datetime import UTC, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import audit
from app.auth.dependencies import AuthContext, authorized_patient, roles
from app.care.conversation_flow import (
    APPOINTMENT_CONFIRMED,
    appointment_confirmed_message,
    process_staged_inbound_message,
)
from app.care.models import CareAppointment, CareConversation, CareConversationMessage, CarePlanItem
from app.clinic_resolution.service import resolver
from app.common.serialization import model_dict
from app.core.config import get_settings
from app.core.errors import AppError
from app.database.models import Patient, Role
from app.database.sessions import control_session
from app.outreach.whatsapp_client import WhatsAppServiceClient, WhatsAppServiceError

router = APIRouter(prefix="/care", tags=["care-staged-booking"])


class InboundWhatsAppPayload(dict):
    pass


async def _appointment(ctx: AuthContext, appointment_id: uuid.UUID) -> CareAppointment:
    row = await ctx.session.get(CareAppointment, appointment_id)
    if not row:
        raise AppError("APPOINTMENT_NOT_FOUND", "Appointment was not found.", 404)
    if ctx.user.role != Role.DIRECTOR and row.branch_id not in ctx.branch_ids:
        raise AppError("BRANCH_NOT_AUTHORIZED", "Appointment is outside your scope.", 403)
    await authorized_patient(ctx, row.patient_id)
    return row


@router.post("/internal/whatsapp/inbound")
async def staged_inbound_whatsapp(
    body: dict,
    control: Annotated[AsyncSession, Depends(control_session)],
    authorization: Annotated[str | None, Header()] = None,
):
    token = get_settings().whatsapp_service_token
    if not token or authorization != f"Bearer {token}":
        raise AppError("AUTH_REQUIRED", "Internal authentication is required.", 401)

    account_id = str(body.get("account_id") or "")
    phone = str(body.get("phone") or "")
    text = str(body.get("text") or "").strip()
    message_id = body.get("message_id")
    if not text:
        raise AppError("MESSAGE_REQUIRED", "Inbound message text is required.", 422)
    if not account_id.startswith("clinic_"):
        raise AppError("CLINIC_CONTEXT_INVALID", "Clinic context is invalid.", 422)
    try:
        clinic_id = uuid.UUID(hex=account_id.removeprefix("clinic_"))
    except ValueError as exc:
        raise AppError("CLINIC_CONTEXT_INVALID", "Clinic context is invalid.", 422) from exc

    clinic = await resolver.by_id(control, clinic_id)
    async with resolver.session_factory(clinic)() as session:
        result = await process_staged_inbound_message(
            session,
            clinic_id=clinic.id,
            clinic_name=clinic.name,
            phone=phone,
            text=text,
            provider_message_id=str(message_id) if message_id else None,
        )
        await session.commit()
        return result


@router.post("/appointments/{appointment_id}/approve")
async def approve_staged_appointment(
    appointment_id: uuid.UUID,
    ctx: Annotated[
        AuthContext,
        Depends(roles(Role.DIRECTOR, Role.MANAGER, Role.DOCTOR)),
    ],
):
    row = await _appointment(ctx, appointment_id)
    if row.status != "PROPOSED":
        raise AppError("INVALID_APPOINTMENT_STATE", "Appointment is not awaiting approval.", 409)
    if not row.patient_confirmed_at:
        raise AppError(
            "PATIENT_CONFIRMATION_REQUIRED",
            "The patient must confirm the proposed time before doctor approval.",
            409,
        )

    collision = await ctx.session.scalar(
        select(CareAppointment.id)
        .where(
            CareAppointment.id != row.id,
            CareAppointment.branch_id == row.branch_id,
            CareAppointment.doctor_id == row.doctor_id,
            CareAppointment.status == "APPROVED",
            CareAppointment.starts_at < row.ends_at,
            CareAppointment.ends_at > row.starts_at,
        )
        .with_for_update()
    )
    if collision:
        raise AppError("APPOINTMENT_COLLISION", "The selected time is no longer available.", 409)

    patient = await ctx.session.get(Patient, row.patient_id)
    if not patient or not (patient.whatsapp_phone or patient.phone):
        raise AppError("PATIENT_PHONE_REQUIRED", "Patient WhatsApp number is required.", 422)

    conversation = (
        await ctx.session.get(CareConversation, row.conversation_id)
        if row.conversation_id
        else None
    )
    language = conversation.language if conversation else "en"
    message = appointment_confirmed_message(
        language,
        row.starts_at,
        row.timezone,
        ctx.clinic.name,
    )
    phone = patient.whatsapp_phone or patient.phone
    if phone is None:
        raise AppError("PATIENT_PHONE_REQUIRED", "Patient WhatsApp number is required.", 422)

    try:
        sent = await WhatsAppServiceClient().send_message(ctx.clinic.id, phone, message)
    except WhatsAppServiceError as exc:
        row.notification_status = "FAILED"
        row.notification_attempt_count += 1
        row.notification_failed_at = datetime.now(UTC)
        row.notification_error = "Provider request failed"
        await audit(
            ctx.session,
            ctx.user,
            "APPOINTMENT_NOTIFICATION_FAILED",
            "CareAppointment",
            row.id,
            row.branch_id,
        )
        await ctx.session.commit()
        raise AppError(
            "APPOINTMENT_NOTIFICATION_FAILED",
            "Appointment remains pending because the patient could not be notified.",
            503,
        ) from exc

    now = datetime.now(UTC)
    row.status = "APPROVED"
    row.notification_status = "SENT"
    row.notification_attempt_count += 1
    row.notification_provider_id = sent.get("message_id")
    row.notification_sent_at = now
    row.notification_failed_at = None
    row.notification_error = None

    if conversation:
        context = dict(conversation.booking_context or {})
        context.update(
            {
                "stage": APPOINTMENT_CONFIRMED,
                "appointment_id": str(row.id),
                "doctor_approved_at": now.isoformat(),
                "confirmed_slot": row.starts_at.isoformat(),
            }
        )
        conversation.booking_context = context
        conversation.last_message_at = now
        conversation.summary = (
            "Appointment confirmed by patient and doctor; final WhatsApp confirmation sent."
        )
        ctx.session.add(
            CareConversationMessage(
                conversation_id=conversation.id,
                care_plan_item_id=row.care_plan_item_id,
                direction="OUT",
                body=message,
                language=language,
                status="SENT",
                sent_at=now,
                attempt_count=1,
                provider_message_id=sent.get("message_id"),
                message_metadata={
                    "kind": "appointment_final_confirmation",
                    "stage": APPOINTMENT_CONFIRMED,
                    "appointment_id": str(row.id),
                    "confirmed_slot": row.starts_at.isoformat(),
                    "timezone": row.timezone,
                },
            )
        )

    if row.care_plan_item_id:
        item = await ctx.session.get(CarePlanItem, row.care_plan_item_id)
        if item:
            item.status = "BOOKED"

    await audit(
        ctx.session,
        ctx.user,
        "APPOINTMENT_APPROVED",
        "CareAppointment",
        row.id,
        row.branch_id,
        {
            "patient_confirmed_at": row.patient_confirmed_at.isoformat()
            if row.patient_confirmed_at
            else None,
            "confirmed_local_time": row.starts_at.astimezone(ZoneInfo(row.timezone)).isoformat(),
        },
    )
    try:
        await ctx.session.commit()
    except IntegrityError as exc:
        await ctx.session.rollback()
        raise AppError(
            "APPOINTMENT_COLLISION",
            "The selected time was booked concurrently.",
            409,
        ) from exc
    return model_dict(row)
