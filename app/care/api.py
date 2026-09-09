import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import audit
from app.auth.dependencies import AuthContext, authorized_patient, current_context, roles
from app.care.language import language_for_phone
from app.care.models import (
    CareAppointment,
    CareAvailabilityException,
    CareConversation,
    CareConversationMessage,
    CarePlan,
    CarePlanItem,
)
from app.care.service import (
    approve_care_plan,
    available_slots,
    process_inbound_message,
    settings_for_branch,
)
from app.clinic_resolution.service import resolver
from app.common.serialization import model_dict
from app.core.config import get_settings
from app.core.errors import AppError
from app.database.models import FollowUp, Patient, PatientDoctorAssignment, Role
from app.database.sessions import control_session
from app.outreach.whatsapp_client import WhatsAppServiceClient, WhatsAppServiceError

router = APIRouter(prefix="/care", tags=["care"])


class CareSettingsUpdate(BaseModel):
    timezone: str = "Asia/Yerevan"
    working_days: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5])
    day_start: str = Field(default="09:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    day_end: str = Field(default="18:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    appointment_minutes: int = Field(default=30, ge=10, le=240)
    slot_interval_minutes: int = Field(default=30, ge=5, le=240)
    min_booking_notice_minutes: int = Field(default=60, ge=0, le=10080)
    booking_horizon_days: int = Field(default=30, ge=1, le=365)
    buffer_minutes: int = Field(default=0, ge=0, le=120)
    preferred_times: list = Field(default_factory=list)
    blocked_windows: list = Field(default_factory=list)
    auto_followup_enabled: bool = True
    auto_outreach_after_review: bool = True
    attach_tooth_image: bool = True
    default_language: str = "en"
    booking_instructions: str | None = Field(default=None, max_length=4000)


class RescheduleRequest(BaseModel):
    preferred_start: datetime | None = None
    doctor_note: str | None = Field(default=None, max_length=2000)


class CarePlanItemUpdate(BaseModel):
    target_followup_at: datetime | None = None
    recommended_window: str | None = Field(default=None, min_length=1, max_length=80)
    rationale: str | None = Field(default=None, min_length=1, max_length=4000)
    message_preview: str | None = Field(default=None, max_length=10000)


class InboundWhatsApp(BaseModel):
    account_id: str
    phone: str
    text: str = Field(min_length=1, max_length=10000)
    message_id: str | None = None


class TransitionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class AvailabilityExceptionRequest(BaseModel):
    starts_at: datetime
    ends_at: datetime
    doctor_id: uuid.UUID | None = None
    kind: str = "UNAVAILABLE"
    reason: str | None = Field(default=None, max_length=500)


class MessageStatusRequest(BaseModel):
    account_id: str
    provider_message_id: str
    status: str
    error: str | None = Field(default=None, max_length=2000)


def _branch_allowed(ctx: AuthContext, branch_id: uuid.UUID) -> bool:
    return ctx.user.role == Role.DIRECTOR or branch_id in ctx.branch_ids


def _utc(value: datetime) -> datetime:
    """Normalize database datetimes (including SQLite's naive values) to UTC."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


async def _care_plan(ctx: AuthContext, plan_id: uuid.UUID) -> CarePlan:
    plan = await ctx.session.get(CarePlan, plan_id)
    if not plan:
        raise AppError("CARE_PLAN_NOT_FOUND", "Care plan was not found.", 404)
    if not _branch_allowed(ctx, plan.branch_id):
        raise AppError("BRANCH_NOT_AUTHORIZED", "Care plan is outside your scope.", 403)
    await authorized_patient(ctx, plan.patient_id)
    return plan


async def _appointment(ctx: AuthContext, appointment_id: uuid.UUID) -> CareAppointment:
    row = await ctx.session.get(CareAppointment, appointment_id)
    if not row:
        raise AppError("APPOINTMENT_NOT_FOUND", "Appointment was not found.", 404)
    if not _branch_allowed(ctx, row.branch_id):
        raise AppError("BRANCH_NOT_AUTHORIZED", "Appointment is outside your scope.", 403)
    await authorized_patient(ctx, row.patient_id)
    return row


@router.get("/dashboard")
async def care_dashboard(ctx: Annotated[AuthContext, Depends(current_context)]):
    plan_query = select(CarePlan)
    appointment_query = select(CareAppointment)
    conversation_query = select(CareConversation)
    if ctx.user.role != Role.DIRECTOR:
        plan_query = plan_query.where(CarePlan.branch_id.in_(ctx.branch_ids))
        appointment_query = appointment_query.where(CareAppointment.branch_id.in_(ctx.branch_ids))
        conversation_query = conversation_query.where(
            CareConversation.branch_id.in_(ctx.branch_ids)
        )
    if ctx.user.role == Role.DOCTOR:
        patient_scope = select(PatientDoctorAssignment.patient_id).where(
            PatientDoctorAssignment.doctor_id == ctx.user.id,
            PatientDoctorAssignment.active.is_(True),
        )
        plan_query = plan_query.where(CarePlan.patient_id.in_(patient_scope))
        appointment_query = appointment_query.where(CareAppointment.patient_id.in_(patient_scope))
        conversation_query = conversation_query.where(
            CareConversation.patient_id.in_(patient_scope)
        )
    plans = (await ctx.session.scalars(plan_query.order_by(CarePlan.updated_at.desc()))).all()
    appointments = (
        await ctx.session.scalars(appointment_query.order_by(CareAppointment.starts_at.asc()))
    ).all()
    conversations = (
        await ctx.session.scalars(
            conversation_query.order_by(CareConversation.last_message_at.desc())
        )
    ).all()
    now = datetime.now(UTC)
    items = (
        (
            await ctx.session.scalars(
                select(CarePlanItem).where(CarePlanItem.care_plan_id.in_([p.id for p in plans]))
            )
        ).all()
        if plans
        else []
    )
    alerts: list[dict[str, str]] = []
    alerts.extend(
        {"kind": "PLAN_APPROVAL", "entity_id": str(p.id), "patient_id": str(p.patient_id)}
        for p in plans
        if p.status == "PENDING_APPROVAL"
    )
    alerts.extend(
        {"kind": "APPOINTMENT_APPROVAL", "entity_id": str(a.id), "patient_id": str(a.patient_id)}
        for a in appointments
        if a.status == "PROPOSED"
    )
    alerts.extend(
        {"kind": "NOTIFICATION_FAILED", "entity_id": str(a.id), "patient_id": str(a.patient_id)}
        for a in appointments
        if a.notification_status == "FAILED"
    )
    return {
        "appointments_awaiting_approval": sum(a.status == "PROPOSED" for a in appointments),
        "active_care_plans": sum(p.status == "ACTIVE" for p in plans),
        "active_conversations": sum(c.status == "ACTIVE" for c in conversations),
        "followups_due": sum(
            i.status not in {"COMPLETED", "REJECTED"} and _utc(i.target_followup_at) <= now
            for i in items
        ),
        "notification_count": len(alerts),
        "alerts": alerts[:20],
        "next_clinical_actions": alerts[:10],
        "upcoming_appointments": [
            model_dict(a)
            for a in appointments
            if _utc(a.starts_at) >= now and a.status in {"APPROVED", "PROPOSED"}
        ][:10],
        "generated_at": now,
    }


@router.get("/settings/{branch_id}")
async def get_care_settings(
    branch_id: uuid.UUID, ctx: Annotated[AuthContext, Depends(current_context)]
):
    if not _branch_allowed(ctx, branch_id):
        raise AppError("BRANCH_NOT_AUTHORIZED", "Branch is outside your scope.", 403)
    row = await settings_for_branch(ctx.session, branch_id)
    await ctx.session.commit()
    return model_dict(row)


@router.put("/settings/{branch_id}")
async def put_care_settings(
    branch_id: uuid.UUID,
    body: CareSettingsUpdate,
    ctx: Annotated[
        AuthContext,
        Depends(roles(Role.DIRECTOR, Role.MANAGER, Role.DOCTOR)),
    ],
):
    if not _branch_allowed(ctx, branch_id):
        raise AppError("BRANCH_NOT_AUTHORIZED", "Branch is outside your scope.", 403)
    try:
        ZoneInfo(body.timezone)
    except ZoneInfoNotFoundError as exc:
        raise AppError("INVALID_TIMEZONE", "Timezone must be a valid IANA timezone.", 422) from exc
    if not body.working_days or any(day < 0 or day > 6 for day in body.working_days):
        raise AppError("INVALID_WORKING_DAYS", "Working days must contain values from 0 to 6.", 422)
    if body.day_start >= body.day_end:
        raise AppError("INVALID_WORKING_HOURS", "Day end must be after day start.", 422)
    row = await settings_for_branch(ctx.session, branch_id)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    await ctx.session.commit()
    return model_dict(row)


@router.get("/plans")
async def list_care_plans(
    ctx: Annotated[AuthContext, Depends(current_context)],
    patient_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=200),
):
    query = select(CarePlan).order_by(CarePlan.created_at.desc()).limit(limit)
    if patient_id:
        query = query.where(CarePlan.patient_id == patient_id)
    if ctx.user.role != Role.DIRECTOR:
        query = query.where(CarePlan.branch_id.in_(ctx.branch_ids))
    if ctx.user.role == Role.DOCTOR:
        query = query.where(
            CarePlan.patient_id.in_(
                select(PatientDoctorAssignment.patient_id).where(
                    PatientDoctorAssignment.doctor_id == ctx.user.id
                )
            )
        )
    plans = (await ctx.session.scalars(query)).all()
    result = []
    for plan in plans:
        items = (
            await ctx.session.scalars(
                select(CarePlanItem).where(CarePlanItem.care_plan_id == plan.id)
            )
        ).all()
        result.append({**model_dict(plan), "items": [model_dict(item) for item in items]})
    return result


@router.patch("/plans/{plan_id}/items/{item_id}")
async def update_plan_item(
    plan_id: uuid.UUID,
    item_id: uuid.UUID,
    body: CarePlanItemUpdate,
    ctx: Annotated[
        AuthContext,
        Depends(roles(Role.DIRECTOR, Role.MANAGER, Role.DOCTOR)),
    ],
):
    plan = await ctx.session.get(CarePlan, plan_id)
    if not plan:
        raise AppError("CARE_PLAN_NOT_FOUND", "Care plan was not found.", 404)
    if not _branch_allowed(ctx, plan.branch_id):
        raise AppError("BRANCH_NOT_AUTHORIZED", "Care plan is outside your scope.", 403)
    await authorized_patient(ctx, plan.patient_id)
    if plan.status != "PENDING_APPROVAL":
        raise AppError("CARE_PLAN_LOCKED", "Only a pending plan can be edited.", 409)
    item = await ctx.session.get(CarePlanItem, item_id)
    if not item or item.care_plan_id != plan.id:
        raise AppError("CARE_PLAN_ITEM_NOT_FOUND", "Care plan item was not found.", 404)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await ctx.session.commit()
    return model_dict(item)


@router.post("/plans/{plan_id}/approve")
async def approve_plan(
    plan_id: uuid.UUID,
    ctx: Annotated[
        AuthContext,
        Depends(roles(Role.DIRECTOR, Role.MANAGER, Role.DOCTOR)),
    ],
):
    plan = await _care_plan(ctx, plan_id)
    if plan.status != "PENDING_APPROVAL":
        raise AppError("INVALID_CARE_PLAN_STATE", "Care plan is not awaiting approval.", 409)
    try:
        await approve_care_plan(
            ctx.session,
            clinic_id=ctx.clinic.id,
            clinic_name=ctx.clinic.name,
            plan=plan,
        )
        plan.approved_by = ctx.user.id
        plan.approved_at = datetime.now(UTC)
        await audit(
            ctx.session, ctx.user, "CARE_PLAN_APPROVED", "CarePlan", plan.id, plan.branch_id
        )
        await ctx.session.commit()
    except WhatsAppServiceError as exc:
        await ctx.session.rollback()
        raise AppError(
            "CARE_OUTREACH_FAILED",
            "The plan was not activated because patient outreach could not be started.",
            503,
        ) from exc
    return model_dict(plan)


@router.post("/plans/{plan_id}/{action}")
async def transition_plan(
    plan_id: uuid.UUID,
    action: str,
    body: TransitionRequest,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER, Role.DOCTOR))],
):
    plan = await _care_plan(ctx, plan_id)
    action = action.lower()
    transitions = {
        "reject": ({"READY_FOR_REVIEW", "PENDING_APPROVAL"}, "REJECTED"),
        "pause": ({"ACTIVE"}, "PAUSED"),
        "resume": ({"PAUSED"}, "ACTIVE"),
        "complete": ({"ACTIVE", "PAUSED"}, "COMPLETED"),
    }
    if action not in transitions:
        raise AppError("INVALID_PLAN_ACTION", "Care plan action is invalid.", 404)
    allowed, target = transitions[action]
    if plan.status == target:
        return model_dict(plan)
    if plan.status not in allowed:
        raise AppError("INVALID_CARE_PLAN_STATE", f"Cannot {action} a {plan.status} plan.", 409)
    plan.status = target
    now = datetime.now(UTC)
    if target == "REJECTED":
        plan.rejected_by, plan.rejected_at = ctx.user.id, now
    elif target == "PAUSED":
        plan.paused_at = now
    elif target == "ACTIVE":
        plan.paused_at = None
    elif target == "COMPLETED":
        plan.completed_at = now
    items = (
        await ctx.session.scalars(select(CarePlanItem).where(CarePlanItem.care_plan_id == plan.id))
    ).all()
    if target == "COMPLETED":
        for item in items:
            if item.status != "REJECTED":
                item.status = "COMPLETED"
        followups = (
            await ctx.session.scalars(
                select(FollowUp).where(
                    FollowUp.patient_id == plan.patient_id,
                    FollowUp.status.in_(["SCHEDULED", "DUE"]),
                )
            )
        ).all()
        for followup in followups:
            followup.status = "COMPLETED"
            followup.completed_at = now
    conversations = (
        await ctx.session.scalars(
            select(CareConversation).where(CareConversation.care_plan_id == plan.id)
        )
    ).all()
    for conversation in conversations:
        if target == "PAUSED":
            conversation.status = "PAUSED"
        elif target == "ACTIVE" and conversation.status == "PAUSED":
            conversation.status = "ACTIVE"
        elif target in {"COMPLETED", "REJECTED"}:
            conversation.status = "CLOSED"
    await audit(
        ctx.session,
        ctx.user,
        f"CARE_PLAN_{target}",
        "CarePlan",
        plan.id,
        plan.branch_id,
        {"reason": body.reason},
    )
    await ctx.session.commit()
    return model_dict(plan)


@router.post("/plans/{plan_id}/items/{item_id}/complete")
async def complete_plan_item(
    plan_id: uuid.UUID,
    item_id: uuid.UUID,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER, Role.DOCTOR))],
):
    plan = await _care_plan(ctx, plan_id)
    if plan.status not in {"ACTIVE", "PAUSED"}:
        raise AppError(
            "INVALID_CARE_PLAN_STATE", "Only active or paused plan steps can be completed.", 409
        )
    item = await ctx.session.get(CarePlanItem, item_id)
    if not item or item.care_plan_id != plan.id:
        raise AppError("CARE_PLAN_ITEM_NOT_FOUND", "Care plan item was not found.", 404)
    if item.status != "COMPLETED":
        item.status = "COMPLETED"
        await audit(
            ctx.session,
            ctx.user,
            "CARE_PLAN_STEP_COMPLETED",
            "CarePlanItem",
            item.id,
            plan.branch_id,
        )
        await ctx.session.commit()
    return model_dict(item)


@router.get("/appointments")
async def appointments(
    ctx: Annotated[AuthContext, Depends(current_context)],
    start: datetime | None = None,
    end: datetime | None = None,
    status: str | None = None,
    patient_id: uuid.UUID | None = None,
):
    start = start or datetime.now(UTC) - timedelta(days=1)
    end = end or datetime.now(UTC) + timedelta(days=14)
    query = (
        select(CareAppointment)
        .where(
            CareAppointment.starts_at >= start,
            CareAppointment.starts_at <= end,
        )
        .order_by(CareAppointment.starts_at.asc())
    )
    if ctx.user.role != Role.DIRECTOR:
        query = query.where(CareAppointment.branch_id.in_(ctx.branch_ids))
    if ctx.user.role == Role.DOCTOR:
        query = query.where(
            CareAppointment.patient_id.in_(
                select(PatientDoctorAssignment.patient_id).where(
                    PatientDoctorAssignment.doctor_id == ctx.user.id
                )
            )
        )
    if status:
        query = query.where(CareAppointment.status == status.upper())
    if patient_id:
        query = query.where(CareAppointment.patient_id == patient_id)
    rows = (await ctx.session.scalars(query)).all()
    patient_ids = {row.patient_id for row in rows}
    patients = (
        {
            p.id: p
            for p in (
                await ctx.session.scalars(select(Patient).where(Patient.id.in_(patient_ids)))
            ).all()
        }
        if patient_ids
        else {}
    )
    return [
        {
            **model_dict(row),
            "patient": model_dict(patients[row.patient_id]) if row.patient_id in patients else None,
        }
        for row in rows
    ]


@router.post("/appointments/{appointment_id}/reschedule")
async def request_reschedule(
    appointment_id: uuid.UUID,
    body: RescheduleRequest,
    ctx: Annotated[AuthContext, Depends(current_context)],
):
    row = await _appointment(ctx, appointment_id)
    if row.status not in {"PROPOSED", "APPROVED", "RESCHEDULE_REQUESTED"}:
        raise AppError("INVALID_APPOINTMENT_STATE", "This appointment cannot be rescheduled.", 409)
    patient = await ctx.session.get(Patient, row.patient_id)
    if not patient or not (patient.whatsapp_phone or patient.phone):
        raise AppError("PATIENT_PHONE_REQUIRED", "Patient WhatsApp number is required.", 422)
    row.status = "RESCHEDULE_REQUESTED"
    row.doctor_note = body.doctor_note
    row.reschedule_count += 1
    phone = patient.whatsapp_phone or patient.phone
    if phone is None:
        raise AppError("PATIENT_PHONE_REQUIRED", "Patient WhatsApp number is required.", 422)
    language = language_for_phone(phone, "en")
    if body.preferred_start:
        proposed = body.preferred_start.strftime("%Y-%m-%d %H:%M")
        if language == "hy":
            message = f"Կլինիկան խնդրել է փոխել ձեր ստուգման ժամը։ Առաջարկվող նոր ժամը՝ {proposed}։ Արդյո՞ք հարմար է։ Եթե ոչ, գրեք ձեզ հարմար օրը կամ ժամը։"
        elif language == "ru":
            message = f"Клиника просит перенести время осмотра. Предлагаемое новое время: {proposed}. Вам удобно? Если нет, напишите предпочтительный день или время."
        else:
            message = f"The clinic would like to reschedule your check-up. Proposed new time: {proposed}. Does this work for you? If not, tell me your preferred day or time."
    else:
        message = "The clinic would like to reschedule your check-up. Please tell me which day or time works best for you."
    sent = await WhatsAppServiceClient().send_message(ctx.clinic.id, phone, message)
    if row.conversation_id:
        ctx.session.add(
            CareConversationMessage(
                conversation_id=row.conversation_id,
                care_plan_item_id=row.care_plan_item_id,
                direction="OUT",
                body=message,
                language=language,
                status="SENT",
                sent_at=datetime.now(UTC),
                attempt_count=1,
                provider_message_id=sent.get("message_id"),
                message_metadata={
                    "kind": "doctor_reschedule",
                    "preferred_start": body.preferred_start.isoformat()
                    if body.preferred_start
                    else None,
                },
            )
        )
    await audit(
        ctx.session,
        ctx.user,
        "APPOINTMENT_RESCHEDULE_REQUESTED",
        "CareAppointment",
        row.id,
        row.branch_id,
    )
    await ctx.session.commit()
    return model_dict(row)


@router.post("/appointments/{appointment_id}/approve")
async def approve_appointment(
    appointment_id: uuid.UUID,
    ctx: Annotated[
        AuthContext,
        Depends(roles(Role.DIRECTOR, Role.MANAGER, Role.DOCTOR)),
    ],
):
    row = await _appointment(ctx, appointment_id)
    if row.status != "PROPOSED":
        raise AppError("INVALID_APPOINTMENT_STATE", "Appointment is not awaiting approval.", 409)
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
    local_time = row.starts_at.astimezone(ZoneInfo(row.timezone)).strftime("%Y-%m-%d %H:%M")
    message = f"Your check-up is confirmed for {local_time} ({row.timezone})."
    phone = patient.whatsapp_phone or patient.phone
    if phone is None:
        raise AppError("PATIENT_PHONE_REQUIRED", "Patient WhatsApp number is required.", 422)
    try:
        sent = await WhatsAppServiceClient().send_message(
            ctx.clinic.id,
            phone,
            message,
        )
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
    row.status = "APPROVED"
    row.notification_status = "SENT"
    row.notification_attempt_count += 1
    row.notification_provider_id = sent.get("message_id")
    row.notification_sent_at = datetime.now(UTC)
    row.notification_failed_at = None
    row.notification_error = None
    if row.conversation_id:
        ctx.session.add(
            CareConversationMessage(
                conversation_id=row.conversation_id,
                care_plan_item_id=row.care_plan_item_id,
                direction="OUT",
                body=message,
                language="en",
                status="SENT",
                sent_at=datetime.now(UTC),
                attempt_count=1,
                provider_message_id=sent.get("message_id"),
                message_metadata={"kind": "appointment_approved"},
            )
        )
    if row.care_plan_item_id:
        item = await ctx.session.get(CarePlanItem, row.care_plan_item_id)
        if item:
            item.status = "BOOKED"
    await audit(
        ctx.session, ctx.user, "APPOINTMENT_APPROVED", "CareAppointment", row.id, row.branch_id
    )
    try:
        await ctx.session.commit()
    except IntegrityError as exc:
        await ctx.session.rollback()
        raise AppError(
            "APPOINTMENT_COLLISION", "The selected time was booked concurrently.", 409
        ) from exc
    return model_dict(row)


@router.post("/appointments/{appointment_id}/{action}")
async def transition_appointment(
    appointment_id: uuid.UUID,
    action: str,
    body: TransitionRequest,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER, Role.DOCTOR))],
):
    row = await _appointment(ctx, appointment_id)
    action = action.lower()
    transitions = {
        "reject": ({"PROPOSED", "RESCHEDULE_REQUESTED"}, "REJECTED"),
        "cancel": ({"PROPOSED", "APPROVED", "RESCHEDULE_REQUESTED"}, "CANCELLED"),
        "complete": ({"APPROVED"}, "COMPLETED"),
    }
    if action not in transitions:
        raise AppError("INVALID_APPOINTMENT_ACTION", "Appointment action is invalid.", 404)
    allowed, target = transitions[action]
    if row.status == target:
        return model_dict(row)
    if row.status not in allowed:
        raise AppError(
            "INVALID_APPOINTMENT_STATE", f"Cannot {action} a {row.status} appointment.", 409
        )
    row.status = target
    row.doctor_note = body.reason or row.doctor_note
    if row.care_plan_item_id:
        item = await ctx.session.get(CarePlanItem, row.care_plan_item_id)
        if item:
            if target == "COMPLETED":
                item.status = "COMPLETED"
            elif target in {"REJECTED", "CANCELLED"} and item.status == "BOOKED":
                item.status = "FOLLOWUP_READY"
    await audit(
        ctx.session,
        ctx.user,
        f"APPOINTMENT_{target}",
        "CareAppointment",
        row.id,
        row.branch_id,
        {"reason": body.reason},
    )
    await ctx.session.commit()
    return model_dict(row)


@router.get("/conversations")
async def conversations(
    ctx: Annotated[AuthContext, Depends(current_context)],
    limit: int = Query(default=100, ge=1, le=200),
):
    query = (
        select(CareConversation)
        .order_by(
            CareConversation.last_message_at.desc().nullslast(), CareConversation.created_at.desc()
        )
        .limit(limit)
    )
    if ctx.user.role != Role.DIRECTOR:
        query = query.where(CareConversation.branch_id.in_(ctx.branch_ids))
    if ctx.user.role == Role.DOCTOR:
        query = query.where(
            CareConversation.patient_id.in_(
                select(PatientDoctorAssignment.patient_id).where(
                    PatientDoctorAssignment.doctor_id == ctx.user.id
                )
            )
        )
    rows = (await ctx.session.scalars(query)).all()
    patient_ids = {row.patient_id for row in rows}
    patients = (
        {
            p.id: p
            for p in (
                await ctx.session.scalars(select(Patient).where(Patient.id.in_(patient_ids)))
            ).all()
        }
        if patient_ids
        else {}
    )
    result = []
    for row in rows:
        appointment = await ctx.session.scalar(
            select(CareAppointment)
            .where(CareAppointment.conversation_id == row.id)
            .order_by(CareAppointment.created_at.desc())
            .limit(1)
        )
        result.append(
            {
                **model_dict(row),
                "patient": model_dict(patients[row.patient_id])
                if row.patient_id in patients
                else None,
                "latest_appointment": model_dict(appointment) if appointment else None,
            }
        )
    return result


@router.get("/conversations/{conversation_id}/messages")
async def conversation_messages(
    conversation_id: uuid.UUID, ctx: Annotated[AuthContext, Depends(current_context)]
):
    conversation = await ctx.session.get(CareConversation, conversation_id)
    if not conversation:
        raise AppError("CONVERSATION_NOT_FOUND", "Conversation was not found.", 404)
    if not _branch_allowed(ctx, conversation.branch_id):
        raise AppError("BRANCH_NOT_AUTHORIZED", "Conversation is outside your scope.", 403)
    await authorized_patient(ctx, conversation.patient_id)
    rows = (
        await ctx.session.scalars(
            select(CareConversationMessage)
            .where(CareConversationMessage.conversation_id == conversation.id)
            .order_by(CareConversationMessage.created_at.asc())
        )
    ).all()
    return [model_dict(row) for row in rows]


@router.post("/conversations/{conversation_id}/messages/{message_id}/retry")
async def retry_conversation_message(
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER, Role.DOCTOR))],
):
    conversation = await ctx.session.get(CareConversation, conversation_id)
    if not conversation:
        raise AppError("CONVERSATION_NOT_FOUND", "Conversation was not found.", 404)
    if not _branch_allowed(ctx, conversation.branch_id):
        raise AppError("BRANCH_NOT_AUTHORIZED", "Conversation is outside your scope.", 403)
    await authorized_patient(ctx, conversation.patient_id)
    message = await ctx.session.get(CareConversationMessage, message_id)
    if not message or message.conversation_id != conversation.id:
        raise AppError("MESSAGE_NOT_FOUND", "Message was not found.", 404)
    if message.direction != "OUT" or message.status != "FAILED":
        raise AppError(
            "INVALID_MESSAGE_STATE", "Only failed outbound messages can be retried.", 409
        )
    message.status = "RETRYING"
    message.attempt_count += 1
    try:
        result = await WhatsAppServiceClient().send_message(
            ctx.clinic.id, conversation.whatsapp_phone, message.body
        )
    except WhatsAppServiceError as exc:
        message.status = "FAILED"
        message.failed_at = datetime.now(UTC)
        message.last_error = "Provider request failed"
        await ctx.session.commit()
        raise AppError("MESSAGE_RETRY_FAILED", "The message retry failed.", 503) from exc
    message.status = "SENT"
    message.provider_message_id = result.get("message_id")
    message.sent_at = datetime.now(UTC)
    message.failed_at = None
    message.last_error = None
    await audit(
        ctx.session,
        ctx.user,
        "CARE_MESSAGE_RETRIED",
        "CareConversationMessage",
        message.id,
        conversation.branch_id,
    )
    await ctx.session.commit()
    return model_dict(message)


@router.get("/availability/{branch_id}/exceptions")
async def list_availability_exceptions(
    branch_id: uuid.UUID,
    ctx: Annotated[AuthContext, Depends(current_context)],
):
    if not _branch_allowed(ctx, branch_id):
        raise AppError("BRANCH_NOT_AUTHORIZED", "Branch is outside your scope.", 403)
    query = select(CareAvailabilityException).where(
        CareAvailabilityException.branch_id == branch_id
    )
    if ctx.user.role == Role.DOCTOR:
        query = query.where(
            or_(
                CareAvailabilityException.doctor_id.is_(None),
                CareAvailabilityException.doctor_id == ctx.user.id,
            )
        )
    rows = (
        await ctx.session.scalars(query.order_by(CareAvailabilityException.starts_at.asc()))
    ).all()
    return [model_dict(row) for row in rows]


@router.post("/availability/{branch_id}/exceptions", status_code=201)
async def create_availability_exception(
    branch_id: uuid.UUID,
    body: AvailabilityExceptionRequest,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER, Role.DOCTOR))],
):
    if not _branch_allowed(ctx, branch_id):
        raise AppError("BRANCH_NOT_AUTHORIZED", "Branch is outside your scope.", 403)
    if (
        body.starts_at.tzinfo is None
        or body.ends_at.tzinfo is None
        or body.ends_at <= body.starts_at
    ):
        raise AppError(
            "INVALID_AVAILABILITY_WINDOW",
            "Availability times must include timezone and end after start.",
            422,
        )
    if body.kind not in {"UNAVAILABLE", "BREAK"}:
        raise AppError(
            "INVALID_AVAILABILITY_KIND", "Availability kind must be UNAVAILABLE or BREAK.", 422
        )
    doctor_id = ctx.user.id if ctx.user.role == Role.DOCTOR else body.doctor_id
    row = CareAvailabilityException(
        branch_id=branch_id,
        doctor_id=doctor_id,
        starts_at=body.starts_at.astimezone(UTC),
        ends_at=body.ends_at.astimezone(UTC),
        kind=body.kind,
        reason=body.reason,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await audit(
        ctx.session,
        ctx.user,
        "AVAILABILITY_EXCEPTION_CREATED",
        "CareAvailabilityException",
        row.id,
        branch_id,
    )
    await ctx.session.commit()
    return model_dict(row)


@router.delete("/availability/{branch_id}/exceptions/{exception_id}", status_code=204)
async def delete_availability_exception(
    branch_id: uuid.UUID,
    exception_id: uuid.UUID,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER, Role.DOCTOR))],
):
    if not _branch_allowed(ctx, branch_id):
        raise AppError("BRANCH_NOT_AUTHORIZED", "Branch is outside your scope.", 403)
    row = await ctx.session.get(CareAvailabilityException, exception_id)
    if not row or row.branch_id != branch_id:
        raise AppError(
            "AVAILABILITY_EXCEPTION_NOT_FOUND", "Availability exception was not found.", 404
        )
    if ctx.user.role == Role.DOCTOR and row.doctor_id not in {None, ctx.user.id}:
        raise AppError("FORBIDDEN", "This exception belongs to another doctor.", 403)
    await audit(
        ctx.session,
        ctx.user,
        "AVAILABILITY_EXCEPTION_DELETED",
        "CareAvailabilityException",
        row.id,
        branch_id,
    )
    await ctx.session.delete(row)
    await ctx.session.commit()


@router.get("/availability/{branch_id}/slots")
async def get_available_slots(
    branch_id: uuid.UUID,
    ctx: Annotated[AuthContext, Depends(current_context)],
    doctor_id: uuid.UUID | None = None,
    limit: int = Query(default=30, ge=1, le=100),
):
    if not _branch_allowed(ctx, branch_id):
        raise AppError("BRANCH_NOT_AUTHORIZED", "Branch is outside your scope.", 403)
    if ctx.user.role == Role.DOCTOR:
        doctor_id = ctx.user.id
    settings = await settings_for_branch(ctx.session, branch_id)
    slots = await available_slots(
        ctx.session, branch_id=branch_id, settings=settings, doctor_id=doctor_id, limit=limit
    )
    return {"timezone": settings.timezone, "slots": [slot.isoformat() for slot in slots]}


@router.post("/internal/whatsapp/inbound")
async def inbound_whatsapp(
    body: InboundWhatsApp,
    control: Annotated[AsyncSession, Depends(control_session)],
    authorization: Annotated[str | None, Header()] = None,
):
    token = get_settings().whatsapp_service_token
    if not token or authorization != f"Bearer {token}":
        raise AppError("AUTH_REQUIRED", "Internal authentication is required.", 401)
    if not body.account_id.startswith("clinic_"):
        raise AppError("CLINIC_CONTEXT_INVALID", "Clinic context is invalid.", 422)
    try:
        clinic_id = uuid.UUID(hex=body.account_id.removeprefix("clinic_"))
    except ValueError as exc:
        raise AppError("CLINIC_CONTEXT_INVALID", "Clinic context is invalid.", 422) from exc
    clinic = await resolver.by_id(control, clinic_id)
    factory = resolver.session_factory(clinic)
    async with factory() as session:
        result = await process_inbound_message(
            session,
            clinic_id=clinic.id,
            clinic_name=clinic.name,
            phone=body.phone,
            text=body.text,
            provider_message_id=body.message_id,
        )
        await session.commit()
        return result


@router.post("/internal/whatsapp/status")
async def whatsapp_message_status(
    body: MessageStatusRequest,
    control: Annotated[AsyncSession, Depends(control_session)],
    authorization: Annotated[str | None, Header()] = None,
):
    token = get_settings().whatsapp_service_token
    if not token or authorization != f"Bearer {token}":
        raise AppError("AUTH_REQUIRED", "Internal authentication is required.", 401)
    if not body.account_id.startswith("clinic_"):
        raise AppError("CLINIC_CONTEXT_INVALID", "Clinic context is invalid.", 422)
    try:
        clinic_id = uuid.UUID(hex=body.account_id.removeprefix("clinic_"))
    except ValueError as exc:
        raise AppError("CLINIC_CONTEXT_INVALID", "Clinic context is invalid.", 422) from exc
    normalized = body.status.upper()
    if normalized not in {"QUEUED", "SENT", "DELIVERED", "READ", "FAILED"}:
        raise AppError("MESSAGE_STATUS_INVALID", "Message delivery status is invalid.", 422)
    clinic = await resolver.by_id(control, clinic_id)
    async with resolver.session_factory(clinic)() as session:
        message = await session.scalar(
            select(CareConversationMessage).where(
                CareConversationMessage.provider_message_id == body.provider_message_id
            )
        )
        if not message:
            return {"handled": False, "reason": "message_not_found"}
        now = datetime.now(UTC)
        message.status = normalized
        if normalized == "SENT":
            message.sent_at = message.sent_at or now
        elif normalized == "DELIVERED":
            message.delivered_at = now
        elif normalized == "READ":
            message.read_at = now
        elif normalized == "FAILED":
            message.failed_at = now
            message.last_error = body.error or "Provider delivery failed"
        await session.commit()
        return {"handled": True, "message_id": str(message.id), "status": normalized}
