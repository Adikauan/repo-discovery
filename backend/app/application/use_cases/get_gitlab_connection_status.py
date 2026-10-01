from hashlib import sha256
from uuid import UUID

from app.application.ports.monitoring_configuration_repository import UnitOfWork
from app.domain.entities.gitlab_connection_status import GitLabConnectionStatus
from app.domain.errors import NotFoundError


def normalized_url_fingerprint(url: str) -> str:
    return sha256(url.rstrip("/").encode("utf-8")).hexdigest()


class GetGitLabConnectionStatus:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def execute(self, configuration_id: UUID) -> GitLabConnectionStatus:
        configuration = self.uow.configuration_repository.get_active(configuration_id)
        if configuration is None:
            raise NotFoundError("Monitoring Configuration was not found.")
        snapshot = self.uow.credential_repository.get(configuration_id)
        if snapshot is None:
            return GitLabConnectionStatus(configuration_id, False, "not_configured")
        current_fingerprint = normalized_url_fingerprint(configuration.gitlab_url)
        if not snapshot.last_validation_result or snapshot.validated_url_fingerprint != current_fingerprint:
            return GitLabConnectionStatus(configuration_id, True, "configured_not_validated")
        state = "validated" if snapshot.last_validation_result == "success" else "failed"
        return GitLabConnectionStatus(
            configuration_id, True, state, snapshot.last_validation_result,
            snapshot.last_validated_at, snapshot.last_successful_validation_at,
        )
