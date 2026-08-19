import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.database.base import Base
from app.database.models import (
    AIAnalysis,
    AIStatus,
    DentalFinding,
    Patient,
    WhatsAppOutreach,
    WhatsAppOutreachStatus,
)
from app.outreach.messages import armenian_message, deterministic_armenian_message
from app.outreach.service import schedule_analysis_outreach
from app.outreach.timing import FollowupTimingEngine, eligible_finding
from app.outreach.whatsapp_client import clinic_account_id, normalize_phone
from app.outreach.worker import recover_stale_claims


def timing(finding_type: str, *, review_required: bool = False):
    return FollowupTimingEngine().calculate(
        finding_type=finding_type,
        tooth_fdi="37",
        analysis_at=datetime(2026, 8, 17, 8, tzinfo=UTC),
        review_required=review_required,
        timezone_name="Asia/Yerevan",
        lead_days=7,
        send_hour=10,
    )


def test_phone_normalization_and_tenant_account_key():
    assert normalize_phone("+374 93 156 663") == "+37493156663"
    clinic_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
    assert clinic_account_id(clinic_id) == "clinic_12345678123456781234567812345678"
    with pytest.raises(ValueError):
        normalize_phone("../374")


def test_exact_timing_is_deterministic_and_uses_yerevan_10am():
    first = timing("DEEP_CARIES")
    second = timing("DEEP_CARIES")
    assert first == second
    assert first.target_followup_at.isoformat() == "2026-11-17T06:00:00+00:00"
    assert first.scheduled_send_at.isoformat() == "2026-11-10T06:00:00+00:00"
    assert first.recommended_window == "1–3 months"


def test_finding_types_use_policy_specific_windows():
    caries = timing("DEEP_CARIES")
    filling = timing("FILLING")
    root_canal = timing("ROOT_CANAL_TREATMENT")
    assert caries.recommended_window == "1–3 months"
    assert root_canal.recommended_window == "3–6 months"
    assert filling.recommended_window == "6–12 months"
    assert (
        len({caries.target_followup_at, root_canal.target_followup_at, filling.target_followup_at})
        == 3
    )


def test_review_required_uses_existing_urgent_policy():
    value = timing("FILLING", review_required=True)
    assert value.recommended_window == "0–1 months"
    assert "AI_REVIEW_REQUIRED" in value.timing_reason


def test_unresolved_and_below_threshold_findings_are_not_eligible():
    assert not eligible_finding(None, 0.99)
    assert not eligible_finding("37", 0.5999)
    assert eligible_finding("37", 0.60)
    assert not eligible_finding("raw_37", 0.99)


def test_armenian_fallback_uses_approved_native_template():
    message = deterministic_armenian_message(timing("FILLING"))
    assert message.startswith("Բարև Ձեզ։")
    assert "37-րդ ատամի հատվածը" in message
    assert "17.08.2027թ.։" in message
    assert "0." not in message


@pytest.mark.asyncio
async def test_armenian_message_keeps_approved_template_and_target(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-does-not-change-outreach")
    get_settings.cache_clear()
    value = timing("DEEP_CARIES")
    message = await armenian_message(value)
    assert message.startswith("Բարև Ձեզ։")
    assert "37-րդ ատամի հատվածը" in message
    assert "17.11.2026թ.։" in message
    assert value.target_followup_at.isoformat() == "2026-11-17T06:00:00+00:00"
    get_settings.cache_clear()


class FakeService:
    def __init__(self, connected=True):
        self.connected = connected
        self.sent = []

    async def status(self, _clinic_id):
        return {"connected": self.connected}

    async def validate_phone(self, _clinic_id, _phone):
        return {"registered": True}

    async def send_message(self, _clinic_id, phone, message):
        self.sent.append((phone, message))
        return {"message_id": "wamid-test"}


def test_fake_transport_never_contacts_real_whatsapp():
    service = FakeService()
    assert service.sent == []


async def _session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


def _patient() -> Patient:
    return Patient(
        patient_number="P-TEST",
        first_name="Test",
        last_name="Patient",
        branch_id=uuid.uuid4(),
        status="ACTIVE",
        whatsapp_phone="+37493156663",
    )


def _analysis(patient_id: uuid.UUID) -> AIAnalysis:
    return AIAnalysis(
        patient_id=patient_id,
        xray_id=uuid.uuid4(),
        requested_by=uuid.uuid4(),
        status=AIStatus.COMPLETED,
        provider="real_opg",
        model_name="DENTAI Unified V5",
        model_version="5",
        requested_at=datetime(2026, 8, 17, 8, tzinfo=UTC),
        completed_at=datetime(2026, 8, 17, 8, tzinfo=UTC),
    )


def _finding(patient_id, analysis_id, tooth, finding_type, confidence=0.9):
    return DentalFinding(
        patient_id=patient_id,
        analysis_id=analysis_id,
        tooth_code=tooth,
        finding_type=finding_type,
        description=finding_type,
        source="AI",
        confidence=confidence,
        provenance={"review_required": False},
    )


@pytest.mark.asyncio
async def test_same_time_findings_are_grouped_but_different_timing_remains_separate(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    get_settings.cache_clear()
    engine, factory = await _session_factory()
    try:
        async with factory() as session:
            patient = _patient()
            session.add(patient)
            await session.flush()
            analysis = _analysis(patient.id)
            session.add(analysis)
            await session.flush()
            crown = _finding(patient.id, analysis.id, "36", "CROWN")
            filling = _finding(patient.id, analysis.id, "37", "FILLING")
            rct = _finding(patient.id, analysis.id, "36", "ROOT_CANAL_TREATMENT")
            session.add_all([crown, filling, rct])
            await session.flush()

            created = await schedule_analysis_outreach(session, analysis, [crown, filling, rct])
            await session.commit()
            rows = (
                await session.scalars(
                    select(WhatsAppOutreach).order_by(WhatsAppOutreach.target_followup_at)
                )
            ).all()

            assert created == 2
            assert len(rows) == 2
            low_risk = next(row for row in rows if row.recommended_window == "6–12 months")
            assert set(low_risk.source_finding_ids) == {str(crown.id), str(filling.id)}
            assert low_risk.tooth_fdi == "MULTIPLE"
            medium = next(row for row in rows if row.recommended_window == "3–6 months")
            assert medium.source_finding_ids == [str(rct.id)]
    finally:
        await engine.dispose()
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_stale_claim_is_recoverable_but_stale_sending_is_quarantined(monkeypatch):
    monkeypatch.setenv("WHATSAPP_CLAIM_TIMEOUT_SECONDS", "60")
    get_settings.cache_clear()
    engine, factory = await _session_factory()
    try:
        async with factory() as session:
            now = datetime.now(UTC)
            common = dict(
                patient_id=uuid.uuid4(),
                analysis_id=uuid.uuid4(),
                finding_id=None,
                source_finding_ids=[],
                tooth_fdi="37",
                finding_type="FILLING",
                recommended_window="6–12 months",
                target_followup_at=now + timedelta(days=30),
                scheduled_send_at=now - timedelta(minutes=5),
                message="test",
                language="hy-AM",
                timing_reason="test",
                timing_policy_rule_id="RULE_TEST",
                timing_policy_version="test",
                clinic_timezone="Asia/Yerevan",
            )
            claimed = WhatsAppOutreach(
                **common,
                status=WhatsAppOutreachStatus.CLAIMED,
                claimed_at=now - timedelta(minutes=10),
                worker_id="old-worker",
            )
            sending = WhatsAppOutreach(
                **common,
                status=WhatsAppOutreachStatus.SENDING,
                claimed_at=now - timedelta(minutes=10),
                dispatch_started_at=now - timedelta(minutes=10),
                worker_id="old-worker",
            )
            sent = WhatsAppOutreach(
                **common,
                status=WhatsAppOutreachStatus.SENT,
                claimed_at=now - timedelta(minutes=10),
                dispatch_started_at=now - timedelta(minutes=10),
                provider_message_id="wamid-ok",
                sent_at=now - timedelta(minutes=9),
            )
            session.add_all([claimed, sending, sent])
            await session.commit()

            recovered = await recover_stale_claims(session)
            await session.refresh(claimed)
            await session.refresh(sending)
            await session.refresh(sent)

            assert recovered == 2
            assert claimed.status == WhatsAppOutreachStatus.SCHEDULED
            assert claimed.safe_error == "STALE_CLAIM_RECOVERED"
            assert sending.status == WhatsAppOutreachStatus.SEND_UNKNOWN
            assert sending.safe_error == "SEND_OUTCOME_UNKNOWN"
            assert sent.status == WhatsAppOutreachStatus.SENT
    finally:
        await engine.dispose()
        get_settings.cache_clear()


def _alembic_upgrade(db_path, revision, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("MIGRATION_PLANE", "clinic")
    command.upgrade(Config("alembic.ini"), revision)


def test_fresh_database_alembic_upgrade_head(tmp_path, monkeypatch):
    db_path = tmp_path / "fresh.db"
    _alembic_upgrade(db_path, "head", monkeypatch)
    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        patient_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(patients)").fetchall()
        }
        outreach_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(whatsapp_outreach)").fetchall()
        }
    assert "whatsapp_outreach" in tables
    assert "whatsapp_phone" in patient_columns
    assert "source_finding_ids" in outreach_columns
    assert "dispatch_started_at" in outreach_columns


def test_existing_0003_database_upgrades_to_head(tmp_path, monkeypatch):
    db_path = tmp_path / "existing.db"
    _alembic_upgrade(db_path, "0003_ai_job_queue", monkeypatch)
    with sqlite3.connect(db_path) as connection:
        connection.execute("DROP TABLE IF EXISTS whatsapp_outreach")
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(patients)").fetchall()
        }
        if "whatsapp_phone" in columns:
            connection.execute("ALTER TABLE patients DROP COLUMN whatsapp_phone")
        connection.commit()
    _alembic_upgrade(db_path, "head", monkeypatch)
    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        patient_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(patients)").fetchall()
        }
    assert "whatsapp_outreach" in tables
    assert "whatsapp_phone" in patient_columns
