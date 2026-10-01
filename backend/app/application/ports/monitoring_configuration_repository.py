from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.application.ports.create_request_store import CreateRequestStore
from app.application.ports.mining_scope_repository import MiningScopeRepository
from app.application.ports.monitoring_schedule_repository import MonitoringScheduleRepository
from app.application.ports.mining_execution_repository import MiningExecutionRepository
from app.application.ports.repository_execution_repository import RepositoryExecutionRepository
from app.domain.monitoring_configuration import MonitoringConfiguration
from app.domain.ports.gitlab_credential_repository import GitLabCredentialRepository
from app.application.ports.author_policy_repository import AuthorPolicyRepository


class MonitoringConfigurationRepository(Protocol):
    def get(self, identifier: UUID) -> MonitoringConfiguration | None: ...
    def lock_active(self, identifier: UUID) -> MonitoringConfiguration | None: ...
    def add(self, configuration: MonitoringConfiguration) -> None: ...
    def get_active(self, identifier: UUID) -> MonitoringConfiguration | None: ...
    def list_active(self, search: str | None = None) -> list[MonitoringConfiguration]: ...
    def update(self, configuration: MonitoringConfiguration, expected_revision: int) -> bool: ...
    def retire(self, configuration: MonitoringConfiguration) -> bool: ...


class UnitOfWork(Protocol):
    configuration_repository: MonitoringConfigurationRepository
    receipt_repository: CreateRequestStore
    credential_repository: GitLabCredentialRepository
    mining_scope_repository: MiningScopeRepository
    schedule_repository: MonitoringScheduleRepository
    execution_repository: MiningExecutionRepository
    repository_execution_repository: RepositoryExecutionRepository
    finding_repository: object
    repository_checkpoint_repository: object
    author_policy_repository: AuthorPolicyRepository

    def begin_execution_creation(self) -> None: ...

    def commit(self) -> None: ...
    def rollback(self) -> None: ...
