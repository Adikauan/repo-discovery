from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from app.application.ports.monitoring_configuration_repository import UnitOfWork
from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
from app.domain.entities.mining_scope import SelectedGitLabGroup
from app.domain.errors import NotFoundError
from app.domain.ports.credential_cipher import CredentialCipher
from app.domain.ports.gitlab_connection_client import GitLabConnectionClient


class GetMiningScope:
    def __init__(self, uow: UnitOfWork, cipher: CredentialCipher | None = None,
                 client: GitLabConnectionClient | None = None, clock=None):
        self.uow, self.cipher, self.client = uow, cipher, client
        self.clock = clock or (lambda: datetime.now(UTC))

    def execute(self, configuration_id: UUID):
        configuration = self.uow.configuration_repository.get_active(configuration_id)
        if configuration is None:
            raise NotFoundError("Monitoring Configuration was not found.")
        scope = self.uow.mining_scope_repository.get(configuration_id)
        current_fingerprint = normalized_url_fingerprint(configuration.gitlab_url)
        credential = self.uow.credential_repository.get(configuration_id)
        availability: dict[UUID, str] = {}
        stale_groups = [item for item in scope.groups if item.instance_fingerprint != current_fingerprint]
        stale_repositories = [item for item in scope.repositories if item.instance_fingerprint != current_fingerprint]
        for item in (*stale_groups, *stale_repositories):
            availability[item.selection_id] = "stale"
        current_groups = [item for item in scope.groups if item.instance_fingerprint == current_fingerprint]
        current_repositories = [item for item in scope.repositories if item.instance_fingerprint == current_fingerprint]
        if not credential:
            for item in (*current_groups, *current_repositories):
                availability[item.selection_id] = "unresolved"
            return scope, availability
        if self.cipher is None or self.client is None:
            raise RuntimeError("Scope reconciliation dependencies are not configured.")

        self.uow.rollback()
        token = self.cipher.decrypt(credential.encrypted_token)
        url = configuration.gitlab_url

        def reconcile(item, is_group):
            return item, self.client.get_group(url, token, item.gitlab_group_id) if is_group else self.client.get_project(
                url, token, item.gitlab_project_id)

        current_items = [(item, True) for item in current_groups] + [(item, False) for item in current_repositories]
        updates_groups = {item.selection_id: item for item in scope.groups}
        updates_repositories = {item.selection_id: item for item in scope.repositories}
        workers = min(8, len(current_items))
        if workers:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(reconcile, item, is_group) for item, is_group in current_items]
                for future in futures:
                    item, result = future.result()
                    if result.succeeded and result.nodes:
                        node = result.nodes[0]
                        availability[item.selection_id] = "available"
                        refreshed = replace(item, name=node.name, full_path=node.full_path,
                                            parent_group_id=node.parent_group_id, updated_at=self.clock())
                        if isinstance(item, SelectedGitLabGroup):
                            updates_groups[item.selection_id] = refreshed
                        else:
                            updates_repositories[item.selection_id] = refreshed
                    elif result.outcome in {"not_found", "forbidden"}:
                        availability[item.selection_id] = "unavailable"
                    else:
                        availability[item.selection_id] = "unresolved"
        refreshed_groups = tuple(updates_groups.values())
        refreshed_repositories = tuple(updates_repositories.values())
        refreshed_scope = replace(scope, groups=refreshed_groups, repositories=refreshed_repositories)
        latest_configuration = self.uow.configuration_repository.get_active(configuration_id)
        latest_credential = self.uow.credential_repository.get(configuration_id)
        if (latest_configuration is None or latest_credential is None
                or normalized_url_fingerprint(latest_configuration.gitlab_url) != current_fingerprint
                or latest_credential.revision != credential.revision):
            self.uow.rollback()
            for item in (*current_groups, *current_repositories):
                availability[item.selection_id] = "unresolved"
            return scope, availability
        if refreshed_scope != scope:
            self.uow.mining_scope_repository.refresh_metadata(refreshed_scope)
            try:
                self.uow.commit()
            except Exception:
                self.uow.rollback()
                raise
        else:
            self.uow.rollback()
        return refreshed_scope, availability
