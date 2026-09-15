import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AuthContext, roles
from app.care.conversation_flow import APPOINTMENT_CONFIRMED, _find_patient
from app.care.conversation_runtime import process_staged_inbound_message
from app.care.models import CareAppointment, CareConversation, CareConversationMessage
from app.care.staged_api import approve_staged_appointment
from app.clinic_resolution.service import resolver
from app.core.config import get_settings
from app.core.errors import AppError
from app.database.models import Role
from app.database.sessions import control_session

router = APIRouter(prefix="/care", tags=["care-lifecycle-guard"])

_OUTREACH_KINDS = {"scheduled_sequential_followup", "finding_followup"}


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _conversation_stamp(conversation: CareConversation) -> datetime:
    return (
        _utc(conversation.last_message_at)
        or _utc(conversation.updated_at)
        or _utc(conversation.created_at)
        or datetime.min.replace(tzinfo=UTC)
    )


def _mark_waiting_for_next_tooth(
    conversation: CareConversation,
    *,
    locked_at: datetime,
    appointment_id: uuid.UUID | None = None,
    confirmed_slot: datetime | None = None,
) -> None:
    context = dict(conversation.booking_context or {})
    context.update(
        {
            "stage": APPOINTMENT_CONFIRMED,
            "patient_ai_locked_at": locked_at.isoformat(),
        }
    )
    if appointment_id is not None:
        context["appointment_id"] = str(appointment_id)
    if confirmed_slot is not None:
        context["confirmed_slot"] = confirmed_slot.isoformat()
    conversation.booking_context = context
    conversation.status = "WAITING_NEXT_TOOTH"
    conversation.summary = (
        "Appointment confirmed; AI is inactive until the next tooth outreach is actually sent."
    )


async def _has_real_outreach_after(
    session: AsyncSession,
    *,
    conversation_id: uuid.UUID,
    locked_at: datetime,
) -> bool:
    messages = (
        await session.scalars(
            select(CareConversationMessage)
            .where(
                CareConversationMessage.conversation_id == conversation_id,
                CareConversationMessage.direction == "OUT",
            )
            .order_by(CareConversationMessage.created_at.desc())
        )
    ).all()
    for message in messages:
        metadata = message.message_metadata or {}
        if metadata.get("kind") not in _OUTREACH_KINDS:
            continue
        sent_at = _utc(message.sent_at) or _utc(message.created_at)
        if sent_at and sent_at > locked_at:
            return True
    return False


async def _deactivate_active_patient_conversations(
    session: AsyncSession,
    *,
    patient_id: uuid.UUID,
    locked_at: datetime,
    appointment_id: uuid.UUID | None = None,
    confirmed_slot: datetime | None = None,
) -> int:
    active = (
        await session.scalars(
            select(CareConversation).where(
                CareConversation.patient_id == patient_id,
                CareConversation.status == "ACTIVE",
            )
        )
    ).all()
    for conversation in active:
        _mark_waiting_for_next_tooth(
            conversation,
            locked_at=locked_at,
            appointment_id=appointment_id,
            confirmed_slot=confirmed_slot,
        )
    return len(active)


async def _enforce_post_confirmation_patient_lock(
    session: AsyncSession,
    *,
    phone: str,
) -> bool:
    """Return True when inbound AI handling must remain blocked for this patient."""
    patient = await _find_patient(session, phone)
    if not patient:
        return False

    conversations = (
        await session.scalars(
            select(CareConversation).where(CareConversation.patient_id == patient.id)
        )
    ).all()
    locks = [
        conversation
        for conversation in conversations
        if conversation.status == "WAITING_NEXT_TOOTH"
        and (conversation.booking_context or {}).get("stage") == APPOINTMENT_CONFIRMED
    ]
    if not locks:
        return False

    latest_lock = max(locks, key=_conversation_stamp)
    locked_at = _conversation_stamp(latest_lock)
    active = [conversation for conversation in conversations if conversation.status == "ACTIVE"]
    if not active:
        return True

    valid_active: list[CareConversation] = []
    for conversation in active:
        if await _has_real_outreach_after(
            session,
            conversation_id=conversation.id,
            locked_at=locked_at,
        ):
            valid_active.append(conversation)

    if valid_active:
        keep = max(valid_active, key=_conversation_stamp)
        for conversation in active:
            if conversation.id != keep.id:
                _mark_waiting_for_next_tooth(conversation, locked_at=locked_at)
        return False

    for conversation in active:
        _mark_waiting_for_next_tooth(conversation, locked_at=locked_at)
    return True


@router.post("/internal/whatsapp/inbound")
async def guarded_staged_inbound_whatsapp(
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
        locked = await _enforce_post_confirmation_patient_lock(session, phone=phone)
        if locked:
            await session.commit()
            return {
                "handled": False,
                "reason": "conversation_locked_after_confirmation",
            }
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
async def guarded_approve_staged_appointment(
    appointment_id: uuid.UUID,
    ctx: Annotated[
        AuthContext,
        Depends(roles(Role.DIRECTOR, Role.MANAGER, Role.DOCTOR)),
    ],
):
    result = await approve_staged_appointment(appointment_id, ctx)
    appointment = await ctx.session.get(CareAppointment, appointment_id)
    if not appointment:
        return result

    locked_at = _utc(appointment.notification_sent_at) or datetime.now(UTC)
    await _deactivate_active_patient_conversations(
        ctx.session,
        patient_id=appointment.patient_id,
        locked_at=locked_at,
        appointment_id=appointment.id,
        confirmed_slot=appointment.starts_at,
    )
    await ctx.session.commit()
    return result
