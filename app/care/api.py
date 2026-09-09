import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AuthContext, authorized_patient, current_context, roles
from app.care.language import language_for_phone
from app.care.models import (
    CareAppointment,
    CareConversation,
    CareConversationMessage,
    CarePlan,
    CarePlanItem,
)
from app.care.service import approve_care_plan, process_inbound_message, settings_for_branch
from app.clinic_resolution.service import resolver
from app.common.serialization import model_dict
from app.core.config import get_settings
from app.core.errors import AppError
from app.database.models import Patient, PatientDoctorAssignment, Role
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


def _branch_allowed(ctx: AuthContext, branch_id: uuid.UUID) -> bool:
    return ctx.user.role == Role.DIRECTOR or branch_id in ctx.branch_ids


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
    plan = await ctx.session.get(CarePlan, plan_id)
    if not plan:
        raise AppError("CARE_PLAN_NOT_FOUND", "Care plan was not found.", 404)
    if not _branch_allowed(ctx, plan.branch_id):
        raise AppError("BRANCH_NOT_AUTHORIZED", "Care plan is outside your scope.", 403)
    await authorized_patient(ctx, plan.patient_id)
    if plan.status != "PENDING_APPROVAL":
        raise AppError("INVALID_CARE_PLAN_STATE", "Care plan is not awaiting approval.", 409)
    try:
        await approve_care_plan(
            ctx.session,
            clinic_id=ctx.clinic.id,
            clinic_name=ctx.clinic.name,
            plan=plan,
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
    row = await ctx.session.get(CareAppointment, appointment_id)
    if not row:
        raise AppError("APPOINTMENT_NOT_FOUND", "Appointment was not found.", 404)
    if not _branch_allowed(ctx, row.branch_id):
        raise AppError("BRANCH_NOT_AUTHORIZED", "Appointment is outside your scope.", 403)
    await authorized_patient(ctx, row.patient_id)
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
                provider_message_id=sent.get("message_id"),
                message_metadata={
                    "kind": "doctor_reschedule",
                    "preferred_start": body.preferred_start.isoformat()
                    if body.preferred_start
                    else None,
                },
            )
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
    row = await ctx.session.get(CareAppointment, appointment_id)
    if not row:
        raise AppError("APPOINTMENT_NOT_FOUND", "Appointment was not found.", 404)
    if not _branch_allowed(ctx, row.branch_id):
        raise AppError("BRANCH_NOT_AUTHORIZED", "Appointment is outside your scope.", 403)
    await authorized_patient(ctx, row.patient_id)
    if row.status != "PROPOSED":
        raise AppError("INVALID_APPOINTMENT_STATE", "Appointment is not awaiting approval.", 409)
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
        raise AppError(
            "APPOINTMENT_NOTIFICATION_FAILED",
            "Appointment remains pending because the patient could not be notified.",
            503,
        ) from exc
    row.status = "APPROVED"
    if row.conversation_id:
        ctx.session.add(
            CareConversationMessage(
                conversation_id=row.conversation_id,
                care_plan_item_id=row.care_plan_item_id,
                direction="OUT",
                body=message,
                language="en",
                status="SENT",
                provider_message_id=sent.get("message_id"),
                message_metadata={"kind": "appointment_approved"},
            )
        )
    if row.care_plan_item_id:
        item = await ctx.session.get(CarePlanItem, row.care_plan_item_id)
        if item:
            item.status = "BOOKED"
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
