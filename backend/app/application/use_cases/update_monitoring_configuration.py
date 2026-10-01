from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable
from uuid import UUID

from app.application.ports.monitoring_configuration_repository import UnitOfWork
from app.domain.errors import NotFoundError, StaleConfigurationError
from app.domain.monitoring_configuration import MonitoringConfiguration


class UpdateMonitoringConfiguration:
    def __init__(self, uow: UnitOfWork, clock: Callable[[], datetime] | None = None):
        self.uow = uow
        self.clock = clock or (lambda: datetime.now(UTC))

    def execute(
        self, identifier: UUID, payload: dict[str, Any], expected_revision: int
    ) -> MonitoringConfiguration:
        current = self.uow.configuration_repository.get_active(identifier)
        if current is None:
            raise NotFoundError("Monitoring Configuration was not found.")
        if current.revision != expected_revision:
            raise StaleConfigurationError("This Monitoring Configuration has changed. Reload and reapply your edits.")
        updated = current.update(
            name=payload.get("name"),
            description=payload.get("description"),
            gitlab_url=payload.get("gitlab_url"),
            enabled=payload.get("enabled"),
            allowed_author_emails=payload.get("allowed_author_emails", current.allowed_author_emails),
            now=self.clock(),
        )
        if updated == current:
            return current
        if not self.uow.configuration_repository.update(updated, expected_revision):
            self.uow.rollback()
            raise StaleConfigurationError("This Monitoring Configuration has changed. Reload and reapply your edits.")
        try:
            self.uow.commit()
        except Exception:
            self.uow.rollback()
            raise
        return updated
