import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.care import service as care_service
from app.care.booking_links import booking_url
from app.care.groq import care_outreach_drafts
from app.care.language import language_for_phone
from app.care.models import CareConversation, CareConversationMessage, CarePlan, CarePlanItem
from app.database.models import DentalFinding, FindingReview, Patient
from app.outreach.whatsapp_client import WhatsAppServiceClient, WhatsAppServiceError

_BUTTON_TEXT = {
    "hy": "Ընտրել այցի ժամ",
    "ru": "Выбрать время",
    "fa": "رزرو زمان چکاپ",
    "tr": "Kontrol saati seç",
    "en": "Book check-up",
}


def _is_confirmed(finding: DentalFinding | None) -> bool:
    return bool(finding and finding.review_status == FindingReview.CONFIRMED)


async def start_or_continue_outreach_with_booking(
    session: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    clinic_name: str,
    patient: Patient,
    plan: CarePlan,
    items: list[CarePlanItem],
) -> CareConversation | None:
    """Send individualized, phone-localized follow-up with a signed booking CTA."""
    phone = care_service._safe_phone(patient.whatsapp_phone or patient.phone)
    if not phone or not items:
        return None

    language = language_for_phone(phone, plan.language or "en")
    plan.language = language
    conversation = await care_service._conversation(
        session, patient=patient, plan=plan, phone=phone
    )
    conversation.language = language
    prior_item_ids = set(
        (
            await session.scalars(
                select(CareConversationMessage.care_plan_item_id).where(
                    CareConversationMessage.conversation_id == conversation.id,
                    CareConversationMessage.direction == "OUT",
                    CareConversationMessage.care_plan_item_id.is_not(None),
                )
            )
        ).all()
    )
    pending = [item for item in items if item.id not in prior_item_ids]
    if not pending:
        return conversation

    settings = await care_service.settings_for_branch(session, patient.branch_id)
    findings = {
        item.finding_id: await session.get(DentalFinding, item.finding_id) for item in pending
    }
    drafts = await care_outreach_drafts(
        language=language,
        patient_name=f"{patient.first_name} {patient.last_name}".strip(),
        clinic_name=clinic_name,
        care_items=[
            {
                "tooth": item.tooth_fdi,
                "finding": item.finding_type,
                "window": item.recommended_window,
                "rationale": item.rationale,
                "clinician_reviewed": _is_confirmed(findings.get(item.finding_id)),
                "visit_outcome": item.outcome,
            }
            for item in pending
        ],
        booking_instructions=settings.booking_instructions,
    )
    if any(not drafts.get(item.tooth_fdi) for item in pending):
        raise WhatsAppServiceError("AI_MESSAGE_GENERATION_UNAVAILABLE", 503)

    client = WhatsAppServiceClient()
    for item in pending:
        url = booking_url(
            clinic_id=clinic_id,
            branch_id=patient.branch_id,
            doctor_id=plan.doctor_id,
            patient_id=patient.id,
            care_plan_id=plan.id,
            care_plan_item_id=item.id,
        )
        message = drafts[item.tooth_fdi]
        crop = (
            await care_service._finding_crop(session, plan, item)
            if settings.attach_tooth_image and item.image_required
            else None
        )
        result = await client.send_booking_message(
            clinic_id,
            phone,
            message,
            url,
            _BUTTON_TEXT.get(language, _BUTTON_TEXT["en"]),
            image=crop,
        )
        session.add(
            CareConversationMessage(
                conversation_id=conversation.id,
                care_plan_item_id=item.id,
                direction="OUT",
                body=message,
                language=language,
                status="SENT",
                sent_at=datetime.now(UTC),
                attempt_count=1,
                provider_message_id=result.get("message_id"),
                message_metadata={
                    "clinic": clinic_name,
                    "kind": "finding_followup",
                    "tooth_fdi": item.tooth_fdi,
                    "image_attached": bool(crop),
                    "booking_url": url,
                    "booking_flow": "SIGNED_LINK_V1",
                    "booking_cta": True,
                },
            )
        )
        item.message_preview = message
        item.status = "CONTACTED"

    conversation.last_message_at = datetime.now(UTC)
    conversation.summary = (
        f"{len(pending)} individualized tooth follow-up message(s) sent with booking CTA. "
        "Awaiting appointment request."
    )
    return conversation


def install_booking_outreach() -> None:
    care_service.start_or_continue_outreach = start_or_continue_outreach_with_booking
