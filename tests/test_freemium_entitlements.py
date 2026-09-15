import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.clinic_resolution.service import ResolvedClinic
from app.core.errors import AppError
from app.database.control_models import AccessRequest, ClinicRegistry, PlatformSettings
from app.platform import freemium
from app.platform.entitlements import (
    FREE_FOLLOWUP_TEETH_PER_OPG_LIMIT,
    FREE_OPG_PER_PATIENT_LIMIT,
    FREE_PATIENT_LIMIT,
    entitlement_payload,
    require_product_access,
    seconds_remaining,
    subscription_state,
)


def clinic(*, plan="FREE", state="ACTIVE", expires_delta=timedelta(hours=24)):
    now = datetime.now(UTC)
    return ResolvedClinic(
        id=uuid.uuid4(),
        slug="test-clinic",
        name="Test Clinic",
        database_url="postgresql+asyncpg://example",
        allowed_origins=[],
        subscription_plan=plan,
        subscription_state=state,
        subscription_starts_at=now,
        subscription_expires_at=now + expires_delta if expires_delta is not None else None,
        free_trial_started_at=now if plan == "FREE" else None,
        upgrade_requested_at=None,
    )


def test_free_entitlements_are_exact_product_limits():
    payload = entitlement_payload(clinic())
    assert payload == {
        "patient_limit": FREE_PATIENT_LIMIT,
        "opg_per_patient_limit": FREE_OPG_PER_PATIENT_LIMIT,
        "followup_teeth_per_opg_limit": FREE_FOLLOWUP_TEETH_PER_OPG_LIMIT,
    }
    assert payload["patient_limit"] == 3
    assert payload["opg_per_patient_limit"] == 1
    assert payload["followup_teeth_per_opg_limit"] == 1


def test_free_trial_becomes_expired_without_disabling_tenant_identity():
    row = clinic(expires_delta=timedelta(seconds=-1))
    assert subscription_state(row) == "FREE_EXPIRED"
    assert seconds_remaining(row) == 0
    with pytest.raises(AppError) as caught:
        require_product_access(row)
    assert caught.value.code == "SUBSCRIPTION_EXPIRED"


def test_payment_review_blocks_product_access_but_keeps_subscription_context():
    row = clinic(state="PAYMENT_REVIEW")
    assert subscription_state(row) == "PAYMENT_REVIEW"
    with pytest.raises(AppError) as caught:
        require_product_access(row)
    assert caught.value.code == "SUBSCRIPTION_PAYMENT_REVIEW"


def test_premium_has_no_free_usage_caps():
    row = clinic(plan="PREMIUM", expires_delta=timedelta(days=30))
    assert subscription_state(row) == "ACTIVE"
    assert entitlement_payload(row) == {
        "patient_limit": None,
        "opg_per_patient_limit": None,
        "followup_teeth_per_opg_limit": None,
    }


@pytest.mark.asyncio
async def test_premium_activation_preserves_same_clinic_and_tenant_database(monkeypatch):
    clinic_id = uuid.uuid4()
    original_dsn = "encrypted:stable-tenant-database"
    registry = ClinicRegistry(
        id=clinic_id,
        slug="stable-clinic",
        name="Stable Clinic",
        is_active=True,
        encrypted_database_url=original_dsn,
        allowed_origins=[],
        feature_flags={"free_trial_used": True},
        subscription_plan="FREE",
        subscription_state="PAYMENT_REVIEW",
        subscription_starts_at=datetime.now(UTC) - timedelta(hours=24),
        subscription_expires_at=datetime.now(UTC) - timedelta(seconds=1),
        free_trial_started_at=datetime.now(UTC) - timedelta(hours=24),
        upgrade_requested_at=datetime.now(UTC),
    )
    request = AccessRequest(
        id=uuid.uuid4(),
        clinic_name="Stable Clinic",
        country="Armenia",
        city="Yerevan",
        contact_name="Director",
        contact_role="Director",
        email="clinic@example.com",
        phone="+37400000000",
        dentists_count=1,
        branches_count=1,
        status="PAYMENT_REVIEW",
        activated_clinic_id=clinic_id,
    )
    settings = PlatformSettings(
        id=1,
        plan_name="Teta2",
        subscription_days=30,
        price_amount=49000,
        price_currency="AMD",
        payment_recipient="Teta2",
        payment_card="1234",
        payment_bank_details="bank",
        payment_email_subject="Payment",
        payment_email_intro="Payment",
        activation_email_subject="Activated",
        activation_email_intro="Activated",
    )

    class FakeSession:
        async def get(self, model, key):
            assert model is ClinicRegistry
            assert key == clinic_id
            return registry

    async def fake_email(*args, **kwargs):
        return None

    monkeypatch.setattr(freemium, "send_logged_email", fake_email)
    returned, expires_at = await freemium.activate_existing_premium(
        FakeSession(),
        request=request,
        settings=settings,
        reference="bank-ref",
        proof_note="verified",
    )

    assert returned is registry
    assert returned.id == clinic_id
    assert returned.encrypted_database_url == original_dsn
    assert returned.subscription_plan == "PREMIUM"
    assert returned.subscription_state == "ACTIVE"
    assert expires_at > datetime.now(UTC) + timedelta(days=29)
    assert request.activated_clinic_id == clinic_id
