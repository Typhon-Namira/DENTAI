import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import audit
from app.auth.dependencies import AuthContext, authorized_patient, current_context, roles
from app.care.booking_links import booking_url, decode_booking_token
from app.care.language import language_for_phone
from app.care.models import (
    CareAppointment,
    CareConversation,
    CareConversationMessage,
    CarePlanItem,
)
from app.care.service import available_slots, settings_for_branch
from app.clinic_resolution.service import resolver
from app.common.serialization import model_dict
from app.core.errors import AppError
from app.database.models import Branch, Patient, Role
from app.database.sessions import control_session
from app.outreach.whatsapp_client import (
    WhatsAppServiceClient,
    WhatsAppServiceError,
    normalize_phone,
)

router = APIRouter(prefix="/care/booking", tags=["care-booking"])


class PublicBookingRequest(BaseModel):
    slot: datetime
    language: str = Field(default="en", pattern=r"^(en|hy|ru)$")
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None


class DoctorRangeRequest(BaseModel):
    starts_at: datetime
    ends_at: datetime
    note: str | None = Field(default=None, max_length=500)


def _uuid(payload: dict[str, Any], key: str) -> uuid.UUID | None:
    value = payload.get(key)
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise AppError("BOOKING_LINK_INVALID", "This booking link is invalid.", 404) from exc


def _branch_allowed(ctx: AuthContext, branch_id: uuid.UUID) -> bool:
    return ctx.user.role == Role.DIRECTOR or branch_id in ctx.branch_ids


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise AppError(
            "BOOKING_TIMEZONE_REQUIRED",
            "The selected time must include a timezone.",
            422,
        )
    return value.astimezone(UTC)


def _language(value: str | None) -> str:
    return value if value in {"en", "hy", "ru"} else "en"


def _slot_label(value: datetime, timezone_name: str) -> str:
    return _utc(value).astimezone(ZoneInfo(timezone_name)).strftime("%Y-%m-%d %H:%M")


def _requested_message(language: str, slot: datetime, timezone_name: str) -> str:
    label = _slot_label(slot, timezone_name)
    if language == "hy":
        return (
            f"Ձեր {label} ({timezone_name}) ստուգման ժամը գրանցվել է և սպասում է "
            "բժշկի հաստատմանը։ Բժշկի պատասխանից հետո անմիջապես կգրենք ձեզ։"
        )
    if language == "ru":
        return (
            f"Ваш запрос на осмотр {label} ({timezone_name}) зарегистрирован и ожидает "
            "подтверждения врача. Мы сразу напишем вам после ответа врача."
        )
    return (
        f"Your requested check-up time, {label} ({timezone_name}), has been registered "
        "and is waiting for the doctor's confirmation. We'll message you as soon as "
        "the doctor responds."
    )


def _approved_message(language: str, slot: datetime, timezone_name: str) -> str:
    label = _slot_label(slot, timezone_name)
    if language == "hy":
        return (
            f"Բժիշկը հաստատել է ձեր ստուգման ժամը՝ {label} ({timezone_name})։ "
            "Սպասում ենք ձեզ կլինիկայում։"
        )
    if language == "ru":
        return f"Врач подтвердил ваш прием: {label} ({timezone_name}). Ждем вас в клинике."
    return (
        f"Your doctor has confirmed your check-up for {label} ({timezone_name}). "
        "We look forward to seeing you at the clinic."
    )


def _range_message(
    language: str,
    start: datetime,
    end: datetime,
    timezone_name: str,
    url: str,
    note: str | None,
) -> str:
    start_label = _slot_label(start, timezone_name)
    end_label = _slot_label(end, timezone_name)
    note_line = f"\n{note.strip()}" if note and note.strip() else ""
    if language == "hy":
        return (
            "Բժիշկն առաջարկում է նոր ժամանակային միջակայք՝ "
            f"{start_label}–{end_label} ({timezone_name})։{note_line}\n"
            f"Այս միջակայքից ընտրեք ազատ ժամը՝ {url}"
        )
    if language == "ru":
        return (
            f"Врач предлагает новый интервал: {start_label}–{end_label} "
            f"({timezone_name}).{note_line}\n"
            f"Выберите свободное время в этом интервале: {url}"
        )
    return (
        f"Your doctor suggests a new time window: {start_label}–{end_label} "
        f"({timezone_name}).{note_line}\nChoose an available time in this window: {url}"
    )


async def _find_patient_by_phone(
    session: AsyncSession, phone: str, branch_id: uuid.UUID
) -> Patient | None:
    normalized = normalize_phone(phone)
    rows = (
        await session.scalars(
            select(Patient).where(
                Patient.branch_id == branch_id,
                Patient.status != "ARCHIVED",
            )
        )
    ).all()
    for patient in rows:
        for candidate in (patient.whatsapp_phone, patient.phone):
            if not candidate:
                continue
            try:
                if normalize_phone(candidate) == normalized:
                    return patient
            except ValueError:
                continue
    return None


async def _conversation_for_patient(
    session: AsyncSession, patient_id: uuid.UUID
) -> CareConversation | None:
    return await session.scalar(
        select(CareConversation)
        .where(
            CareConversation.patient_id == patient_id,
            CareConversation.status == "ACTIVE",
        )
        .order_by(CareConversation.created_at.desc())
    )


async def _send_and_log(
    session: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient: Patient,
    conversation: CareConversation | None,
    care_plan_item_id: uuid.UUID | None,
    language: str,
    message: str,
    kind: str,
) -> tuple[str, str | None]:
    phone = patient.whatsapp_phone or patient.phone
    if not phone:
        return "NOT_AVAILABLE", None
    try:
        normalized = normalize_phone(phone)
        sent = await WhatsAppServiceClient().send_message(clinic_id, normalized, message)
    except (WhatsAppServiceError, ValueError):
        return "FAILED", None
    provider_id = sent.get("message_id")
    if conversation:
        session.add(
            CareConversationMessage(
                conversation_id=conversation.id,
                care_plan_item_id=care_plan_item_id,
                direction="OUT",
                body=message,
                language=language,
                status="SENT",
                sent_at=datetime.now(UTC),
                attempt_count=1,
                provider_message_id=provider_id,
                message_metadata={"kind": kind},
            )
        )
        conversation.last_message_at = datetime.now(UTC)
    return "SENT", provider_id


@router.get("/link/{branch_id}")
async def clinic_booking_link(
    branch_id: uuid.UUID,
    ctx: Annotated[AuthContext, Depends(current_context)],
):
    if not _branch_allowed(ctx, branch_id):
        raise AppError("BRANCH_NOT_AUTHORIZED", "Branch is outside your scope.", 403)
    branch = await ctx.session.get(Branch, branch_id)
    if not branch:
        raise AppError("BRANCH_NOT_FOUND", "Branch was not found.", 404)
    settings = await settings_for_branch(ctx.session, branch_id)
    await ctx.session.commit()
    doctor_id = ctx.user.id if ctx.user.role == Role.DOCTOR else None
    return {
        "url": booking_url(
            clinic_id=ctx.clinic.id,
            branch_id=branch_id,
            doctor_id=doctor_id,
        ),
        "branch_id": str(branch_id),
        "branch_name": branch.name,
        "timezone": settings.timezone,
        "working_days": settings.working_days,
        "day_start": settings.day_start,
        "day_end": settings.day_end,
        "appointment_minutes": settings.appointment_minutes,
        "booking_horizon_days": settings.booking_horizon_days,
        "languages": ["en", "hy", "ru"],
        "stable": True,
    }


@router.get("/public/{token}")
async def public_booking_form(
    token: str,
    control: Annotated[AsyncSession, Depends(control_session)],
):
    payload = decode_booking_token(token)
    clinic_id = _uuid(payload, "clinic_id")
    branch_id = _uuid(payload, "branch_id")
    if not clinic_id or not branch_id:
        raise AppError("BOOKING_LINK_INVALID", "This booking link is invalid.", 404)
    clinic = await resolver.by_id(control, clinic_id)
    async with resolver.session_factory(clinic)() as session:
        branch = await session.get(Branch, branch_id)
        if not branch or not branch.is_active:
            raise AppError(
                "BOOKING_BRANCH_UNAVAILABLE",
                "This clinic location is unavailable.",
                404,
            )
        settings = await settings_for_branch(session, branch_id)
        doctor_id = _uuid(payload, "doctor_id")
        patient_id = _uuid(payload, "patient_id")
        patient = await session.get(Patient, patient_id) if patient_id else None
        slots = await available_slots(
            session,
            branch_id=branch_id,
            settings=settings,
            doctor_id=doctor_id,
            limit=5000,
        )
        start_raw, end_raw = payload.get("window_start"), payload.get("window_end")
        if start_raw and end_raw:
            try:
                window_start = _utc(datetime.fromisoformat(str(start_raw)))
                window_end = _utc(datetime.fromisoformat(str(end_raw)))
                slots = [
                    slot for slot in slots if window_start <= slot.astimezone(UTC) <= window_end
                ]
            except (ValueError, TypeError) as exc:
                raise AppError(
                    "BOOKING_LINK_INVALID",
                    "This booking link is invalid.",
                    404,
                ) from exc
        await session.commit()
        return {
            "clinic_name": clinic.name,
            "branch_name": branch.name,
            "timezone": settings.timezone,
            "working_days": settings.working_days,
            "day_start": settings.day_start,
            "day_end": settings.day_end,
            "appointment_minutes": settings.appointment_minutes,
            "booking_horizon_days": settings.booking_horizon_days,
            "slots": [slot.isoformat() for slot in slots],
            "patient": {"first_name": patient.first_name} if patient else None,
            "prefilled": patient is not None,
            "languages": ["en", "hy", "ru"],
        }


@router.post("/public/{token}", status_code=201)
async def public_book(
    token: str,
    body: PublicBookingRequest,
    control: Annotated[AsyncSession, Depends(control_session)],
):
    payload = decode_booking_token(token)
    clinic_id = _uuid(payload, "clinic_id")
    branch_id = _uuid(payload, "branch_id")
    if not clinic_id or not branch_id:
        raise AppError("BOOKING_LINK_INVALID", "This booking link is invalid.", 404)
    clinic = await resolver.by_id(control, clinic_id)
    async with resolver.session_factory(clinic)() as session:
        branch = await session.get(Branch, branch_id)
        if not branch or not branch.is_active:
            raise AppError(
                "BOOKING_BRANCH_UNAVAILABLE",
                "This clinic location is unavailable.",
                404,
            )
        settings = await settings_for_branch(session, branch_id)
        doctor_id = _uuid(payload, "doctor_id")
        patient_id = _uuid(payload, "patient_id")
        selected = _utc(body.slot)
        fresh_slots = await available_slots(
            session,
            branch_id=branch_id,
            settings=settings,
            doctor_id=doctor_id,
            limit=5000,
        )
        fresh_by_utc = {slot.astimezone(UTC) for slot in fresh_slots}
        if selected not in fresh_by_utc:
            raise AppError(
                "BOOKING_SLOT_UNAVAILABLE",
                "That time is no longer available. Please choose another slot.",
                409,
            )
        start_raw, end_raw = payload.get("window_start"), payload.get("window_end")
        if start_raw and end_raw:
            try:
                window_start = _utc(datetime.fromisoformat(str(start_raw)))
                window_end = _utc(datetime.fromisoformat(str(end_raw)))
            except (ValueError, TypeError) as exc:
                raise AppError(
                    "BOOKING_LINK_INVALID",
                    "This booking link is invalid.",
                    404,
                ) from exc
            if not (window_start <= selected <= window_end):
                raise AppError(
                    "BOOKING_SLOT_OUTSIDE_DOCTOR_WINDOW",
                    "Please select a time inside the doctor's suggested window.",
                    409,
                )

        patient = await session.get(Patient, patient_id) if patient_id else None
        if not patient:
            if not body.first_name or not body.last_name or not body.phone:
                raise AppError(
                    "BOOKING_PATIENT_DETAILS_REQUIRED",
                    "Name and phone are required for booking.",
                    422,
                )
            try:
                normalized_phone = normalize_phone(body.phone)
            except ValueError as exc:
                raise AppError(
                    "BOOKING_PHONE_INVALID",
                    "Use an international phone number.",
                    422,
                ) from exc
            patient = await _find_patient_by_phone(session, normalized_phone, branch_id)
            if not patient:
                patient = Patient(
                    patient_number=f"WEB-{uuid.uuid4().hex[:10].upper()}",
                    first_name=body.first_name.strip(),
                    last_name=body.last_name.strip(),
                    phone=normalized_phone,
                    whatsapp_phone=normalized_phone,
                    email=str(body.email).casefold() if body.email else None,
                    branch_id=branch_id,
                    status="ACTIVE",
                )
                session.add(patient)
                await session.flush()

        # Supersede an earlier doctor-rejected proposal only after the patient
        # successfully chooses a fresh slot from the current availability engine.
        old_rows = (
            await session.scalars(
                select(CareAppointment).where(
                    CareAppointment.patient_id == patient.id,
                    CareAppointment.branch_id == branch_id,
                    CareAppointment.status == "RESCHEDULE_REQUESTED",
                )
            )
        ).all()
        for old in old_rows:
            old.status = "RESCHEDULED"

        care_plan_item_id = _uuid(payload, "care_plan_item_id")
        if care_plan_item_id:
            item = await session.get(CarePlanItem, care_plan_item_id)
            if not item:
                care_plan_item_id = None
        conversation = await _conversation_for_patient(session, patient.id)
        duration = timedelta(minutes=settings.appointment_minutes)
        appointment = CareAppointment(
            patient_id=patient.id,
            branch_id=branch_id,
            doctor_id=doctor_id,
            conversation_id=conversation.id if conversation else None,
            care_plan_item_id=care_plan_item_id,
            starts_at=selected,
            ends_at=selected + duration,
            timezone=settings.timezone,
            status="PROPOSED",
            source="BOOKING_LINK",
            reason="Teta2 check-up booking",
            patient_confirmed_at=datetime.now(UTC),
            notification_status="PENDING",
        )
        session.add(appointment)
        try:
            await session.flush()
        except IntegrityError as exc:
            await session.rollback()
            raise AppError(
                "BOOKING_SLOT_UNAVAILABLE",
                "That time was just booked. Please choose another slot.",
                409,
            ) from exc

        language = _language(body.language)
        message = _requested_message(language, selected, settings.timezone)
        notification_status, provider_id = await _send_and_log(
            session,
            clinic_id=clinic_id,
            patient=patient,
            conversation=conversation,
            care_plan_item_id=care_plan_item_id,
            language=language,
            message=message,
            kind="booking_link_requested",
        )
        appointment.notification_status = notification_status
        appointment.notification_attempt_count = 1 if notification_status != "NOT_AVAILABLE" else 0
        appointment.notification_provider_id = provider_id
        appointment.notification_sent_at = (
            datetime.now(UTC) if notification_status == "SENT" else None
        )
        await session.commit()
        return {
            "id": str(appointment.id),
            "status": appointment.status,
            "starts_at": appointment.starts_at,
            "timezone": appointment.timezone,
            "message": message,
            "notification_status": notification_status,
        }


@router.post("/appointments/{appointment_id}/approve")
async def approve_booking_appointment(
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
        raise AppError(
            "BRANCH_NOT_AUTHORIZED",
            "Appointment is outside your scope.",
            403,
        )
    await authorized_patient(ctx, row.patient_id)
    if row.status != "PROPOSED":
        raise AppError(
            "INVALID_APPOINTMENT_STATE",
            "Appointment is not awaiting approval.",
            409,
        )
    collision = await ctx.session.scalar(
        select(CareAppointment.id).where(
            CareAppointment.id != row.id,
            CareAppointment.branch_id == row.branch_id,
            CareAppointment.doctor_id == row.doctor_id,
            CareAppointment.status == "APPROVED",
            CareAppointment.starts_at < row.ends_at,
            CareAppointment.ends_at > row.starts_at,
        )
    )
    if collision:
        raise AppError(
            "APPOINTMENT_COLLISION",
            "The selected time is no longer available.",
            409,
        )
    patient = await ctx.session.get(Patient, row.patient_id)
    if not patient:
        raise AppError("PATIENT_NOT_FOUND", "Patient was not found.", 404)
    conversation = (
        await ctx.session.get(CareConversation, row.conversation_id)
        if row.conversation_id
        else None
    )
    phone = patient.whatsapp_phone or patient.phone
    language = _language(conversation.language if conversation else language_for_phone(phone, "en"))
    message = _approved_message(language, row.starts_at, row.timezone)
    notification_status, provider_id = await _send_and_log(
        ctx.session,
        clinic_id=ctx.clinic.id,
        patient=patient,
        conversation=conversation,
        care_plan_item_id=row.care_plan_item_id,
        language=language,
        message=message,
        kind="appointment_approved",
    )
    if notification_status == "FAILED":
        raise AppError(
            "APPOINTMENT_NOTIFICATION_FAILED",
            "The patient could not be notified, so the appointment remains pending.",
            503,
        )
    row.status = "APPROVED"
    row.notification_status = notification_status
    row.notification_attempt_count += 1
    row.notification_provider_id = provider_id
    row.notification_sent_at = datetime.now(UTC) if notification_status == "SENT" else None
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


@router.post("/appointments/{appointment_id}/suggest-range")
async def suggest_booking_range(
    appointment_id: uuid.UUID,
    body: DoctorRangeRequest,
    ctx: Annotated[
        AuthContext,
        Depends(roles(Role.DIRECTOR, Role.MANAGER, Role.DOCTOR)),
    ],
):
    row = await ctx.session.get(CareAppointment, appointment_id)
    if not row:
        raise AppError("APPOINTMENT_NOT_FOUND", "Appointment was not found.", 404)
    if not _branch_allowed(ctx, row.branch_id):
        raise AppError(
            "BRANCH_NOT_AUTHORIZED",
            "Appointment is outside your scope.",
            403,
        )
    await authorized_patient(ctx, row.patient_id)
    if row.status not in {"PROPOSED", "RESCHEDULE_REQUESTED"}:
        raise AppError(
            "INVALID_APPOINTMENT_STATE",
            "This appointment cannot be rescheduled.",
            409,
        )
    start = _utc(body.starts_at)
    end = _utc(body.ends_at)
    if end <= start:
        raise AppError(
            "INVALID_DOCTOR_WINDOW",
            "The end of the suggested window must be after its start.",
            422,
        )
    settings = await settings_for_branch(ctx.session, row.branch_id)
    patient = await ctx.session.get(Patient, row.patient_id)
    if not patient:
        raise AppError("PATIENT_NOT_FOUND", "Patient was not found.", 404)
    conversation = (
        await ctx.session.get(CareConversation, row.conversation_id)
        if row.conversation_id
        else await _conversation_for_patient(ctx.session, patient.id)
    )
    language = _language(
        conversation.language
        if conversation
        else language_for_phone(patient.whatsapp_phone or patient.phone, "en")
    )
    url = booking_url(
        clinic_id=ctx.clinic.id,
        branch_id=row.branch_id,
        doctor_id=row.doctor_id,
        patient_id=row.patient_id,
        care_plan_item_id=row.care_plan_item_id,
        window_start=start.isoformat(),
        window_end=end.isoformat(),
    )
    message = _range_message(
        language,
        start,
        end,
        settings.timezone,
        url,
        body.note,
    )
    notification_status, _ = await _send_and_log(
        ctx.session,
        clinic_id=ctx.clinic.id,
        patient=patient,
        conversation=conversation,
        care_plan_item_id=row.care_plan_item_id,
        language=language,
        message=message,
        kind="doctor_reschedule_range",
    )
    if notification_status == "FAILED":
        raise AppError(
            "APPOINTMENT_NOTIFICATION_FAILED",
            "The doctor's suggested range could not be sent to the patient.",
            503,
        )
    row.status = "RESCHEDULE_REQUESTED"
    row.doctor_note = body.note or (f"Suggested range: {start.isoformat()} – {end.isoformat()}")
    row.reschedule_count += 1
    await audit(
        ctx.session,
        ctx.user,
        "APPOINTMENT_RESCHEDULE_REQUESTED",
        "CareAppointment",
        row.id,
        row.branch_id,
    )
    await ctx.session.commit()
    return {
        **model_dict(row),
        "booking_url": url,
        "suggested_start": start,
        "suggested_end": end,
    }
