from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable, Literal
from uuid import UUID

from app.application.ports.monitoring_configuration_repository import UnitOfWork
from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
from app.domain.errors import ConflictError, CredentialReplacementConflict, FieldValidationError, NotFoundError
from app.domain.ports.credential_cipher import CredentialCipher
from app.domain.ports.gitlab_connection_client import GitLabConnectionClient


@dataclass(frozen=True, slots=True)
class ValidationResponse:
    configuration_id: UUID
    credential_source: Literal["saved_credential", "candidate_token"]
    state: Literal["validated", "failed"]
    result: str
    message: str
    checked_at: datetime
    last_successful_validation_at: datetime | None = None


class ValidateGitLabConnection:
    def __init__(self, uow: UnitOfWork, cipher: CredentialCipher, client: GitLabConnectionClient,
                 clock: Callable[[], datetime] | None = None):
        self.uow, self.cipher, self.client = uow, cipher, client
        self.clock = clock or (lambda: datetime.now(UTC))

    def execute(self, configuration_id: UUID, candidate_token: str | None = None) -> ValidationResponse:
        configuration = self.uow.configuration_repository.get_active(configuration_id)
        if configuration is None:
            raise NotFoundError("Monitoring Configuration was not found.")
        snapshot = self.uow.credential_repository.get(configuration_id)
        if candidate_token is not None:
            token, source = candidate_token, "candidate_token"
        else:
            if snapshot is None:
                raise ConflictError("Configure a GitLab credential before validating.")
            token, source = self.cipher.decrypt(snapshot.encrypted_token), "saved_credential"
        result = self.client.validate(configuration.gitlab_url, token)
        if result.outcome == "invalid_url":
            raise FieldValidationError("gitlab_url", "invalid_url", "The configured GitLab URL is invalid.")
        checked_at = self.clock()
        last_success = None
        if source == "saved_credential" and snapshot is not None:
            fingerprint = normalized_url_fingerprint(configuration.gitlab_url)
            if not self.uow.credential_repository.update_validation(
                configuration_id, snapshot.revision, fingerprint, result.outcome, checked_at
            ):
                self.uow.rollback()
                raise CredentialReplacementConflict("The connection changed during validation. Try again.")
            try:
                self.uow.commit()
            except Exception:
                self.uow.rollback()
                raise
            last_success = checked_at if result.succeeded else snapshot.last_successful_validation_at
        return ValidationResponse(
            configuration_id, source, "validated" if result.succeeded else "failed",
            result.outcome, result.message, checked_at, last_success,
        )
