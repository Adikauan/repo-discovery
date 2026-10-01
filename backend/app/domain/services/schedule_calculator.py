from calendar import monthrange
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.domain.entities.monitoring_schedule import MonitoringSchedule, RecurrenceType
from app.domain.errors import FieldValidationError


def _resolve_local(local_value: datetime, timezone: ZoneInfo) -> datetime:
    """Resolve a local wall time: earlier instant in folds; shift by the gap in gaps."""
    projections: list[tuple[datetime, datetime]] = []
    for fold in (0, 1):
        candidate = local_value.replace(tzinfo=timezone, fold=fold)
        instant = candidate.astimezone(UTC)
        round_trip = instant.astimezone(timezone)
        if round_trip.replace(tzinfo=None) == local_value:
            projections.append((instant, round_trip.replace(tzinfo=None)))
    distinct = {instant for instant, _ in projections}
    if distinct:
        return min(distinct)

    # A gap has two invalid interpretations. The pre-transition offset's UTC
    # projection lands after the gap; select that projection to preserve position.
    forward: list[tuple[datetime, datetime]] = []
    for fold in (0, 1):
        instant = local_value.replace(tzinfo=timezone, fold=fold).astimezone(UTC)
        projected = instant.astimezone(timezone).replace(tzinfo=None)
        if projected > local_value:
            forward.append((projected, instant))
    if not forward:
        raise FieldValidationError("executionTime", "invalid_schedule", "This local time could not be resolved.")
    return min(forward, key=lambda entry: entry[0])[1]


def _candidate_date(schedule: MonitoringSchedule, start: date, offset: int) -> date | None:
    if schedule.recurrence_type == RecurrenceType.DAILY:
        return start + timedelta(days=offset)
    if schedule.recurrence_type == RecurrenceType.WEEKLY:
        day = start + timedelta(days=offset)
        return day if day.isoweekday() == schedule.day_of_week else None
    month_index = start.year * 12 + start.month - 1 + offset
    year, month0 = divmod(month_index, 12)
    month = month0 + 1
    if year < 1 or year > 9999:
        return None
    day = min(schedule.day_of_month or 1, monthrange(year, month)[1])
    try:
        return date(year, month, day)
    except ValueError:
        return None


def calculate_next_occurrence(schedule: MonitoringSchedule, reference_instant: datetime) -> datetime:
    """Return the first scheduled instant strictly after an explicit aware reference."""
    if not schedule.configured or not schedule.enabled:
        raise ValueError("A next occurrence requires an enabled configured schedule.")
    if reference_instant.tzinfo is None or reference_instant.utcoffset() is None:
        raise ValueError("The reference instant must be timezone-aware.")
    timezone = ZoneInfo(schedule.timezone or "UTC")
    reference = reference_instant.astimezone(UTC)
    local_reference = reference.astimezone(timezone)
    start = local_reference.date()
    # A bounded four-year search covers every monthly/day-of-week cycle and leap-day.
    limit = 1462 if schedule.recurrence_type == RecurrenceType.DAILY else 1462
    for offset in range(limit):
        candidate_day = _candidate_date(schedule, start, offset)
        if candidate_day is None:
            continue
        local_candidate = datetime.combine(candidate_day, schedule.execution_time or time.min)
        occurrence = _resolve_local(local_candidate, timezone)
        if occurrence > reference:
            return occurrence
    raise ValueError("No future schedule occurrence could be calculated.")
