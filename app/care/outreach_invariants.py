import calendar
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.care.models import CareConversation, CareConversationMessage, CarePlan, CarePlanItem
from app.database.models import (
    AIAnalysis,
    FollowUp,
    WhatsAppOutreach,
    WhatsAppOutreachStatus,
    XRay,
)

AI_REPLY_TIMEOUT = timedelta(minutes=10)
_SUPERSEDABLE_OUTREACH = {
    WhatsAppOutreachStatus.QUEUED,
    WhatsAppOutreachStatus.SCHEDULED,
    WhatsAppOutreachStatus.CLAIMED,
}


def utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def add_calendar_months(value: datetime, months: int) -> datetime:
    """Advance by calendar months while preserving local wall-clock semantics."""
    absolute_month = value.year * 12 + (value.month - 1) + months
    year, month_zero = divmod(absolute_month, 12)
    month = month_zero + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


async def supersede_patient_schedule_for_new_xray(
    session: AsyncSession,
    *,
    patient_id: uuid.UUID,
    new_xray_id: uuid.UUID,
) -> dict[str, int]:
    """Expire all not-yet-sent care scheduling that belongs to older OPGs.

    History is preserved. Only future execution state is invalidated so the new OPG
    can become the single source of truth for the patient's next tooth schedule.
    """
    old_analysis_ids = list(
        (
            await session.scalars(
                select(AIAnalysis.id).where(
                    AIAnalysis.patient_id == patient_id,
                    AIAnalysis.xray_id != new_xray_id,
                )
            )
        ).all()
    )
    if not old_analysis_ids:
        return {"outreach": 0, "plans": 0, "items": 0, "conversations": 0, "followups": 0}

    now = datetime.now(UTC)
    outreach_rows = (
        await session.scalars(
            select(WhatsAppOutreach).where(
                WhatsAppOutreach.patient_id == patient_id,
                WhatsAppOutreach.analysis_id.in_(old_analysis_ids),
                WhatsAppOutreach.status.in_(list(_SUPERSEDABLE_OUTREACH)),
            )
        )
    ).all()
    for row in outreach_rows:
        row.status = WhatsAppOutreachStatus.CANCELLED
        row.safe_error = "SUPERSEDED_BY_NEW_OPG"
        row.worker_id = None
        row.claimed_at = None
        row.retry_at = None

    plans = (
        await session.scalars(
            select(CarePlan).where(
                CarePlan.patient_id == patient_id,
                CarePlan.analysis_id.in_(old_analysis_ids),
                CarePlan.status.notin_(["COMPLETED", "REJECTED", "SUPERSEDED_NEW_OPG"]),
            )
        )
    ).all()
    plan_ids = [plan.id for plan in plans]
    for plan in plans:
        plan.status = "SUPERSEDED_NEW_OPG"
        plan.completed_at = now
        plan.summary = "Superseded by a newer OPG; all previous future outreach dates are expired."

    items: list[CarePlanItem] = []
    conversations: list[CareConversation] = []
    if plan_ids:
        items = list(
            (
                await session.scalars(
                    select(CarePlanItem).where(
                        CarePlanItem.care_plan_id.in_(plan_ids),
                        CarePlanItem.status.notin_(["COMPLETED", "REJECTED", "SUPERSEDED_NEW_OPG"]),
                    )
                )
            ).all()
        )
        for item in items:
            item.status = "SUPERSEDED_NEW_OPG"
            item.conversation_start_at = None

        conversations = list(
            (
                await session.scalars(
                    select(CareConversation).where(
                        CareConversation.patient_id == patient_id,
                        CareConversation.care_plan_id.in_(plan_ids),
                        CareConversation.status.in_(["ACTIVE", "WAITING_NEXT_TOOTH"]),
                    )
                )
            ).all()
        )
        for conversation in conversations:
            context = dict(conversation.booking_context or {})
            context.update(
                {
                    "stage": "SUPERSEDED_NEW_OPG",
                    "superseded_at": now.isoformat(),
                    "superseded_by_xray_id": str(new_xray_id),
                }
            )
            conversation.booking_context = context
            conversation.status = "WAITING_NEW_OPG_PLAN"
            conversation.summary = (
                "A newer OPG was uploaded. AI and the previous tooth schedule are inactive "
                "until the new OPG plan is reviewed and scheduled."
            )

    followups = list(
        (
            await session.scalars(
                select(FollowUp).where(
                    FollowUp.patient_id == patient_id,
                    FollowUp.status == "SCHEDULED",
                    FollowUp.reason.like("Teta2 Care · tooth %"),
                )
            )
        ).all()
    )
    for followup in followups:
        followup.status = "SUPERSEDED_NEW_OPG"
        followup.notes = ((followup.notes or "") + " Superseded by a newer OPG.").strip()

    await session.flush()
    return {
        "outreach": len(outreach_rows),
        "plans": len(plans),
        "items": len(items),
        "conversations": len(conversations),
        "followups": len(followups),
    }


async def validate_outreach_before_dispatch(
    session: AsyncSession,
    *,
    outreach: WhatsAppOutreach,
) -> tuple[bool, str | None]:
    """Last-moment guard against stale OPG rows and duplicate tooth sends.

    Caller must hold a row lock on the patient until dispatch is committed. That
    serializes concurrent workers for the same patient and makes this check safe.
    """
    analysis = await session.get(AIAnalysis, outreach.analysis_id)
    if not analysis:
        outreach.status = WhatsAppOutreachStatus.CANCELLED
        outreach.safe_error = "ANALYSIS_NOT_FOUND"
        return False, outreach.safe_error

    latest_xray = await session.scalar(
        select(XRay)
        .where(XRay.patient_id == outreach.patient_id)
        .order_by(XRay.uploaded_at.desc(), XRay.id.desc())
        .limit(1)
    )
    if latest_xray and analysis.xray_id != latest_xray.id:
        outreach.status = WhatsAppOutreachStatus.CANCELLED
        outreach.safe_error = "SUPERSEDED_BY_NEW_OPG"
        outreach.worker_id = None
        outreach.claimed_at = None
        return False, outreach.safe_error

    already_sent = await session.scalar(
        select(WhatsAppOutreach.id)
        .where(
            WhatsAppOutreach.id != outreach.id,
            WhatsAppOutreach.patient_id == outreach.patient_id,
            WhatsAppOutreach.analysis_id == outreach.analysis_id,
            WhatsAppOutreach.tooth_fdi == outreach.tooth_fdi,
            WhatsAppOutreach.status == WhatsAppOutreachStatus.SENT,
        )
        .order_by(WhatsAppOutreach.sent_at.desc())
        .limit(1)
    )
    if already_sent:
        outreach.status = WhatsAppOutreachStatus.CANCELLED
        outreach.safe_error = "DUPLICATE_TOOTH_ALREADY_SENT"
        outreach.worker_id = None
        outreach.claimed_at = None
        return False, outreach.safe_error

    return True, None


async def _latest_message(
    session: AsyncSession,
    conversation_id: uuid.UUID,
    direction: str,
) -> CareConversationMessage | None:
    return await session.scalar(
        select(CareConversationMessage)
        .where(
            CareConversationMessage.conversation_id == conversation_id,
            CareConversationMessage.direction == direction,
        )
        .order_by(CareConversationMessage.created_at.desc())
        .limit(1)
    )


async def expire_conversation_for_ai_inactivity(
    session: AsyncSession,
    conversation: CareConversation,
    *,
    now: datetime | None = None,
) -> bool:
    if conversation.status != "ACTIVE":
        return False
    current = now or datetime.now(UTC)
    last_out = await _latest_message(session, conversation.id, "OUT")
    if not last_out:
        return False
    out_at = utc(last_out.sent_at) or utc(last_out.created_at)
    if out_at is None or out_at > current - AI_REPLY_TIMEOUT:
        return False

    last_in = await _latest_message(session, conversation.id, "IN")
    in_at = utc(last_in.created_at) if last_in else None
    if in_at is not None and in_at > out_at:
        return False

    context = dict(conversation.booking_context or {})
    context.update(
        {
            "stage": "AI_INACTIVITY_TIMEOUT",
            "ai_inactivity_locked_at": current.isoformat(),
            "ai_inactivity_after_message_at": out_at.isoformat(),
            "ai_inactivity_timeout_minutes": 10,
        }
    )
    conversation.booking_context = context
    conversation.status = "WAITING_NEXT_TOOTH"
    conversation.summary = (
        "AI conversation closed after 10 minutes without a patient reply. "
        "AI remains inactive until the next scheduled tooth outreach is actually sent."
    )
    return True


async def expire_patient_ai_inactivity(
    session: AsyncSession,
    *,
    patient_id: uuid.UUID,
    now: datetime | None = None,
) -> bool:
    active = list(
        (
            await session.scalars(
                select(CareConversation).where(
                    CareConversation.patient_id == patient_id,
                    CareConversation.status == "ACTIVE",
                )
            )
        ).all()
    )
    expired = False
    for conversation in active:
        expired = await expire_conversation_for_ai_inactivity(
            session, conversation, now=now
        ) or expired
    return expired


async def sweep_ai_inactivity(session: AsyncSession, *, now: datetime | None = None) -> int:
    active = list(
        (
            await session.scalars(
                select(CareConversation).where(CareConversation.status == "ACTIVE")
            )
        ).all()
    )
    count = 0
    for conversation in active:
        if await expire_conversation_for_ai_inactivity(session, conversation, now=now):
            count += 1
    if count:
        await session.flush()
    return count
