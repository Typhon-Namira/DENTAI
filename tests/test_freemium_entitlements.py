import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.clinic_resolution.service import ResolvedClinic
from app.core.errors import AppError
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
