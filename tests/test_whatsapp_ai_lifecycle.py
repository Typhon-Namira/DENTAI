import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.care.conversation_runtime import process_staged_inbound_message
from app.care.models import CareConversation, CarePlan, CarePlanItem
from app.care.sequential import record_scheduled_outreach_sent
from app.database.base import Base
from app.database.models import Patient, WhatsAppOutreach, WhatsAppOutreachStatus


async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_inactive_conversation_does_not_reach_ai(monkeypatch):
    engine, factory = await session_factory()
    branch_id = uuid.uuid4()
    try:
        async with factory() as session:
            patient = Patient(
                patient_number="AI-OFF-1",
                first_name="Ani",
                last_name="Test",
                branch_id=branch_id,
                status="ACTIVE",
                whatsapp_phone="+37493123456",
            )
            session.add(patient)
            await session.flush()
            plan = CarePlan(
                patient_id=patient.id,
                analysis_id=uuid.uuid4(),
                branch_id=branch_id,
                doctor_id=uuid.uuid4(),
                status="ACTIVE",
                language="en",
            )
            session.add(plan)
            await session.flush()
            session.add(
                CareConversation(
                    patient_id=patient.id,
                    care_plan_id=plan.id,
                    branch_id=branch_id,
                    whatsapp_phone=patient.whatsapp_phone,
                    language="en",
                    status="WAITING_NEXT_TOOTH",
                    booking_context={"stage": "APPOINTMENT_CONFIRMED"},
                )
            )
            await session.flush()

            async def unexpected_agent(**_kwargs):
                raise AssertionError("AI must stay off after final appointment confirmation")

            monkeypatch.setattr("app.care.conversation_runtime._agent", unexpected_agent)
            result = await process_staged_inbound_message(
                session,
                clinic_id=uuid.uuid4(),
                clinic_name="Clinic",
                phone=patient.whatsapp_phone,
                text="Thanks, see you next week",
                provider_message_id="after-final-confirmation",
            )

            assert result == {"handled": False, "reason": "conversation_not_active"}
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_next_tooth_outreach_reactivates_ai_and_resets_booking_stage():
    engine, factory = await session_factory()
    branch_id = uuid.uuid4()
    try:
        async with factory() as session:
            patient = Patient(
                patient_number="AI-NEXT-1",
                first_name="Ani",
                last_name="Test",
                branch_id=branch_id,
                status="ACTIVE",
                whatsapp_phone="+37493123456",
            )
            session.add(patient)
            await session.flush()
            plan = CarePlan(
                patient_id=patient.id,
                analysis_id=uuid.uuid4(),
                branch_id=branch_id,
                doctor_id=uuid.uuid4(),
                status="ACTIVE",
                language="en",
            )
            session.add(plan)
            await session.flush()
            item = CarePlanItem(
                care_plan_id=plan.id,
                finding_id=uuid.uuid4(),
                tooth_fdi="24",
                finding_type="CARIES",
                confidence=0.8,
                recommended_window="within 30 days",
                target_followup_at=datetime.now(UTC) + timedelta(days=30),
                status="FOLLOWUP_READY",
                rationale="Follow-up recommended",
                message_preview="Opening message",
                appointment_required=True,
                image_required=False,
                sequence_order=2,
                priority_score=80,
                priority_level="HIGH",
            )
            session.add(item)
            await session.flush()
            conversation = CareConversation(
                patient_id=patient.id,
                care_plan_id=plan.id,
                branch_id=branch_id,
                whatsapp_phone=patient.whatsapp_phone,
                language="en",
                status="WAITING_NEXT_TOOTH",
                booking_context={
                    "sequence_mode": True,
                    "stage": "APPOINTMENT_CONFIRMED",
                    "appointment_id": "old-appointment",
                    "confirmed_slot": "old-slot",
                    "last_visit_outcome": "TREATED",
                },
            )
            session.add(conversation)
            await session.flush()
            outreach = WhatsAppOutreach(
                patient_id=patient.id,
                analysis_id=plan.analysis_id,
                finding_id=item.finding_id,
                source_finding_ids=[str(item.finding_id)],
                tooth_fdi=item.tooth_fdi,
                finding_type=item.finding_type,
                recommended_window=item.recommended_window,
                target_followup_at=item.target_followup_at,
                scheduled_send_at=datetime.now(UTC),
                message="Fresh AI outreach for tooth 24",
                language="en",
                status=WhatsAppOutreachStatus.SENT,
                timing_reason=item.rationale,
                timing_policy_rule_id="CARE_SEQUENCE",
                timing_policy_version="1.0",
                clinic_timezone="Asia/Yerevan",
                include_image=False,
                sent_at=datetime.now(UTC),
                attempt_count=1,
            )
            session.add(outreach)
            await session.flush()

            await record_scheduled_outreach_sent(
                session,
                outreach=outreach,
                provider_message_id="next-tooth-message",
            )
            await session.flush()

            assert conversation.status == "ACTIVE"
            assert conversation.booking_context["stage"] == "WAITING_PATIENT_REPLY"
            assert conversation.booking_context["active_item_id"] == str(item.id)
            assert conversation.booking_context["last_visit_outcome"] == "TREATED"
            assert "appointment_id" not in conversation.booking_context
            assert "confirmed_slot" not in conversation.booking_context
    finally:
        await engine.dispose()
