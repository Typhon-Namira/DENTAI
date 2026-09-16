import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.care.models import CareConversation, CareConversationMessage, CarePlan, CarePlanItem
from app.care.outreach_invariants import (
    add_calendar_months,
    expire_conversation_for_ai_inactivity,
    supersede_patient_schedule_for_new_xray,
    validate_outreach_before_dispatch,
)
from app.database.base import Base
from app.database.models import (
    AIAnalysis,
    AIStatus,
    FollowUp,
    Patient,
    WhatsAppOutreach,
    WhatsAppOutreachStatus,
    XRay,
)


async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


def test_calendar_month_schedule_is_anchored_to_exact_day_when_possible():
    start = datetime(2027, 1, 31, 16, 0, tzinfo=UTC)
    assert add_calendar_months(start, 1) == datetime(2027, 2, 28, 16, 0, tzinfo=UTC)
    assert add_calendar_months(start, 2) == datetime(2027, 3, 31, 16, 0, tzinfo=UTC)
    assert add_calendar_months(start, 3) == datetime(2027, 4, 30, 16, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_ai_conversation_closes_after_ten_minutes_without_patient_reply():
    engine, factory = await session_factory()
    branch_id = uuid.uuid4()
    now = datetime.now(UTC)
    try:
        async with factory() as session:
            patient = Patient(
                patient_number="TIMEOUT-1",
                first_name="Ani",
                last_name="Test",
                branch_id=branch_id,
                status="ACTIVE",
                whatsapp_phone="+37493120001",
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
            conversation = CareConversation(
                patient_id=patient.id,
                care_plan_id=plan.id,
                branch_id=branch_id,
                whatsapp_phone=patient.whatsapp_phone,
                language="en",
                status="ACTIVE",
                booking_context={"stage": "WAITING_PATIENT_REPLY"},
                last_message_at=now - timedelta(minutes=11),
            )
            session.add(conversation)
            await session.flush()
            session.add(
                CareConversationMessage(
                    conversation_id=conversation.id,
                    direction="OUT",
                    body="AI follow-up",
                    language="en",
                    status="SENT",
                    created_at=now - timedelta(minutes=11),
                    sent_at=now - timedelta(minutes=11),
                    provider_message_id="timeout-out-1",
                    message_metadata={"kind": "care_reply"},
                )
            )
            await session.flush()

            expired = await expire_conversation_for_ai_inactivity(
                session, conversation, now=now
            )

            assert expired is True
            assert conversation.status == "WAITING_NEXT_TOOTH"
            assert conversation.booking_context["stage"] == "AI_INACTIVITY_TIMEOUT"
            assert conversation.booking_context["ai_inactivity_timeout_minutes"] == 10
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_ai_timeout_resets_when_patient_replies_after_latest_ai_message():
    engine, factory = await session_factory()
    branch_id = uuid.uuid4()
    now = datetime.now(UTC)
    try:
        async with factory() as session:
            patient = Patient(
                patient_number="TIMEOUT-2",
                first_name="Ani",
                last_name="Reply",
                branch_id=branch_id,
                status="ACTIVE",
                whatsapp_phone="+37493120002",
            )
            session.add(patient)
            await session.flush()
            conversation = CareConversation(
                patient_id=patient.id,
                branch_id=branch_id,
                whatsapp_phone=patient.whatsapp_phone,
                language="en",
                status="ACTIVE",
                booking_context={"stage": "WAITING_PATIENT_REPLY"},
            )
            session.add(conversation)
            await session.flush()
            session.add_all(
                [
                    CareConversationMessage(
                        conversation_id=conversation.id,
                        direction="OUT",
                        body="AI follow-up",
                        language="en",
                        status="SENT",
                        created_at=now - timedelta(minutes=12),
                        sent_at=now - timedelta(minutes=12),
                        provider_message_id="timeout-out-2",
                        message_metadata={"kind": "care_reply"},
                    ),
                    CareConversationMessage(
                        conversation_id=conversation.id,
                        direction="IN",
                        body="Thanks",
                        language="en",
                        status="RECEIVED",
                        created_at=now - timedelta(minutes=5),
                        provider_message_id="timeout-in-2",
                        message_metadata={},
                    ),
                ]
            )
            await session.flush()

            expired = await expire_conversation_for_ai_inactivity(
                session, conversation, now=now
            )

            assert expired is False
            assert conversation.status == "ACTIVE"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_duplicate_sent_tooth_is_cancelled_before_second_dispatch():
    engine, factory = await session_factory()
    branch_id = uuid.uuid4()
    now = datetime.now(UTC)
    try:
        async with factory() as session:
            patient = Patient(
                patient_number="DEDUP-1",
                first_name="Aram",
                last_name="Test",
                branch_id=branch_id,
                status="ACTIVE",
                whatsapp_phone="+37493120003",
            )
            session.add(patient)
            await session.flush()
            xray = XRay(
                patient_id=patient.id,
                uploaded_by=uuid.uuid4(),
                branch_id=branch_id,
                storage_key="dedup-xray",
                original_filename="opg.jpg",
                mime_type="image/jpeg",
                size_bytes=100,
                uploaded_at=now - timedelta(hours=1),
            )
            session.add(xray)
            await session.flush()
            analysis = AIAnalysis(
                patient_id=patient.id,
                xray_id=xray.id,
                requested_by=uuid.uuid4(),
                status=AIStatus.COMPLETED,
                provider="test",
                model_name="test",
                model_version="1",
                completed_at=now - timedelta(minutes=50),
            )
            session.add(analysis)
            await session.flush()
            common = {
                "patient_id": patient.id,
                "analysis_id": analysis.id,
                "tooth_fdi": "11",
                "finding_type": "CARIES",
                "recommended_window": "soon",
                "target_followup_at": now + timedelta(days=30),
                "scheduled_send_at": now,
                "message": "Follow-up tooth 11",
                "language": "en",
                "timing_reason": "test",
                "timing_policy_rule_id": "TEST",
                "timing_policy_version": "1",
                "clinic_timezone": "Asia/Yerevan",
            }
            sent = WhatsAppOutreach(
                **common,
                status=WhatsAppOutreachStatus.SENT,
                sent_at=now - timedelta(seconds=5),
                provider_message_id="sent-11",
            )
            candidate = WhatsAppOutreach(
                **common,
                status=WhatsAppOutreachStatus.CLAIMED,
                worker_id="worker-2",
                claimed_at=now,
            )
            session.add_all([sent, candidate])
            await session.flush()

            valid, reason = await validate_outreach_before_dispatch(
                session, outreach=candidate
            )

            assert valid is False
            assert reason == "DUPLICATE_TOOTH_ALREADY_SENT"
            assert candidate.status == WhatsAppOutreachStatus.CANCELLED
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_new_opg_expires_old_future_schedule_without_deleting_history():
    engine, factory = await session_factory()
    branch_id = uuid.uuid4()
    now = datetime.now(UTC)
    try:
        async with factory() as session:
            patient = Patient(
                patient_number="OPG-RESET-1",
                first_name="Nare",
                last_name="Test",
                branch_id=branch_id,
                status="ACTIVE",
                whatsapp_phone="+37493120004",
            )
            session.add(patient)
            await session.flush()
            old_xray = XRay(
                patient_id=patient.id,
                uploaded_by=uuid.uuid4(),
                branch_id=branch_id,
                storage_key="old-opg",
                original_filename="old.jpg",
                mime_type="image/jpeg",
                size_bytes=100,
                uploaded_at=now - timedelta(days=10),
            )
            new_xray = XRay(
                patient_id=patient.id,
                uploaded_by=uuid.uuid4(),
                branch_id=branch_id,
                storage_key="new-opg",
                original_filename="new.jpg",
                mime_type="image/jpeg",
                size_bytes=100,
                uploaded_at=now,
            )
            session.add_all([old_xray, new_xray])
            await session.flush()
            analysis = AIAnalysis(
                patient_id=patient.id,
                xray_id=old_xray.id,
                requested_by=uuid.uuid4(),
                status=AIStatus.COMPLETED,
                provider="test",
                model_name="test",
                model_version="1",
                completed_at=now - timedelta(days=9),
            )
            session.add(analysis)
            await session.flush()
            plan = CarePlan(
                patient_id=patient.id,
                analysis_id=analysis.id,
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
                tooth_fdi="26",
                finding_type="CARIES",
                confidence=0.9,
                recommended_window="soon",
                target_followup_at=now + timedelta(days=20),
                status="SCHEDULED_FUTURE_TOOTH",
                rationale="test",
                sequence_order=2,
                priority_score=80,
                priority_level="HIGH",
                conversation_start_at=now + timedelta(days=20),
            )
            conversation = CareConversation(
                patient_id=patient.id,
                care_plan_id=plan.id,
                branch_id=branch_id,
                whatsapp_phone=patient.whatsapp_phone,
                language="en",
                status="WAITING_NEXT_TOOTH",
                booking_context={"sequence_mode": True},
            )
            outreach = WhatsAppOutreach(
                patient_id=patient.id,
                analysis_id=analysis.id,
                finding_id=item.finding_id,
                tooth_fdi="26",
                finding_type="CARIES",
                recommended_window="soon",
                target_followup_at=now + timedelta(days=20),
                scheduled_send_at=now + timedelta(days=20),
                message="future outreach",
                language="en",
                status=WhatsAppOutreachStatus.SCHEDULED,
                timing_reason="test",
                timing_policy_rule_id="TEST",
                timing_policy_version="1",
                clinic_timezone="Asia/Yerevan",
            )
            followup = FollowUp(
                patient_id=patient.id,
                doctor_id=plan.doctor_id,
                branch_id=branch_id,
                reason="Teta2 Care · tooth 26 · CARIES",
                due_at=now + timedelta(days=20),
                status="SCHEDULED",
                priority="HIGH",
                created_by=plan.doctor_id,
            )
            session.add_all([item, conversation, outreach, followup])
            await session.flush()

            result = await supersede_patient_schedule_for_new_xray(
                session,
                patient_id=patient.id,
                new_xray_id=new_xray.id,
            )

            assert result["outreach"] == 1
            assert outreach.status == WhatsAppOutreachStatus.CANCELLED
            assert outreach.safe_error == "SUPERSEDED_BY_NEW_OPG"
            assert plan.status == "SUPERSEDED_NEW_OPG"
            assert item.status == "SUPERSEDED_NEW_OPG"
            assert conversation.status == "WAITING_NEW_OPG_PLAN"
            assert followup.status == "SUPERSEDED_NEW_OPG"
    finally:
        await engine.dispose()
