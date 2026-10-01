from __future__ import annotations

from app.application.ports.monitoring_configuration_repository import UnitOfWork
from app.domain.monitoring_configuration import MonitoringConfiguration


class ListMonitoringConfigurations:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def execute(self, search: str | None = None) -> list[MonitoringConfiguration]:
        normalized_search = (search or "").strip() or None
        return self.uow.configuration_repository.list_active(normalized_search)

    def execute_with_schedule(self, search: str | None = None):
        normalized_search = (search or "").strip() or None
        repository = self.uow.configuration_repository
        if hasattr(repository, "list_active_with_schedules"):
            return repository.list_active_with_schedules(normalized_search)
        # Keeps lightweight adapters/test doubles compatible while production uses one joined query.
        return [(item, None) for item in repository.list_active(normalized_search)]
