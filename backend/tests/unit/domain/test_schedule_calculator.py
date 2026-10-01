from datetime import UTC, date, datetime, time
from uuid import uuid4

import pytest

from app.domain.entities.monitoring_schedule import MonitoringSchedule
from app.domain.services.schedule_calculator import calculate_next_occurrence


def schedule(kind="daily", *, hour=10, minute=0, zone="UTC", weekday=None, monthday=None):
    return MonitoringSchedule.create(
        configuration_id=uuid4(), recurrence_type=kind, enabled=True,
        execution_time=time(hour, minute), timezone=zone, now=datetime(2026, 1, 1, tzinfo=UTC),
        day_of_week=weekday, day_of_month=monthday,
    )


@pytest.mark.parametrize(("reference", "expected"), [
    (datetime(2026, 1, 1, 9, 59, tzinfo=UTC), datetime(2026, 1, 1, 10, tzinfo=UTC)),
    (datetime(2026, 1, 1, 10, 1, tzinfo=UTC), datetime(2026, 1, 2, 10, tzinfo=UTC)),
    (datetime(2026, 1, 1, 10, tzinfo=UTC), datetime(2026, 1, 2, 10, tzinfo=UTC)),
])
def test_daily_is_strictly_after_reference(reference, expected):
    assert calculate_next_occurrence(schedule(), reference) == expected


def test_weekly_selected_weekday_before_time_is_today_then_rolls_next_week():
    item = schedule("weekly", weekday=4)
    assert calculate_next_occurrence(item, datetime(2026, 1, 1, 9, tzinfo=UTC)) == datetime(2026, 1, 1, 10, tzinfo=UTC)
    assert calculate_next_occurrence(item, datetime(2026, 1, 1, 10, tzinfo=UTC)) == datetime(2026, 1, 8, 10, tzinfo=UTC)


@pytest.mark.parametrize(("reference", "expected"), [
    (datetime(2026, 4, 1, tzinfo=UTC), datetime(2026, 4, 30, 10, tzinfo=UTC)),
    (datetime(2026, 4, 30, 10, tzinfo=UTC), datetime(2026, 5, 31, 10, tzinfo=UTC)),
    (datetime(2027, 2, 1, tzinfo=UTC), datetime(2027, 2, 28, 10, tzinfo=UTC)),
    (datetime(2028, 2, 1, tzinfo=UTC), datetime(2028, 2, 29, 10, tzinfo=UTC)),
    (datetime(2026, 12, 31, 10, tzinfo=UTC), datetime(2027, 1, 31, 10, tzinfo=UTC)),
])
def test_monthly_clamps_and_rolls_year(reference, expected):
    assert calculate_next_occurrence(schedule("monthly", monthday=31), reference) == expected


def test_daily_occurrence_converts_configured_timezone_to_utc():
    assert calculate_next_occurrence(
        schedule(zone="America/Sao_Paulo", hour=9), datetime(2026, 1, 1, 11, tzinfo=UTC)
    ) == datetime(2026, 1, 1, 12, tzinfo=UTC)


def test_nonexistent_new_york_time_moves_forward_by_gap():
    item = schedule(zone="America/New_York", hour=2, minute=30)
    assert calculate_next_occurrence(item, datetime(2024, 3, 10, 6, tzinfo=UTC)) == datetime(2024, 3, 10, 7, 30, tzinfo=UTC)


def test_ambiguous_new_york_time_uses_first_instant():
    item = schedule(zone="America/New_York", hour=1, minute=30)
    assert calculate_next_occurrence(item, datetime(2024, 11, 3, 4, tzinfo=UTC)) == datetime(2024, 11, 3, 5, 30, tzinfo=UTC)


def test_non_hour_lord_howe_gap_preserves_position():
    item = schedule(zone="Australia/Lord_Howe", hour=2, minute=15)
    assert calculate_next_occurrence(item, datetime(2024, 10, 5, 15, tzinfo=UTC)) == datetime(2024, 10, 5, 15, 45, tzinfo=UTC)


def test_calculation_requires_aware_reference_and_enabled_schedule():
    item = schedule()
    with pytest.raises(ValueError):
        calculate_next_occurrence(item, datetime(2026, 1, 1))
    disabled = MonitoringSchedule.create(configuration_id=uuid4(), recurrence_type="daily", enabled=False,
        execution_time=time(10), timezone="UTC", now=datetime(2026, 1, 1, tzinfo=UTC))
    with pytest.raises(ValueError):
        calculate_next_occurrence(disabled, datetime(2026, 1, 1, tzinfo=UTC))
