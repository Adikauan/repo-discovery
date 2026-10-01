from __future__ import annotations

from datetime import UTC, datetime
from typing import Callable
from uuid import UUID

from app.application.ports.monitoring_configuration_repository import UnitOfWork
from app.domain.errors import NotFoundError, StaleConfigurationError


class RetireMonitoringConfiguration:
    def __init__(self, uow: UnitOfWork, clock: Callable[[], datetime] | None = None):
        self.uow = uow
        self.clock = clock or (lambda: datetime.now(UTC))

    def execute(self, identifier: UUID) -> None:
        current = self.uow.configuration_repository.get_active(identifier)
        if current is None:
            raise NotFoundError("Monitoring Configuration was not found.")
        retired = current.retire(self.clock())
        if not self.uow.configuration_repository.retire(retired):
            self.uow.rollback()
            raise StaleConfigurationError("This Monitoring Configuration is no longer available.")
        self.uow.credential_repository.remove(identifier)
        try:
            self.uow.commit()
        except Exception:
            self.uow.rollback()
            raise
