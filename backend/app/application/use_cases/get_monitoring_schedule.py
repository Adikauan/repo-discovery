from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.domain.entities.monitoring_schedule import MonitoringSchedule
from app.domain.errors import NotFoundError
from app.domain.services.schedule_calculator import calculate_next_occurrence


@dataclass(frozen=True, slots=True)
class ScheduleReadResult:
    schedule: MonitoringSchedule | None
    version: int
    next_occurrence: datetime | None


class GetMonitoringSchedule:
    def __init__(self, uow, now=None):
        self.uow = uow
        self.now = now or (lambda: datetime.now(UTC))

    def execute(self, configuration_id: UUID) -> ScheduleReadResult:
        if self.uow.configuration_repository.get_active(configuration_id) is None:
            raise NotFoundError("Monitoring Configuration not found.")
        state = self.uow.schedule_repository.get(configuration_id)
        next_occurrence = calculate_next_occurrence(state, self.now()) if state.configured and state.enabled else None
        return ScheduleReadResult(state if state.configured else None, state.version, next_occurrence)
