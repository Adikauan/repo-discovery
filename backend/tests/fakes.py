from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.application.ports.create_request_store import CreateRequestReceipt
from app.domain.errors import DuplicateIdempotencyKey
from app.domain.entities.mining_scope import MiningScope
from app.domain.entities.monitoring_schedule import MonitoringSchedule
from app.domain.monitoring_configuration import MonitoringConfiguration
from app.domain.ports.gitlab_credential_repository import CredentialSnapshot


@dataclass
class MemoryUnitOfWork:
    configurations: dict[UUID, MonitoringConfiguration] = field(default_factory=dict)
    receipts: dict[str, CreateRequestReceipt] = field(default_factory=dict)
    credentials: dict[UUID, CredentialSnapshot] = field(default_factory=dict)
    scopes: dict[UUID, MiningScope] = field(default_factory=dict)
    schedules: dict[UUID, MonitoringSchedule] = field(default_factory=dict)
    executions: dict = field(default_factory=dict)
    _snapshot: tuple | None = None
    findings: dict = field(default_factory=dict)
    checkpoints: dict = field(default_factory=dict)
    author_policies: dict = field(default_factory=dict)
    target_branch_rules: dict = field(default_factory=dict)

    def __post_init__(self):
        self.configuration_repository = MemoryConfigurationRepository(self)
        self.receipt_repository = MemoryReceiptRepository(self)
        self.credential_repository = MemoryCredentialRepository(self)
        self.mining_scope_repository = MemoryMiningScopeRepository(self)
        self.schedule_repository = MemoryMonitoringScheduleRepository(self)
        self.execution_repository = MemoryExecutionRepository(self)
        self.repository_execution_repository = MemoryRepositoryExecutionRepository(self)
        self.finding_repository = MemoryFindingRepository(self)
        self.repository_checkpoint_repository = MemoryCheckpointRepository(self)
        self.author_policy_repository = MemoryAuthorPolicyRepository(self)
        self.target_branch_repository = MemoryTargetBranchRepository(self)

    def begin_execution_creation(self):
        self.__enter__()

    def __enter__(self):
        self._snapshot = (self.configurations.copy(), self.receipts.copy(), self.credentials.copy(), self.scopes.copy(), self.schedules.copy(), self.executions.copy(), self.repository_execution_repository.items.copy(), self.findings.copy(), self.checkpoints.copy(), self.author_policies.copy(), self.target_branch_rules.copy())
        return self

    def __exit__(self, exc_type, exc, traceback):
        if exc_type is not None:
            self.rollback()
        return False

    def commit(self):
        self._snapshot = (self.configurations.copy(), self.receipts.copy(), self.credentials.copy(), self.scopes.copy(), self.schedules.copy(), self.executions.copy(), self.repository_execution_repository.items.copy(), self.findings.copy(), self.checkpoints.copy(), self.author_policies.copy(), self.target_branch_rules.copy())

    def rollback(self):
        if self._snapshot is not None:
            self.configurations, self.receipts, self.credentials, self.scopes, self.schedules, self.executions, self.repository_execution_repository.items, self.findings, self.checkpoints, self.author_policies, self.target_branch_rules = self._snapshot


class MemoryConfigurationRepository:
    def __init__(self, uow: MemoryUnitOfWork):
        self.uow = uow

    def add(self, configuration):
        self.uow.configurations[configuration.id] = configuration

    def get(self, identifier):
        return self.uow.configurations.get(identifier)

    def lock_active(self, identifier):
        return self.get_active(identifier)

    def get_active(self, identifier):
        configuration = self.uow.configurations.get(identifier)
        return configuration if configuration is not None and configuration.retired_at is None else None

    def list_active(self, search=None):
        configurations = [c for c in self.uow.configurations.values() if c.retired_at is None]
        if search and search.strip():
            term = search.strip().casefold()
            configurations = [c for c in configurations if term in c.name.casefold()]
        return sorted(configurations, key=lambda c: c.created_at, reverse=True)

    def list_active_with_schedules(self, search=None):
        configurations = self.list_active(search)
        return [(item, self.uow.schedule_repository.get(item.id) if self.uow.schedule_repository.get(item.id).configured else None)
                for item in configurations]

    def update(self, configuration, expected_revision):
        current = self.get_active(configuration.id)
        if current is None or current.revision != expected_revision:
            return False
        self.uow.configurations[configuration.id] = configuration
        return True

    def retire(self, configuration):
        current = self.get_active(configuration.id)
        if current is None:
            return False
        self.uow.configurations[configuration.id] = configuration
        return True


class MemoryAuthorPolicyRepository:
    def __init__(self, uow): self.uow = uow
    def list_for_configuration(self, configuration_id):
        return [item for item in self.uow.author_policies.values() if item.monitoring_configuration_id == configuration_id]
    def get(self, policy_id): return self.uow.author_policies.get(policy_id)
    def upsert(self, policy):
        current = next((item for item in self.list_for_configuration(policy.monitoring_configuration_id)
            if item.scope_type == policy.scope_type and item.instance_fingerprint == policy.instance_fingerprint
            and item.gitlab_group_id == policy.gitlab_group_id and item.gitlab_project_id == policy.gitlab_project_id
            and item.branch == policy.branch), None)
        if current is not None: self.uow.author_policies.pop(current.id, None)
        self.uow.author_policies[policy.id] = policy
    def delete(self, policy_id, configuration_id):
        item = self.uow.author_policies.get(policy_id)
        if item is None or item.monitoring_configuration_id != configuration_id: return False
        del self.uow.author_policies[policy_id]
        return True


class MemoryTargetBranchRepository:
    def __init__(self, uow): self.uow = uow
    def list_for_configuration(self, configuration_id):
        return [item for item in self.uow.target_branch_rules.values()
                if item.monitoring_configuration_id == configuration_id]
    def replace_for_configuration(self, configuration_id, rules):
        self.uow.target_branch_rules = {key: item for key, item in self.uow.target_branch_rules.items()
            if item.monitoring_configuration_id != configuration_id}
        self.uow.target_branch_rules.update({item.id: item for item in rules})


class MemoryReceiptRepository:
    def __init__(self, uow: MemoryUnitOfWork):
        self.uow = uow

    def get(self, key):
        return self.uow.receipts.get(key)

    def add(self, receipt):
        if receipt.request_key in self.uow.receipts:
            raise DuplicateIdempotencyKey()
        self.uow.receipts[receipt.request_key] = receipt


class MemoryCredentialRepository:
    def __init__(self, uow: MemoryUnitOfWork):
        self.uow = uow

    def get(self, configuration_id):
        return self.uow.credentials.get(configuration_id)

    def replace(self, configuration_id, encrypted_token, expected_revision, now: datetime):
        current = self.get(configuration_id)
        if expected_revision is None:
            if current is not None:
                return False
            revision = 1
        elif current is None or current.revision != expected_revision:
            return False
        else:
            revision = expected_revision + 1
        self.uow.credentials[configuration_id] = CredentialSnapshot(
            configuration_id, encrypted_token, revision, None, None, None, None)
        return True

    def remove(self, configuration_id):
        self.uow.credentials.pop(configuration_id, None)

    def update_validation(self, configuration_id, expected_revision, url_fingerprint, result, checked_at):
        current = self.get(configuration_id)
        if current is None or current.revision != expected_revision:
            return False
        self.uow.credentials[configuration_id] = CredentialSnapshot(
            current.configuration_id, current.encrypted_token, current.revision, result, checked_at,
            checked_at if result == "success" else current.last_successful_validation_at, url_fingerprint)
        return True


class MemoryMiningScopeRepository:
    def __init__(self, uow: MemoryUnitOfWork):
        self.uow = uow

    def get(self, configuration_id):
        return self.uow.scopes.get(configuration_id, MiningScope(configuration_id, 0, None))

    def replace(self, scope, expected_version):
        if self.get(scope.configuration_id).version != expected_version:
            return False
        self.uow.scopes[scope.configuration_id] = scope
        return True

    def refresh_metadata(self, scope):
        self.uow.scopes[scope.configuration_id] = scope


class MemoryMonitoringScheduleRepository:
    def __init__(self, uow: MemoryUnitOfWork):
        self.uow = uow

    def get(self, configuration_id, *, for_update=False):
        return self.uow.schedules.get(configuration_id, MonitoringSchedule.unconfigured(configuration_id))

    def list_eligible(self):
        return [(configuration, schedule) for configuration in self.uow.configurations.values()
            if configuration.enabled and configuration.retired_at is None
            for schedule in [self.get(configuration.id)] if schedule.configured and schedule.enabled]

    def replace(self, schedule, expected_version):
        current = self.get(schedule.monitoring_configuration_id)
        if current.version != expected_version:
            return False
        self.uow.schedules[schedule.monitoring_configuration_id] = schedule
        return True


class FakeCipher:
    def encrypt(self, token: str) -> bytes:
        return b"encrypted:" + token.encode("utf-8")

    def decrypt(self, encrypted_token: bytes) -> str:
        return encrypted_token.removeprefix(b"encrypted:").decode("utf-8")


class MemoryExecutionRepository:
    def __init__(self, uow):
        self.uow = uow

    def add(self, item):
        from app.domain.errors import ConflictError
        if item.trigger_type == "scheduled" and any(
            existing.monitoring_configuration_id == item.monitoring_configuration_id
            and existing.scheduled_occurrence_at == item.scheduled_occurrence_at
            for existing in self.uow.executions.values()
        ):
            from app.domain.errors import DuplicateScheduledOccurrence
            raise DuplicateScheduledOccurrence()
        if self.active_for(item.monitoring_configuration_id):
            raise ConflictError('An execution is already active.')
        self.uow.executions[item.id] = item

    def get(self, identifier, *, for_update=False):
        return self.uow.executions.get(identifier)

    def active_for(self, configuration_id):
        return next((e for e in self.uow.executions.values() if e.monitoring_configuration_id == configuration_id and e.active), None)

    def transition(self, item, expected_status):
        current = self.get(item.id)
        if current is None or current.status != expected_status:
            return False
        self.uow.executions[item.id] = item
        return True

    def update_snapshot(self, execution):
        current = self.get(execution.id)
        if current is None or current.status != "running": return False
        self.uow.executions[execution.id] = execution
        return True

    def update_counters(self, identifier, *, repository_count, successful_count, failed_count, finding_count, scope_failures=0, repository_mining_completed=False):
        from dataclasses import replace
        current = self.uow.executions.get(identifier)
        if current is None:
            return False
        self.uow.executions[identifier] = replace(current, repository_count=repository_count,
            successful_repository_count=successful_count, failed_repository_count=failed_count,
            finding_count=finding_count, scope_resolution_failure_count=scope_failures,
            repository_mining_completed=repository_mining_completed)
        return True

    def page(self, *, page, page_size, configuration_id=None, status=None, trigger_type=None):
        items = [e for e in self.uow.executions.values() if
            (configuration_id is None or e.monitoring_configuration_id == configuration_id) and
            (status is None or e.status == status) and (trigger_type is None or e.trigger_type == trigger_type)]
        items.sort(key=lambda e: (e.created_at, e.id), reverse=True)
        return items[(page - 1) * page_size:page * page_size], len(items)


class MemoryRepositoryExecutionRepository:
    def __init__(self, uow):
        self.uow = uow
        self.items = {}

    def add(self, item):
        from app.domain.errors import ConflictError
        if any(row.mining_execution_id == item.mining_execution_id
                and row.gitlab_project_id == item.gitlab_project_id
                and row.target_branch == item.target_branch for row in self.items.values()):
            raise ConflictError("Repository branch already exists for this execution.")
        self.items[item.id] = item

    def get(self, identifier, execution_id=None, *, for_update=False):
        item = self.items.get(identifier)
        return item if item is not None and (execution_id is None or item.mining_execution_id == execution_id) else None

    def get_by_project(self, execution_id, project_id):
        return next((item for item in self.items.values() if item.mining_execution_id == execution_id and item.gitlab_project_id == project_id), None)

    def transition(self, item, expected_status):
        current = self.items.get(item.id)
        if current is None or current.status != expected_status:
            return False
        self.items[item.id] = item
        return True


    def save_summary(self, item, expected_status="running"):
        return self.transition(item, expected_status)

    def list_for_execution(self, execution_id, *, page=1, page_size=25):
        values = sorted((item for item in self.items.values() if item.mining_execution_id == execution_id),
                        key=lambda item: (item.repository_full_path.casefold(), item.gitlab_project_id,
                                          item.target_branch or ""))
        return values[(page - 1) * page_size:page * page_size], len(values)

    def update_execution_counters(self, execution_id, **counters):
        current = self.uow.executions.get(execution_id)
        if current is None:
            return False
        from dataclasses import replace
        self.uow.executions[execution_id] = replace(current,
            repository_count=counters["repository_count"], successful_repository_count=counters["successful_count"],
            failed_repository_count=counters["failed_count"], finding_count=counters["finding_count"],
            scope_resolution_failure_count=counters.get("scope_failures", 0))
        return True


class MemoryCheckpointRepository:
    def __init__(self, uow): self.uow = uow
    def get(self, config_id, project_id, branch): return self.uow.checkpoints.get((config_id, project_id, branch))
    def put(self, item): self.uow.checkpoints[(item.monitoring_configuration_id, item.gitlab_project_id, item.branch)] = item


class MemoryFindingRepository:
    def __init__(self, uow): self.uow = uow
    def add(self, item): self.uow.findings[item.id] = item
    def list_for_execution(self, execution_id, *, page=1, page_size=25, repository_id=None, rule_id=None, severity=None):
        rows = [(item, self.uow.repository_execution_repository.items[item.repository_execution_id].repository_full_path)
                for item in self.uow.findings.values()
                if self.uow.repository_execution_repository.items[item.repository_execution_id].mining_execution_id == execution_id
                and (repository_id is None or item.repository_execution_id == repository_id)
                and (rule_id is None or item.rule_id == rule_id) and (severity is None or item.severity == severity)]
        rows.sort(key=lambda pair: (pair[0].authored_at is None, -(pair[0].authored_at or pair[0].created_at).timestamp(), str(pair[0].id)))
        return rows[(page - 1) * page_size:page * page_size], len(rows)
    def list_for_repository(self, repository_execution_id, *, page=1, page_size=25, rule_id=None, severity=None):
        rows = [item for item in self.uow.findings.values() if item.repository_execution_id == repository_execution_id
                and (rule_id is None or item.rule_id == rule_id) and (severity is None or item.severity == severity)]
        rows.sort(key=lambda item: (item.authored_at is None, -(item.authored_at or item.created_at).timestamp(), str(item.id)))
        return rows[(page - 1) * page_size:page * page_size], len(rows)
    def get(self, identifier): return self.uow.findings.get(identifier)
    def count_by_executions(self, execution_ids):
        counts = {identifier: 0 for identifier in execution_ids}
        repository_rows = self.uow.repository_execution_repository.items.values()
        repository_owner = {row.id: row.mining_execution_id for row in repository_rows}
        for finding in self.uow.findings.values():
            owner = repository_owner.get(finding.repository_execution_id)
            if owner in counts: counts[owner] += 1
        return counts


class FakeGitLabClient:
    def __init__(self, result=None):
        from app.domain.value_objects.connection_validation_result import ConnectionValidationResult
        self.result = result or ConnectionValidationResult("success", "GitLab connection validated.")
        self.calls = []

    def validate(self, gitlab_url, token):
        self.calls.append((gitlab_url, token))
        return self.result

    @staticmethod
    def discovery_result(nodes=(), outcome="success"):
        from app.domain.value_objects.gitlab_discovery_result import GitLabDiscoveryResult
        return GitLabDiscoveryResult(outcome, tuple(nodes))

    def list_top_level_groups(self, gitlab_url, token):
        self.calls.append(("root", gitlab_url, token))
        return getattr(self, "root_result", self.discovery_result())

    def list_group_children(self, gitlab_url, token, group_id):
        self.calls.append(("children", gitlab_url, token, group_id))
        return getattr(self, "children", {}).get(group_id, self.discovery_result())

    def get_group(self, gitlab_url, token, group_id):
        self.calls.append(("group", gitlab_url, token, group_id))
        return getattr(self, "groups", {}).get(group_id, self.discovery_result())

    def get_project(self, gitlab_url, token, project_id):
        self.calls.append(("project", gitlab_url, token, project_id))
        return getattr(self, "projects", {}).get(project_id, self.discovery_result())
