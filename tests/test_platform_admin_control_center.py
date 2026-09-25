from datetime import UTC, datetime, timedelta

import pytest

from app.clinic_resolution.service import ResolvedClinic
from app.core.errors import AppError
from app.database.control_models import ClinicRegistry
from app.platform.admin_control_service import clinic_category, clinic_operational_state
from app.platform.entitlements import require_product_access, subscription_state


def clinic(**overrides):
    now = datetime.now(UTC)
    values = {
        "slug": "test-clinic",
        "name": "Test Clinic",
        "is_active": True,
        "encrypted_database_url": "encrypted",
        "allowed_origins": [],
        "feature_flags": {},
        "subscription_plan": "FREE",
        "subscription_state": "ACTIVE",
        "subscription_source": "FREE",
        "subscription_starts_at": now,
        "subscription_expires_at": now + timedelta(hours=24),
        "free_trial_started_at": now,
    }
    values.update(overrides)
    return ClinicRegistry(**values)


def test_free_paid_and_gift_accounts_are_separate():
    assert clinic_category(clinic()) == "FREE"
    assert (
        clinic_category(clinic(subscription_plan="PREMIUM", subscription_source="FREE")) == "PAID"
    )
    assert (
        clinic_category(clinic(subscription_plan="PREMIUM", subscription_source="GIFT")) == "GIFT"
    )


def test_archived_and_expired_states_are_operationally_distinct():
    assert clinic_operational_state(clinic(is_active=False)) == "ARCHIVED"
    assert (
        clinic_operational_state(
            clinic(subscription_expires_at=datetime.now(UTC) - timedelta(minutes=1))
        )
        == "EXPIRED"
    )
    assert clinic_operational_state(clinic(subscription_state="PAYMENT_REVIEW")) == "PAYMENT_REVIEW"


def test_suspended_subscription_is_blocked_but_reported_distinctly():
    resolved = ResolvedClinic(
        id=clinic().id,
        slug="test-clinic",
        name="Test Clinic",
        database_url="sqlite+aiosqlite:///./test.db",
        allowed_origins=[],
        subscription_plan="PREMIUM",
        subscription_state="SUSPENDED",
        subscription_starts_at=datetime.now(UTC) - timedelta(days=10),
        subscription_expires_at=datetime.now(UTC) + timedelta(days=20),
        free_trial_started_at=None,
        upgrade_requested_at=None,
    )

    assert subscription_state(resolved) == "SUSPENDED"
    with pytest.raises(AppError) as error:
        require_product_access(resolved)

    assert error.value.code == "SUBSCRIPTION_SUSPENDED"
    assert error.value.status_code == 403
