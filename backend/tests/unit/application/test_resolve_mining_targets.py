from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
from app.application.use_cases.resolve_mining_targets import ResolveMiningTargets
from app.domain.author_policy import AuthorPolicy
from app.domain.entities.mining_scope import MiningScope, SelectedGitLabGroup, SelectedGitLabRepository
from app.domain.errors import FieldValidationError
from app.domain.monitoring_configuration import MonitoringConfiguration
from tests.fakes import MemoryUnitOfWork

NOW = datetime(2026, 10, 1, tzinfo=UTC)


class Provider:
    def __init__(self, projects):
        self.projects = projects

    def get_project_scope(self, url, token, project_id):
        return self.projects[project_id]

    def get_group(self, url, token, group_id):
        return object()

    def group_children(self, url, token, group_id):
        return (), tuple(project for project in self.projects.values() if project.id in {42, 43})


def project(project_id, name):
    return type("Project", (), {"id": project_id, "name": name, "full_path": f"backend/{name}"})()


def test_policy_branch_alone_resolves_dev_larah_target_without_scope_branch_state():
    config = MonitoringConfiguration.create(identifier=uuid4(), name="dev-larah", gitlab_url="https://gitlab.example", now=NOW)
    fingerprint = normalized_url_fingerprint(config.gitlab_url)
    scope = MiningScope(config.id, 1, NOW, repositories=(SelectedGitLabRepository(
        uuid4(), fingerprint, 42, "api", "backend/api", None, NOW),))
    policy = AuthorPolicy.repository_branch(identifier=uuid4(), configuration_id=config.id,
        instance_fingerprint=fingerprint, gitlab_project_id=42, branch="dev-larah", full_path="backend/api",
        allowed_author_emails=[" Dev@example.com "])
    result = ResolveMiningTargets(Provider({42: project(42, "api")})).execute(config, scope, "token", [policy])
    assert [(item.gitlab_project_id, item.branch, item.allowed_author_emails) for item in result] == [
        (42, "dev-larah", ("dev@example.com",))]


def test_multiple_repository_branch_policies_create_independent_targets_and_allowlists():
    config = MonitoringConfiguration.create(identifier=uuid4(), name="multi-branch",
        gitlab_url="https://gitlab.example", now=NOW)
    fingerprint = normalized_url_fingerprint(config.gitlab_url)
    scope = MiningScope(config.id, 1, NOW, repositories=(SelectedGitLabRepository(
        uuid4(), fingerprint, 42, "api", "backend/api", None, NOW),))
    policies = [
        AuthorPolicy.repository_branch(identifier=uuid4(), configuration_id=config.id,
            instance_fingerprint=fingerprint, gitlab_project_id=42, branch="main", full_path="backend/api",
            allowed_author_emails=["main@example.com"]),
        AuthorPolicy.repository_branch(identifier=uuid4(), configuration_id=config.id,
            instance_fingerprint=fingerprint, gitlab_project_id=42, branch="dev-larah", full_path="backend/api",
            allowed_author_emails=["dev@example.com"]),
    ]

    result = ResolveMiningTargets(Provider({42: project(42, "api")})).execute(config, scope, "token", policies)

    assert {(item.gitlab_project_id, item.branch, item.allowed_author_emails) for item in result} == {
        (42, "main", ("main@example.com",)), (42, "dev-larah", ("dev@example.com",))}


def test_new_group_descendant_without_policy_blocks_entire_target_resolution():
    config = MonitoringConfiguration.create(identifier=uuid4(), name="dynamic", gitlab_url="https://gitlab.example", now=NOW)
    fingerprint = normalized_url_fingerprint(config.gitlab_url)
    scope = MiningScope(config.id, 1, NOW, groups=(SelectedGitLabGroup(
        uuid4(), fingerprint, 31, "backend", "backend", None, NOW),))
    provider = Provider({42: project(42, "api-a"), 43: project(43, "api-b")})
    policy = AuthorPolicy.repository_branch(identifier=uuid4(), configuration_id=config.id,
        instance_fingerprint=fingerprint, gitlab_project_id=42, branch="main", full_path="backend/api-a",
        allowed_author_emails=[])
    with pytest.raises(FieldValidationError) as error:
        ResolveMiningTargets(provider).execute(config, scope, "token", [policy])
    assert error.value.field == "policies" and error.value.code == "incomplete"
