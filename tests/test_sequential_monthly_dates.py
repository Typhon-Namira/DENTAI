from datetime import UTC, datetime

from app.care.models import CarePlanItem
from app.care.sequential import _approval_schedule, _monthly_contact


def test_monthly_contact_keeps_same_local_calendar_day():
    first = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)

    second = _monthly_contact(first, "UTC", 1)
    third = _monthly_contact(first, "UTC", 2)
    fourth = _monthly_contact(first, "UTC", 3)

    assert second == datetime(2026, 6, 18, 12, 0, tzinfo=UTC)
    assert third == datetime(2026, 7, 18, 12, 0, tzinfo=UTC)
    assert fourth == datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


def test_approval_schedule_preserves_clinician_selected_date():
    system_default = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
    clinician_selected = datetime(2026, 9, 24, 9, 30, tzinfo=UTC)
    item = CarePlanItem(target_followup_at=clinician_selected)

    assert _approval_schedule(item, system_default) == clinician_selected
