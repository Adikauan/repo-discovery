from datetime import UTC, datetime
from typing import Callable
from uuid import UUID, uuid4

from app.application.ports.monitoring_configuration_repository import UnitOfWork
from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
from app.application.use_cases.get_gitlab_scope_tree import _raise_provider_error
from app.domain.entities.mining_scope import MiningScope, SelectedGitLabGroup, SelectedGitLabRepository
from app.domain.errors import (ConflictError, FieldValidationError, NotFoundError,
                               StaleConfigurationError)
from app.domain.ports.credential_cipher import CredentialCipher
from app.domain.ports.gitlab_connection_client import GitLabConnectionClient


class ReplaceMiningScope:
    def __init__(self, uow: UnitOfWork, cipher: CredentialCipher, client: GitLabConnectionClient,
                 clock: Callable[[], datetime] | None = None):
        self.uow, self.cipher, self.client = uow, cipher, client
        self.clock = clock or (lambda: datetime.now(UTC))

    @staticmethod
    def _validated_node(result, expected_type: str, field: str):
        if not result.succeeded:
            if result.outcome in {"not_found", "forbidden"}:
                raise FieldValidationError(field, "unavailable", "This GitLab selection is no longer available.")
            _raise_provider_error(result.outcome)
        if len(result.nodes) != 1 or result.nodes[0].type != expected_type:
            raise FieldValidationError(field, "invalid_entity", "Choose an available GitLab entity of this type.")
        return result.nodes[0]

    def execute(self, configuration_id: UUID, groups: list[dict], repositories: list[dict],
                expected_version: int) -> MiningScope:
        configuration = self.uow.configuration_repository.get_active(configuration_id)
        if configuration is None:
            raise NotFoundError("Monitoring Configuration was not found.")
        current_scope = self.uow.mining_scope_repository.get(configuration_id)
        if current_scope.version != expected_version:
            raise StaleConfigurationError("The saved scope changed. Reload and review your selections.")

        existing_groups = {item.selection_id: item for item in current_scope.groups}
        existing_repositories = {item.selection_id: item for item in current_scope.repositories}
        new_groups: list[SelectedGitLabGroup | None] = []
        new_repositories: list[SelectedGitLabRepository | None] = []
        requested_keys: set[tuple[str, str, int]] = set()
        original_url = configuration.gitlab_url
        fingerprint = normalized_url_fingerprint(original_url)

        for payload in groups:
            selection_id = payload.get("selection_id")
            gitlab_id = payload.get("gitlab_id")
            if selection_id is not None:
                item = existing_groups.get(selection_id)
                if item is None or item.gitlab_group_id != gitlab_id:
                    raise FieldValidationError("groups", "invalid_selection", "Review the selected GitLab groups.")
                key = ("group", item.instance_fingerprint, item.gitlab_group_id)
                new_groups.append(item)
            else:
                key = ("group", fingerprint, gitlab_id)
                new_groups.append(None)
            if key in requested_keys:
                raise FieldValidationError("groups", "duplicate", "Remove duplicate GitLab group selections.")
            requested_keys.add(key)

        for payload in repositories:
            selection_id = payload.get("selection_id")
            gitlab_id = payload.get("gitlab_id")
            if selection_id is not None:
                item = existing_repositories.get(selection_id)
                if item is None or item.gitlab_project_id != gitlab_id:
                    raise FieldValidationError("repositories", "invalid_selection", "Review the selected repositories.")
                key = ("repository", item.instance_fingerprint, item.gitlab_project_id)
                new_repositories.append(item)
            else:
                key = ("repository", fingerprint, gitlab_id)
                new_repositories.append(None)
            if key in requested_keys:
                raise FieldValidationError("repositories", "duplicate", "Remove duplicate repository selections.")
            requested_keys.add(key)

        has_new = any(item is None for item in new_groups) or any(item is None for item in new_repositories)
        credential = self.uow.credential_repository.get(configuration_id) if has_new else None
        if has_new and credential is None:
            raise ConflictError("Configure a GitLab credential before adding new scope selections.")
        if has_new:
            token = self.cipher.decrypt(credential.encrypted_token)
            self.uow.rollback()
            resolved_groups: dict[int, SelectedGitLabGroup] = {}
            resolved_repositories: dict[int, SelectedGitLabRepository] = {}
            for payload, item in zip(groups, new_groups):
                if item is not None:
                    continue
                node = self._validated_node(
                    self.client.get_group(original_url, token, payload["gitlab_id"]), "group", "groups")
                resolved_groups[payload["gitlab_id"]] = SelectedGitLabGroup(
                    uuid4(), fingerprint, node.id, node.name, node.full_path, node.parent_group_id, self.clock())
            for payload, item in zip(repositories, new_repositories):
                if item is not None:
                    continue
                node = self._validated_node(
                    self.client.get_project(original_url, token, payload["gitlab_id"]), "repository", "repositories")
                resolved_repositories[payload["gitlab_id"]] = SelectedGitLabRepository(
                    uuid4(), fingerprint, node.id, node.name, node.full_path, node.parent_group_id, self.clock())
            latest_configuration = self.uow.configuration_repository.get_active(configuration_id)
            latest_credential = self.uow.credential_repository.get(configuration_id)
            if (latest_configuration is None or latest_credential is None
                    or normalized_url_fingerprint(latest_configuration.gitlab_url) != fingerprint
                    or latest_credential.revision != credential.revision):
                self.uow.rollback()
                raise ConflictError("The GitLab connection changed while saving scope. Retry after reloading.")
            new_groups = [resolved_groups[item["gitlab_id"]] if current is None else current
                          for item, current in zip(groups, new_groups)]
            new_repositories = [resolved_repositories[item["gitlab_id"]] if current is None else current
                                for item, current in zip(repositories, new_repositories)]

        now = self.clock()
        scope = MiningScope(configuration_id, expected_version + 1, now,
                            tuple(new_groups), tuple(new_repositories))
        if not self.uow.mining_scope_repository.replace(scope, expected_version):
            self.uow.rollback()
            raise StaleConfigurationError("The saved scope changed. Reload and review your selections.")
        try:
            self.uow.commit()
        except Exception:
            self.uow.rollback()
            raise
        return scope
