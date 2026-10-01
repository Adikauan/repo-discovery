from datetime import UTC, datetime
from typing import Callable
from uuid import UUID

from app.application.ports.monitoring_configuration_repository import UnitOfWork
from app.domain.errors import CredentialReplacementConflict, CredentialServiceUnavailable, NotFoundError
from app.domain.ports.credential_cipher import CredentialCipher


class SaveGitLabCredential:
    def __init__(self, uow: UnitOfWork, cipher: CredentialCipher,
                 clock: Callable[[], datetime] | None = None):
        self.uow = uow
        self.cipher = cipher
        self.clock = clock or (lambda: datetime.now(UTC))

    def execute(self, configuration_id: UUID, token: str):
        if self.uow.configuration_repository.get_active(configuration_id) is None:
            raise NotFoundError("Monitoring Configuration was not found.")
        snapshot = self.uow.credential_repository.get(configuration_id)
        expected_revision = snapshot.revision if snapshot else None
        encrypted = self.cipher.encrypt(token)
        if not self.uow.credential_repository.replace(
            configuration_id, encrypted, expected_revision, self.clock()
        ):
            self.uow.rollback()
            raise CredentialReplacementConflict("The credential changed during replacement. Try again.")
        try:
            self.uow.commit()
        except Exception as error:
            self.uow.rollback()
            raise CredentialServiceUnavailable("Credential storage is unavailable.") from error
        from app.application.use_cases.get_gitlab_connection_status import GetGitLabConnectionStatus
        return GetGitLabConnectionStatus(self.uow).execute(configuration_id)
