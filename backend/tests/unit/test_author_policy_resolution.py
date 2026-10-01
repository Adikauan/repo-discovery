from uuid import uuid4

import pytest

from app.domain.entities.execution_snapshot import (ExecutionSnapshotV2, SnapshotAuthorPolicy,
    SnapshotGroup, SnapshotRepositoryGroupCoverage)
from app.domain.services.author_policy_resolver import AuthorPolicyResolutionError, resolve_author_policy


def snapshot(policies):
    return ExecutionSnapshotV2(configuration_id=uuid4(), configuration_name="fixture", configuration_enabled=True,
        gitlab_url="https://gitlab.example", trigger_type="manual", author_policy_mode="scope_aware",
        groups=(SnapshotGroup(gitlab_group_id=1, name="root", full_path="sequor", parent_group_id=None,
            instance_fingerprint="a" * 64), SnapshotGroup(gitlab_group_id=2, name="backend", full_path="sequor/backend",
            parent_group_id=1, instance_fingerprint="a" * 64)),
        group_author_policies=tuple(item for item in policies if item.scope_type == "group"),
        repository_branch_author_policies=tuple(item for item in policies if item.scope_type == "repository_branch"),
        repository_group_coverage=(SnapshotRepositoryGroupCoverage(gitlab_project_id=55, selected_group_id=1,
            distance_to_repository=2), SnapshotRepositoryGroupCoverage(gitlab_project_id=55, selected_group_id=2,
            distance_to_repository=1)))


def group(identifier, path, authors):
    return SnapshotAuthorPolicy(scope_type="group", instance_fingerprint="a" * 64,
        full_path=path, gitlab_group_id=identifier, allowed_author_emails=tuple(authors))


def repo(authors):
    return SnapshotAuthorPolicy(scope_type="repository_branch", instance_fingerprint="a" * 64,
        full_path="sequor/backend/api", gitlab_project_id=55, branch="main", allowed_author_emails=tuple(authors))


def test_parent_group_only():
    resolved = resolve_author_policy(snapshot((group(1, "sequor", ["a@example.com"]),)), 55,
        "sequor/backend/api", "main")
    assert resolved.allowed_author_emails == ("a@example.com",)


def test_child_group_only():
    resolved = resolve_author_policy(snapshot((group(2, "sequor/backend", ["b@example.com"]),)), 55,
        "sequor/backend/api", "main")
    assert resolved.allowed_author_emails == ("b@example.com",)


def test_child_group_wins_without_union_or_intersection():
    resolved = resolve_author_policy(snapshot((group(1, "sequor", ["a@example.com"]),
                                               group(2, "sequor/backend", ["b@example.com"]))), 55,
        "sequor/backend/api", "main")
    assert resolved.allowed_author_emails == ("b@example.com",)


def test_repository_branch_wins_over_parent_and_child_groups():
    resolved = resolve_author_policy(snapshot((group(1, "sequor", ["a@example.com"]),
        group(2, "sequor/backend", ["b@example.com"]), repo(["repo@example.com"]))), 55,
        "sequor/backend/api", "main")
    assert resolved.allowed_author_emails == ("repo@example.com",)


def test_equal_specificity_duplicate_group_paths_fail_safely():
    state = snapshot((group(1, "sequor/backend", ["a@example.com"]),
                      group(2, "sequor/backend", ["b@example.com"])))
    state = state.model_copy(update={"repository_group_coverage": (
        SnapshotRepositoryGroupCoverage(gitlab_project_id=55, selected_group_id=1, distance_to_repository=1),
        SnapshotRepositoryGroupCoverage(gitlab_project_id=55, selected_group_id=2, distance_to_repository=1))})
    with pytest.raises(AuthorPolicyResolutionError) as error:
        resolve_author_policy(state, 55, "sequor/backend/api", "main")
    assert error.value.code == "author_policy_ambiguous"


def test_missing_scope_aware_policy_disables_detection_and_explicit_empty_is_distinct():
    state = snapshot(())
    assert resolve_author_policy(state, 55, "sequor/backend/api", "main").allowed_author_emails is None
    empty_policy = repo(())
    assert resolve_author_policy(snapshot((empty_policy,)), 55, "sequor/backend/api", "main").allowed_author_emails == ()
