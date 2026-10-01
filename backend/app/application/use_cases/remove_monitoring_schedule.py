from datetime import UTC, datetime
from uuid import UUID

from app.domain.entities.monitoring_schedule import MonitoringSchedule
from app.domain.errors import NotFoundError, StaleConfigurationError


class RemoveMonitoringSchedule:
    def __init__(self, uow, now=None):
        self.uow = uow
        self.now = now or (lambda: datetime.now(UTC))

    def execute(self, configuration_id: UUID, expected_version: int) -> int:
        if self.uow.configuration_repository.lock_active(configuration_id) is None:
            raise NotFoundError("Monitoring Configuration not found.")
        current = self.uow.schedule_repository.get(configuration_id, for_update=True)
        if current.version != expected_version:
            raise StaleConfigurationError("The schedule has changed. Reload and review your draft.")
        if not current.configured:
            return current.version
        tombstone = MonitoringSchedule.unconfigured(configuration_id, expected_version + 1, self.now())
        if not self.uow.schedule_repository.replace(tombstone, expected_version):
            self.uow.rollback()
            raise StaleConfigurationError("The schedule has changed. Reload and review your draft.")
        self.uow.commit()
        return tombstone.version
