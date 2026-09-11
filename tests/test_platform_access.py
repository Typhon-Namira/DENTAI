import uuid
from datetime import UTC, datetime, timedelta

from app.database.control_models import ClinicRegistry
from app.platform.service import next_subscription_window, subscription_expired


def clinic(**overrides):
    values = {
        "slug": "clinic-test",
        "name": "Clinic Test",
        "is_active": True,
        "encrypted_database_url": "plain:sqlite+aiosqlite:///./test.db",
        "subscription_plan": "TETA2_CARE",
        "subscription_status": "ACTIVE",
        "subscription_started_at": None,
        "subscription_ends_at": None,
        "renewal_count": 0,
    }
    values.update(overrides)
    return ClinicRegistry(**values)


def test_new_subscription_window_is_exactly_30_days():
    start, end = next_subscription_window()
    assert end - start == timedelta(days=30)


def test_renewal_extends_from_existing_future_expiry():
    future = datetime.now(UTC) + timedelta(days=12)
    row = clinic(subscription_ends_at=future)
    start, end = next_subscription_window(row)
    assert abs((start - future).total_seconds()) < 1
    assert end - start == timedelta(days=30)


def test_expired_and_suspended_subscriptions_are_blocked():
    expired = clinic(subscription_ends_at=datetime.now(UTC) - timedelta(seconds=1))
    suspended = clinic(subscription_status="SUSPENDED", subscription_ends_at=datetime.now(UTC) + timedelta(days=5))
    assert subscription_expired(expired) is True
    assert subscription_expired(suspended) is True


def test_legacy_active_clinic_without_expiry_remains_available():
    row = clinic(subscription_ends_at=None)
    assert subscription_expired(row) is False


def test_registry_plan_is_teta2_care():
    row = clinic(id=uuid.uuid4())
    assert row.subscription_plan == "TETA2_CARE"
