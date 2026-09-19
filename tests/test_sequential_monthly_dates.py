from datetime import UTC, datetime

from app.care.models import CarePlanItem
from app.care.outreach_invariants import align_sequence_schedule, monthly_sequence_at
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


def test_monthly_sequence_at_keeps_one_calendar_month_between_teeth():
    first = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)

    assert monthly_sequence_at(first, "UTC", 0) == datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
    assert monthly_sequence_at(first, "UTC", 1) == datetime(2026, 10, 19, 12, 0, tzinfo=UTC)
    assert monthly_sequence_at(first, "UTC", 2) == datetime(2026, 11, 19, 12, 0, tzinfo=UTC)
    assert monthly_sequence_at(first, "UTC", 3) == datetime(2026, 12, 19, 12, 0, tzinfo=UTC)


def test_align_sequence_schedule_repairs_duplicate_legacy_dates():
    duplicate = datetime(2026, 10, 19, 6, 0, tzinfo=UTC)
    items = [
        CarePlanItem(
            sequence_order=index,
            target_followup_at=duplicate,
            conversation_start_at=duplicate if index == 1 else None,
        )
        for index in range(1, 5)
    ]

    changed = align_sequence_schedule(
        items,
        "UTC",
        first_start=duplicate,
        force_rebase=True,
    )

    assert changed
    assert [item.target_followup_at for item in items] == [
        datetime(2026, 10, 19, 6, 0, tzinfo=UTC),
        datetime(2026, 11, 19, 6, 0, tzinfo=UTC),
        datetime(2026, 12, 19, 6, 0, tzinfo=UTC),
        datetime(2027, 1, 19, 6, 0, tzinfo=UTC),
    ]
    assert [item.conversation_start_at for item in items] == [
        item.target_followup_at for item in items
    ]
