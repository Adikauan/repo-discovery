from uuid import uuid4

import pytest

from app.domain.author_policy import AuthorPolicy, AuthorPolicyAuthor
from app.domain.errors import FieldValidationError


def test_repository_branch_policy_normalizes_authors_and_keeps_branch_identity():
    policy = AuthorPolicy.repository_branch(
        identifier=uuid4(),
        configuration_id=uuid4(),
        instance_fingerprint="a" * 64,
        gitlab_project_id=42,
        branch="release/2026-q4",
        full_path="sequor/api-gateway",
        allowed_author_emails=[" Alice@example.com ", "alice@EXAMPLE.com", "bob@example.com"],
    )

    assert policy.scope_type == "repository_branch"
    assert policy.gitlab_project_id == 42
    assert policy.branch == "release/2026-q4"
    assert policy.allowed_author_emails == ("alice@example.com", "bob@example.com")
    assert policy.gitlab_group_id is None


def test_group_policy_has_no_branch_or_repository_identity():
    policy = AuthorPolicy.group(
        identifier=uuid4(),
        configuration_id=uuid4(),
        instance_fingerprint="b" * 64,
        gitlab_group_id=17,
        full_path="sequor/backend",
        allowed_author_emails=["group@example.com"],
    )

    assert policy.scope_type == "group"
    assert policy.gitlab_group_id == 17
    assert policy.gitlab_project_id is None
    assert policy.branch is None


@pytest.mark.parametrize(
    "arguments",
    [
        {"gitlab_group_id": 17, "gitlab_project_id": 42, "branch": "main"},
        {"gitlab_group_id": 17, "gitlab_project_id": None, "branch": "main"},
        {"gitlab_group_id": None, "gitlab_project_id": 42, "branch": None},
    ],
)
def test_invalid_policy_scope_shape_is_rejected(arguments):
    with pytest.raises(FieldValidationError):
        AuthorPolicy.create(
            identifier=uuid4(),
            configuration_id=uuid4(),
            instance_fingerprint="c" * 64,
            full_path="some/path",
            allowed_author_emails=[],
            **arguments,
        )


def test_empty_author_policy_is_distinct_from_missing_policy():
    policy = AuthorPolicy.group(
        identifier=uuid4(),
        configuration_id=uuid4(),
        instance_fingerprint="d" * 64,
        gitlab_group_id=17,
        full_path="sequor/backend",
        allowed_author_emails=[],
    )

    assert policy is not None
    assert policy.allowed_author_emails == ()


def test_policy_author_child_is_normalized():
    author = AuthorPolicyAuthor.create(uuid4(), " Alice@Example.com ")

    assert author.normalized_email == "alice@example.com"
