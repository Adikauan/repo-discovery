from uuid import UUID

from app.application.ports.monitoring_configuration_repository import UnitOfWork
from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
from app.domain.errors import ConflictError, FieldValidationError, GitLabDiscoveryError, NotFoundError
from app.domain.ports.credential_cipher import CredentialCipher
from app.domain.ports.gitlab_connection_client import GitLabConnectionClient


def _raise_provider_error(outcome: str) -> None:
    if outcome == "invalid_url":
        raise FieldValidationError("gitlab_url", "invalid_url", "The configured GitLab URL is invalid.")
    raise GitLabDiscoveryError(outcome)


class GetGitLabScopeTree:
    def __init__(self, uow: UnitOfWork, cipher: CredentialCipher, client: GitLabConnectionClient):
        self.uow, self.cipher, self.client = uow, cipher, client

    def execute(self, configuration_id: UUID, group_id: int | None = None):
        configuration = self.uow.configuration_repository.get_active(configuration_id)
        if configuration is None:
            raise NotFoundError("Monitoring Configuration was not found.")
        snapshot = self.uow.credential_repository.get(configuration_id)
        if snapshot is None:
            raise ConflictError("Configure a GitLab credential before browsing scope.")
        url = configuration.gitlab_url
        credential_revision = snapshot.revision
        token = self.cipher.decrypt(snapshot.encrypted_token)
        self.uow.rollback()
        result = (self.client.list_top_level_groups(url, token) if group_id is None
                  else self.client.list_group_children(url, token, group_id))
        if not result.succeeded:
            if result.outcome == "not_found":
                raise NotFoundError("The requested GitLab group is unavailable.")
            _raise_provider_error(result.outcome)
        latest_configuration = self.uow.configuration_repository.get_active(configuration_id)
        latest_credential = self.uow.credential_repository.get(configuration_id)
        if (latest_configuration is None or latest_credential is None
                or normalized_url_fingerprint(latest_configuration.gitlab_url) != normalized_url_fingerprint(url)
                or latest_credential.revision != credential_revision):
            self.uow.rollback()
            raise ConflictError("The GitLab connection changed during discovery. Retry the request.")
        self.uow.rollback()
        return result.nodes
