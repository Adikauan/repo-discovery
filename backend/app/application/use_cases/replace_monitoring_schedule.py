from dataclasses import dataclass
from datetime import UTC, datetime, time
from uuid import UUID

from app.domain.entities.monitoring_schedule import MonitoringSchedule
from app.domain.errors import FieldValidationError, NotFoundError, StaleConfigurationError
from app.domain.services.schedule_calculator import calculate_next_occurrence


@dataclass(frozen=True, slots=True)
class ScheduleWriteResult:
    schedule: MonitoringSchedule
    next_occurrence: datetime | None


class ReplaceMonitoringSchedule:
    def __init__(self, uow, now=None):
        self.uow = uow
        self.now = now or (lambda: datetime.now(UTC))

    def execute(self, configuration_id: UUID, payload: dict, expected_version: int) -> MonitoringSchedule:
        if self.uow.configuration_repository.lock_active(configuration_id) is None:
            raise NotFoundError("Monitoring Configuration not found.")
        current = self.uow.schedule_repository.get(configuration_id, for_update=True)
        if current.version != expected_version:
            raise StaleConfigurationError("The schedule has changed. Reload and review your draft.")
        now = self.now()
        execution_time = payload.get("execution_time", payload.get("executionTime"))
        if isinstance(execution_time, str):
            try:
                execution_time = time.fromisoformat(execution_time)
            except ValueError:
                raise FieldValidationError("executionTime", "invalid_schedule", "Choose a valid time in HH:mm format.") from None
        candidate = MonitoringSchedule.create(
            configuration_id=configuration_id,
            recurrence_type=payload.get("recurrence_type", payload.get("recurrenceType")),
            enabled=payload.get("enabled"),
            execution_time=execution_time,
            timezone=payload.get("timezone"), now=now, version=expected_version + 1,
            day_of_week=payload.get("day_of_week", payload.get("dayOfWeek")),
            day_of_month=payload.get("day_of_month", payload.get("dayOfMonth")),
        )
        if current.configured and self._same_values(current, candidate):
            self.uow.rollback()
            return ScheduleWriteResult(current, calculate_next_occurrence(current, now) if current.enabled else None)
        next_occurrence = calculate_next_occurrence(candidate, now) if candidate.enabled else None
        if not self.uow.schedule_repository.replace(candidate, expected_version):
            self.uow.rollback()
            raise StaleConfigurationError("The schedule has changed. Reload and review your draft.")
        self.uow.commit()
        return ScheduleWriteResult(candidate, next_occurrence)

    @staticmethod
    def _same_values(left: MonitoringSchedule, right: MonitoringSchedule) -> bool:
        return (left.recurrence_type, left.enabled, left.execution_time, left.timezone,
                left.day_of_week, left.day_of_month) == (
                right.recurrence_type, right.enabled, right.execution_time, right.timezone,
                right.day_of_week, right.day_of_month)
