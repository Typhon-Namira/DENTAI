import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import audit
from app.auth.dependencies import AuthContext, authorized_patient, current_context, roles
from app.care.groq import care_agent_reply
from app.care.language import language_name
from app.care.models import (
    CareAppointment,
    CareConversation,
    CareConversationMessage,
    CarePlan,
    CarePlanItem,
)
from app.care.sequential import approve_sequential_plan, record_visit_outcome
from app.care.service import available_slots, settings_for_branch
from app.clinic_resolution.service import resolver
from app.common.serialization import model_dict
from app.core.config import get_settings
from app.core.errors import AppError
from app.database.models import Patient, PatientDoctorAssignment, Role
from app.database.sessions import control_session
from app.outreach.whatsapp_client import WhatsAppServiceClient, normalize_phone

router = APIRouter(prefix="/care", tags=["care-sequential"])


class VisitOutcomeRequest(BaseModel):
    outcome: str
    note: str | None = Field(default=None, max_length=2000)


class InboundWhatsApp(BaseModel):
    account_id: str
    phone: str
    text: str = Field(min_length=1, max_length=10000)
    message_id: str | None = None


def _branch_allowed(ctx: AuthContext, branch_id: uuid.UUID) -> bool:
    return ctx.user.role == Role.DIRECTOR or branch_id in ctx.branch_ids


async def _patient_for_phone(session: AsyncSession, phone: str) -> Patient | None:
    try:
        normalized = normalize_phone(phone)
    except ValueError:
        return None
    rows = (
        await session.scalars(
            select(Patient).where(
                (Patient.whatsapp_phone.is_not(None)) | (Patient.phone.is_not(None))
            )
        )
    ).all()
    for patient in rows:
        for value in (patient.whatsapp_phone, patient.phone):
            if not value:
                continue
            try:
                if normalize_phone(value) == normalized:
                    return patient
            except ValueError:
                continue
    return None


@router.get("/sequential-plans")
async def sequential_plans(
    ctx: Annotated[AuthContext, Depends(current_context)],
    limit: int = Query(default=200, ge=1, le=200),
):
    query = select(CarePlan).order_by(CarePlan.created_at.desc()).limit(limit)
    if ctx.user.role != Role.DIRECTOR:
        query = query.where(CarePlan.branch_id.in_(ctx.branch_ids))
    if ctx.user.role == Role.DOCTOR:
        query = query.where(
            CarePlan.patient_id.in_(
                select(PatientDoctorAssignment.patient_id).where(
                    PatientDoctorAssignment.doctor_id == ctx.user.id,
                    PatientDoctorAssignment.active.is_(True),
                )
            )
        )
    plans = (await ctx.session.scalars(query)).all()
    patient_ids = {plan.patient_id for plan in plans}
    patients = (
        {
            patient.id: patient
            for patient in (
                await ctx.session.scalars(select(Patient).where(Patient.id.in_(patient_ids)))
            ).all()
        }
        if patient_ids
        else {}
    )
    result = []
    for plan in plans:
        items = (
            await ctx.session.scalars(
                select(CarePlanItem)
                .where(CarePlanItem.care_plan_id == plan.id)
                .order_by(CarePlanItem.sequence_order.asc(), CarePlanItem.priority_score.desc())
            )
        ).all()
        patient = patients.get(plan.patient_id)
        result.append(
            {
                **model_dict(plan),
                "patient": model_dict(patient) if patient else None,
                "items": [model_dict(item) for item in items if item.status != "REJECTED"],
            }
        )
    return result


@router.post("/plans/{plan_id}/approve-sequential")
async def approve_plan_sequential(
    plan_id: uuid.UUID,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER, Role.DOCTOR))],
):
    plan = await ctx.session.get(CarePlan, plan_id)
    if not plan:
        raise AppError("CARE_PLAN_NOT_FOUND", "Care plan was not found.", 404)
    if not _branch_allowed(ctx, plan.branch_id):
        raise AppError("BRANCH_NOT_AUTHORIZED", "Care plan is outside your scope.", 403)
    await authorized_patient(ctx, plan.patient_id)
    if plan.status != "PENDING_APPROVAL":
        raise AppError("INVALID_CARE_PLAN_STATE", "Care plan is not awaiting approval.", 409)

    await approve_sequential_plan(ctx.session, plan=plan)
    plan.approved_by = ctx.user.id
    plan.approved_at = datetime.now(UTC)
    await audit(
        ctx.session,
        ctx.user,
        "CARE_PLAN_SEQUENTIAL_APPROVED",
        "CarePlan",
        plan.id,
        plan.branch_id,
    )
    await ctx.session.commit()
    items = (
        await ctx.session.scalars(
            select(CarePlanItem)
            .where(CarePlanItem.care_plan_id == plan.id)
            .order_by(CarePlanItem.sequence_order.asc())
        )
    ).all()
    return {
        **model_dict(plan),
        "items": [model_dict(item) for item in items if item.status != "REJECTED"],
    }


@router.post("/appointments/{appointment_id}/outcome")
async def appointment_outcome(
    appointment_id: uuid.UUID,
    body: VisitOutcomeRequest,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER, Role.DOCTOR))],
):
    row = await ctx.session.get(CareAppointment, appointment_id)
    if not row:
        raise AppError("APPOINTMENT_NOT_FOUND", "Appointment was not found.", 404)
    if not _branch_allowed(ctx, row.branch_id):
        raise AppError("BRANCH_NOT_AUTHORIZED", "Appointment is outside your scope.", 403)
    await authorized_patient(ctx, row.patient_id)
    if row.status not in {"APPROVED", "PROPOSED", "RESCHEDULE_REQUESTED"}:
        raise AppError(
            "INVALID_APPOINTMENT_STATE",
            "Visit outcome can only be recorded for an active appointment.",
            409,
        )
    try:
        await record_visit_outcome(
            ctx.session,
            appointment=row,
            outcome=body.outcome,
            note=body.note,
        )
    except ValueError as exc:
        raise AppError(
            "INVALID_VISIT_OUTCOME",
            "Outcome must be TREATED, ATTENDED_NOT_TREATED, or NO_SHOW.",
            422,
        ) from exc
    await audit(
        ctx.session,
        ctx.user,
        "APPOINTMENT_VISIT_OUTCOME_RECORDED",
        "CareAppointment",
        row.id,
        row.branch_id,
        {"outcome": row.visit_outcome, "note": body.note},
    )
    await ctx.session.commit()
    return model_dict(row)


@router.post("/internal/whatsapp/inbound")
async def sequential_inbound_whatsapp(
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
    async with resolver.session_factory(clinic)() as session:
        patient = await _patient_for_phone(session, body.phone)
        if not patient:
            return {"handled": False, "reason": "patient_not_found"}
        conversation = await session.scalar(
            select(CareConversation)
            .where(CareConversation.patient_id == patient.id, CareConversation.status == "ACTIVE")
            .order_by(CareConversation.created_at.desc())
            .limit(1)
        )
        if not conversation:
            return {"handled": False, "reason": "conversation_not_found"}
        if body.message_id:
            duplicate = await session.scalar(
                select(CareConversationMessage.id).where(
                    CareConversationMessage.conversation_id == conversation.id,
                    CareConversationMessage.provider_message_id == body.message_id,
                )
            )
            if duplicate:
                return {"handled": True, "duplicate": True}

        inbound = CareConversationMessage(
            conversation_id=conversation.id,
            direction="IN",
            body=body.text,
            language=conversation.language,
            status="RECEIVED",
            provider_message_id=body.message_id,
            message_metadata={},
        )
        session.add(inbound)
        await session.flush()

        plan = (
            await session.get(CarePlan, conversation.care_plan_id)
            if conversation.care_plan_id
            else None
        )
        active_item = None
        if plan:
            active_item = await session.scalar(
                select(CarePlanItem)
                .where(
                    CarePlanItem.care_plan_id == plan.id,
                    CarePlanItem.status.in_(
                        [
                            "FOLLOWUP_READY",
                            "CONTACTED",
                            "APPOINTMENT_PENDING_APPROVAL",
                            "BOOKED",
                        ]
                    ),
                )
                .order_by(CarePlanItem.sequence_order.asc())
                .limit(1)
            )
        history = (
            await session.scalars(
                select(CareConversationMessage)
                .where(CareConversationMessage.conversation_id == conversation.id)
                .order_by(CareConversationMessage.created_at.asc())
            )
        ).all()
        settings = await settings_for_branch(session, patient.branch_id)
        slots = await available_slots(
            session,
            branch_id=patient.branch_id,
            settings=settings,
            doctor_id=plan.doctor_id if plan else None,
            limit=8,
        )
        slot_strings = [slot.isoformat() for slot in slots]
        context = dict(conversation.booking_context or {})
        outcome_context = ""
        if context.get("last_visit_outcome"):
            outcome_context = (
                f" Previous clinic-recorded visit outcome for tooth {context.get('last_visit_tooth')}: "
                f"{context.get('last_visit_outcome')}. Use this as factual conversation context."
            )
        reply = await care_agent_reply(
            language=conversation.language,
            patient_name=f"{patient.first_name} {patient.last_name}".strip(),
            clinic_name=clinic.name,
            care_items=(
                [
                    {
                        "tooth": active_item.tooth_fdi,
                        "finding": active_item.finding_type,
                        "window": active_item.recommended_window,
                        "priority": active_item.priority_level,
                        "visit_outcome": active_item.outcome,
                    }
                ]
                if active_item
                else []
            ),
            history=[
                {
                    "role": "assistant" if item.direction == "OUT" else "user",
                    "content": item.body,
                }
                for item in history
            ],
            available_slots=slot_strings,
            inbound_message=body.text,
            booking_instructions=(settings.booking_instructions or "") + outcome_context,
        )

        selected = None
        if active_item and reply.selected_slot and reply.selected_slot in slot_strings:
            fresh = await available_slots(
                session,
                branch_id=patient.branch_id,
                settings=settings,
                doctor_id=plan.doctor_id if plan else None,
                limit=64,
            )
            if reply.selected_slot in {slot.isoformat() for slot in fresh}:
                selected = datetime.fromisoformat(reply.selected_slot)
                duration = timedelta(minutes=settings.appointment_minutes)
                appointment = CareAppointment(
                    patient_id=patient.id,
                    branch_id=patient.branch_id,
                    doctor_id=plan.doctor_id if plan else None,
                    conversation_id=conversation.id,
                    care_plan_item_id=active_item.id,
                    starts_at=selected.astimezone(UTC),
                    ends_at=(selected + duration).astimezone(UTC),
                    timezone=settings.timezone,
                    status="PROPOSED",
                    source="AI",
                    tooth_fdi=active_item.tooth_fdi,
                    finding_type=active_item.finding_type,
                    reason=f"Teta2 Care check-up · tooth {active_item.tooth_fdi}",
                    patient_confirmed_at=datetime.now(UTC),
                )
                session.add(appointment)
                active_item.status = "APPOINTMENT_PENDING_APPROVAL"

        normalized_phone = normalize_phone(body.phone)
        sent = await WhatsAppServiceClient().send_message(clinic.id, normalized_phone, reply.reply)
        session.add(
            CareConversationMessage(
                conversation_id=conversation.id,
                care_plan_item_id=active_item.id if active_item else None,
                direction="OUT",
                body=reply.reply,
                language=conversation.language,
                status="SENT",
                sent_at=datetime.now(UTC),
                attempt_count=1,
                provider_message_id=sent.get("message_id"),
                message_metadata={
                    "intent": reply.intent,
                    "needs_human": reply.needs_human,
                    "selected_slot": reply.selected_slot,
                    "booked": bool(selected),
                    "active_tooth": active_item.tooth_fdi if active_item else None,
                },
            )
        )
        conversation.last_message_at = datetime.now(UTC)
        conversation.summary = (
            f"Tooth {active_item.tooth_fdi}: {reply.intent}. " if active_item else ""
        ) + (
            "Appointment awaiting doctor approval."
            if selected
            else f"Conversation active. Language: {language_name(conversation.language)}."
        )
        await session.commit()
        return {
            "handled": True,
            "intent": reply.intent,
            "appointment_proposed": bool(selected),
            "needs_human": reply.needs_human,
            "active_tooth": active_item.tooth_fdi if active_item else None,
        }
