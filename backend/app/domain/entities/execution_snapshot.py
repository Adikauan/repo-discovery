from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class SnapshotValue(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')


class SnapshotGroup(SnapshotValue):
    gitlab_group_id: int = Field(gt=0)
    name: str
    full_path: str
    parent_group_id: int | None = None
    instance_fingerprint: str


class SnapshotRepository(SnapshotValue):
    gitlab_project_id: int = Field(gt=0)
    name: str
    full_path: str
    parent_group_id: int | None = None
    instance_fingerprint: str


class ScheduleTriggerContext(SnapshotValue):
    scheduled_occurrence: AwareDatetime
    schedule_version: int = Field(gt=0)


class ExecutionSnapshotV1(SnapshotValue):
    schema_version: Literal[1] = 1
    configuration_id: UUID
    configuration_name: str
    configuration_enabled: bool
    gitlab_url: str
    configuration_revision: int | None = Field(default=None, gt=0)
    scope_version: int | None = Field(default=None, ge=0)
    groups: tuple[SnapshotGroup, ...] = ()
    repositories: tuple[SnapshotRepository, ...] = ()
    trigger_type: Literal['manual', 'scheduled']
    schedule_context: ScheduleTriggerContext | None = None
    allowed_author_emails: tuple[str, ...] = ()

    @classmethod
    def capture(cls, configuration, scope, *, trigger_type: Literal['manual', 'scheduled'] = 'manual',
                scheduled_occurrence: datetime | None = None, schedule_version: int | None = None):
        if trigger_type == 'scheduled':
            if scheduled_occurrence is None or schedule_version is None:
                raise ValueError('Scheduled snapshots require occurrence and schedule version context.')
            schedule_context = ScheduleTriggerContext(scheduled_occurrence=scheduled_occurrence,
                schedule_version=schedule_version)
        elif scheduled_occurrence is not None or schedule_version is not None:
            raise ValueError('Manual snapshots cannot contain schedule trigger context.')
        else:
            schedule_context = None
        return cls(configuration_id=configuration.id, configuration_name=configuration.name,
            configuration_enabled=configuration.enabled, gitlab_url=configuration.gitlab_url,
            configuration_revision=configuration.revision, scope_version=scope.version,
            trigger_type=trigger_type, schedule_context=schedule_context,
            allowed_author_emails=tuple(configuration.allowed_author_emails),
            groups=tuple(SnapshotGroup(gitlab_group_id=g.gitlab_group_id, name=g.name,
                full_path=g.full_path, parent_group_id=g.parent_group_id,
                instance_fingerprint=g.instance_fingerprint) for g in scope.groups),
            repositories=tuple(SnapshotRepository(gitlab_project_id=r.gitlab_project_id, name=r.name,
                full_path=r.full_path, parent_group_id=r.parent_group_id,
                instance_fingerprint=r.instance_fingerprint) for r in scope.repositories))


class SnapshotAuthorPolicy(SnapshotValue):
    scope_type: Literal['group', 'repository_branch']
    instance_fingerprint: str
    full_path: str
    gitlab_group_id: int | None = None
    gitlab_project_id: int | None = None
    branch: str | None = None
    allowed_author_emails: tuple[str, ...] = ()


class SnapshotRepositoryGroupCoverage(SnapshotValue):
    gitlab_project_id: int = Field(gt=0)
    selected_group_id: int = Field(gt=0)
    distance_to_repository: int = Field(ge=0)


class ExecutionSnapshotV2(ExecutionSnapshotV1):
    schema_version: Literal[2] = 2
    author_policy_mode: Literal['legacy', 'scope_aware'] = 'legacy'
    allowed_author_emails: tuple[str, ...] = ()
    legacy_allowed_author_emails: tuple[str, ...] = ()
    group_author_policies: tuple[SnapshotAuthorPolicy, ...] = ()
    repository_branch_author_policies: tuple[SnapshotAuthorPolicy, ...] = ()
    repository_group_coverage: tuple[SnapshotRepositoryGroupCoverage, ...] = ()

    @classmethod
    def capture(cls, configuration, scope, *, policies=(), trigger_type: Literal['manual', 'scheduled'] = 'manual',
                scheduled_occurrence: datetime | None = None, schedule_version: int | None = None):
        base = ExecutionSnapshotV1.capture(configuration, scope, trigger_type=trigger_type,
            scheduled_occurrence=scheduled_occurrence, schedule_version=schedule_version)
        normalized_policies = tuple(SnapshotAuthorPolicy(scope_type=p.scope_type,
                instance_fingerprint=p.instance_fingerprint, full_path=p.full_path,
                gitlab_group_id=p.gitlab_group_id, gitlab_project_id=p.gitlab_project_id,
                branch=p.branch, allowed_author_emails=p.allowed_author_emails) for p in policies)
        return cls(**{**base.model_dump(), 'schema_version': 2, 'allowed_author_emails': ()},
            author_policy_mode=configuration.author_policy_mode,
            legacy_allowed_author_emails=base.allowed_author_emails if configuration.author_policy_mode == 'legacy' else (),
            group_author_policies=tuple(p for p in normalized_policies if p.scope_type == 'group'),
            repository_branch_author_policies=tuple(p for p in normalized_policies if p.scope_type == 'repository_branch'))

    @property
    def author_policies(self):
        return (*self.group_author_policies, *self.repository_branch_author_policies)

    def with_repository_group_coverage(self, repositories):
        policies = [item for item in self.author_policies if item.scope_type == "group"]
        coverage = []
        for repository in repositories:
            path = repository.full_path.strip("/").casefold().split("/")
            for policy in policies:
                prefix = policy.full_path.strip("/").casefold().split("/")
                if len(prefix) <= len(path) and path[:len(prefix)] == prefix:
                    coverage.append(SnapshotRepositoryGroupCoverage(
                        gitlab_project_id=repository.id, selected_group_id=policy.gitlab_group_id,
                        distance_to_repository=len(path) - len(prefix)))
        return self.model_copy(update={"repository_group_coverage": tuple(sorted(coverage,
            key=lambda item: (item.gitlab_project_id, item.distance_to_repository, item.selected_group_id)))})


class SnapshotTargetBranchRule(SnapshotValue):
    scope_type: Literal['group', 'repository']
    instance_fingerprint: str
    gitlab_scope_id: int = Field(gt=0)
    full_path: str
    branch_name: str


class ExecutionSnapshotV3(ExecutionSnapshotV2):
    schema_version: Literal[3] = 3
    target_branch_rules: tuple[SnapshotTargetBranchRule, ...] = ()

    @classmethod
    def capture(cls, configuration, scope, *, policies=(), target_branch_rules=(), trigger_type='manual',
                scheduled_occurrence: datetime | None = None, schedule_version: int | None = None):
        base = ExecutionSnapshotV2.capture(configuration, scope, policies=policies,
            trigger_type=trigger_type, scheduled_occurrence=scheduled_occurrence,
            schedule_version=schedule_version)
        targets = tuple(SnapshotTargetBranchRule(scope_type=rule.scope_type,
            instance_fingerprint=rule.instance_fingerprint, gitlab_scope_id=rule.gitlab_scope_id,
            full_path=rule.full_path, branch_name=rule.branch_name) for rule in target_branch_rules)
        return cls(**{**base.model_dump(), 'schema_version': 3}, target_branch_rules=targets)


class SnapshotMiningTarget(SnapshotValue):
    gitlab_project_id: int = Field(gt=0)
    instance_fingerprint: str
    name: str
    full_path: str
    branch: str = Field(min_length=1)
    allowed_author_emails: tuple[str, ...] = ()


class ExecutionSnapshotV4(ExecutionSnapshotV3):
    """Final policy-sourced mining targets; Scope branch rules are not consulted."""
    schema_version: Literal[4] = 4
    mining_targets: tuple[SnapshotMiningTarget, ...] = ()

    @classmethod
    def capture(cls, configuration, scope, *, mining_targets=(), trigger_type='manual',
                scheduled_occurrence: datetime | None = None, schedule_version: int | None = None):
        base = ExecutionSnapshotV2.capture(configuration, scope, policies=(), trigger_type=trigger_type,
            scheduled_occurrence=scheduled_occurrence, schedule_version=schedule_version)
        targets = tuple(SnapshotMiningTarget(gitlab_project_id=item.gitlab_project_id,
            instance_fingerprint=item.instance_fingerprint, name=item.name, full_path=item.full_path,
            branch=item.branch, allowed_author_emails=tuple(item.allowed_author_emails))
            for item in mining_targets)
        return cls(**{**base.model_dump(), 'schema_version': 4,
            'allowed_author_emails': (), 'legacy_allowed_author_emails': (),
            'repository_branch_author_policies': (), 'group_author_policies': (),
            'repository_group_coverage': (), 'target_branch_rules': ()}, mining_targets=targets)

    @property
    def author_policies(self):
        return tuple(SnapshotAuthorPolicy(scope_type='repository_branch',
            instance_fingerprint=item.instance_fingerprint, full_path=item.full_path,
            gitlab_project_id=item.gitlab_project_id, branch=item.branch,
            allowed_author_emails=item.allowed_author_emails) for item in self.mining_targets)


def load_execution_snapshot(payload: dict):
    if payload.get('schema_version') == 4:
        return ExecutionSnapshotV4.model_validate(payload)
    if payload.get('schema_version') == 3:
        return ExecutionSnapshotV3.model_validate(payload)
    if payload.get('schema_version') == 3:
        return ExecutionSnapshotV3.model_validate(payload)
    if payload.get('schema_version') == 2:
        return ExecutionSnapshotV2.model_validate(payload)
    return ExecutionSnapshotV1.model_validate(payload)
