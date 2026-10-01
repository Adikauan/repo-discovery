from uuid import UUID

from app.application.ports.monitoring_configuration_repository import UnitOfWork
from app.domain.errors import NotFoundError
from app.domain.monitoring_configuration import MonitoringConfiguration


class GetMonitoringConfiguration:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def execute(self, identifier: UUID) -> MonitoringConfiguration:
        configuration = self.uow.configuration_repository.get_active(identifier)
        if configuration is None:
            raise NotFoundError("Monitoring Configuration was not found.")
        return configuration
