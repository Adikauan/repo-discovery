from uuid import UUID

from app.application.ports.monitoring_configuration_repository import UnitOfWork
from app.domain.errors import NotFoundError


class RemoveGitLabCredential:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def execute(self, configuration_id: UUID) -> None:
        if self.uow.configuration_repository.get_active(configuration_id) is None:
            raise NotFoundError("Monitoring Configuration was not found.")
        self.uow.credential_repository.remove(configuration_id)
        try:
            self.uow.commit()
        except Exception:
            self.uow.rollback()
            raise
