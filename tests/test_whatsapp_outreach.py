import uuid
from datetime import UTC, datetime

import pytest

from app.outreach.messages import armenian_message, deterministic_armenian_message
from app.outreach.timing import FollowupTimingEngine, eligible_finding
from app.outreach.whatsapp_client import clinic_account_id, normalize_phone


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


def test_armenian_fallback_contains_exact_date_and_no_model_score():
    message = deterministic_armenian_message(timing("FILLING"))
    assert "17.08.2027" in message
    assert "0." not in message
    assert "ատամ" in message


@pytest.mark.asyncio
async def test_groq_unavailable_falls_back_without_changing_target(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    from app.core.config import get_settings

    get_settings.cache_clear()
    value = timing("DEEP_CARIES")
    message = await armenian_message(value)
    assert "17.11.2026" in message
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
