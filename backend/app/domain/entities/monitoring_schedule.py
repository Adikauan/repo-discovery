from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from enum import StrEnum
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from app.domain.errors import FieldValidationError


class RecurrenceType(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


def validate_timezone(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise FieldValidationError("timezone", "invalid_timezone", "Choose a supported IANA timezone.")
    try:
        if value not in available_timezones():
            raise ZoneInfoNotFoundError(value)
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise FieldValidationError("timezone", "invalid_timezone", "Choose a supported IANA timezone.") from None
    return value


@dataclass(frozen=True, slots=True)
class MonitoringSchedule:
    monitoring_configuration_id: UUID
    configured: bool
    version: int
    recurrence_type: RecurrenceType | None = None
    enabled: bool | None = None
    execution_time: time | None = None
    timezone: str | None = None
    day_of_week: int | None = None
    day_of_month: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.version < 0:
            raise ValueError("Schedule version cannot be negative.")
        if not self.configured:
            payload = (self.recurrence_type, self.enabled, self.execution_time, self.timezone,
                       self.day_of_week, self.day_of_month, self.created_at)
            if any(value is not None for value in payload):
                raise ValueError("An unconfigured schedule cannot contain recurrence data.")
            return
        if self.version < 1:
            raise ValueError("A configured schedule must have a positive version.")
        if self.recurrence_type is None:
            raise FieldValidationError("recurrenceType", "invalid_schedule", "Choose a recurrence type.")
        if not isinstance(self.enabled, bool):
            raise FieldValidationError("enabled", "invalid_schedule", "Choose whether automatic scheduling is enabled.")
        if not isinstance(self.execution_time, time) or self.execution_time.tzinfo is not None or \
                self.execution_time.second != 0 or self.execution_time.microsecond != 0:
            raise FieldValidationError("executionTime", "invalid_schedule", "Choose a valid time in HH:mm format.")
        if self.timezone is None:
            raise FieldValidationError("timezone", "invalid_timezone", "Choose a supported IANA timezone.")
        validate_timezone(self.timezone)
        if self.recurrence_type == RecurrenceType.DAILY:
            if self.day_of_week is not None or self.day_of_month is not None:
                raise FieldValidationError("recurrenceType", "invalid_schedule", "Daily schedules do not use weekday or month day.")
        elif self.recurrence_type == RecurrenceType.WEEKLY:
            if self.day_of_week not in range(1, 8) or self.day_of_month is not None:
                raise FieldValidationError("dayOfWeek", "invalid_schedule", "Choose one ISO weekday from 1 to 7.")
        elif self.recurrence_type == RecurrenceType.MONTHLY:
            if self.day_of_month not in range(1, 32) or self.day_of_week is not None:
                raise FieldValidationError("dayOfMonth", "invalid_schedule", "Choose one day of month from 1 to 31.")
        if self.created_at is None or self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise FieldValidationError("schedule", "invalid_schedule", "Schedule timestamps must be timezone-aware.")

    @classmethod
    def create(cls, *, configuration_id: UUID, recurrence_type: RecurrenceType | str,
               enabled: bool, execution_time: time, timezone: str,
               now: datetime, day_of_week: int | None = None,
               day_of_month: int | None = None, version: int = 1) -> MonitoringSchedule:
        try:
            recurrence = RecurrenceType(recurrence_type)
        except ValueError:
            raise FieldValidationError("recurrenceType", "invalid_schedule", "Choose daily, weekly, or monthly.") from None
        return cls(configuration_id, True, version, recurrence, enabled, execution_time,
                   validate_timezone(timezone), day_of_week, day_of_month, now, now)

    @classmethod
    def unconfigured(cls, configuration_id: UUID, version: int = 0,
                     updated_at: datetime | None = None) -> MonitoringSchedule:
        return cls(configuration_id, False, version, updated_at=updated_at)
