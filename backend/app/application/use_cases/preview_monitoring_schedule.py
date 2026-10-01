from datetime import UTC, datetime, time
from uuid import UUID

from app.domain.entities.monitoring_schedule import MonitoringSchedule
from app.domain.errors import FieldValidationError, NotFoundError
from app.domain.services.schedule_calculator import calculate_next_occurrence


class PreviewMonitoringSchedule:
    def __init__(self, uow, now=None):
        self.uow = uow
        self.now = now or (lambda: datetime.now(UTC))

    def execute(self, configuration_id: UUID, payload: dict):
        if self.uow.configuration_repository.get_active(configuration_id) is None:
            raise NotFoundError("Monitoring Configuration not found.")
        reference = payload.get("reference_instant", payload.get("referenceInstant")) or self.now()
        if reference.tzinfo is None or reference.utcoffset() is None:
            raise FieldValidationError("referenceInstant", "invalid_schedule", "Provide a timezone-aware reference instant.")
        values = payload.get("schedule", payload)
        execution_time = values.get("execution_time", values.get("executionTime"))
        if isinstance(execution_time, str):
            try:
                execution_time = time.fromisoformat(execution_time)
            except ValueError:
                raise FieldValidationError("executionTime", "invalid_schedule", "Choose a valid time in HH:mm format.") from None
        schedule = MonitoringSchedule.create(
            configuration_id=configuration_id,
            recurrence_type=values.get("recurrence_type", values.get("recurrenceType")),
            enabled=values.get("enabled"), execution_time=execution_time,
            timezone=values.get("timezone"), now=reference,
            day_of_week=values.get("day_of_week", values.get("dayOfWeek")),
            day_of_month=values.get("day_of_month", values.get("dayOfMonth")),
        )
        return calculate_next_occurrence(schedule, reference) if schedule.enabled else None
