from typing import Protocol
from uuid import UUID

from app.domain.entities.monitoring_schedule import MonitoringSchedule
from app.domain.monitoring_configuration import MonitoringConfiguration


class MonitoringScheduleRepository(Protocol):
    def get(self, configuration_id: UUID, *, for_update: bool = False) -> MonitoringSchedule: ...

    def list_eligible(self) -> list[tuple[MonitoringConfiguration, MonitoringSchedule]]: ...

    def replace(self, schedule: MonitoringSchedule, expected_version: int) -> bool: ...
