from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.infrastructure.database.models import (
    AuthorPolicyAuthorRecord,
    AuthorPolicyRecord,
    MonitoringConfigurationRecord,
)


def seed_configuration(session):
    identifier = uuid4()
    now = datetime.now(UTC)
    session.add(MonitoringConfigurationRecord(
        id=identifier, name="Policy test", description=None, gitlab_url="https://gitlab.example",
        enabled=False, created_at=now, updated_at=now, revision=1, retired_at=None,
        allowed_author_emails=[], author_policy_mode="legacy",
    ))
    session.flush()
    return identifier


def test_postgres_policy_constraints_and_email_uniqueness(pg_uow_factory):
    uow = pg_uow_factory()
    session = uow.session
    configuration_id = seed_configuration(session)
    policy_id = uuid4()
    session.add(AuthorPolicyRecord(
        id=policy_id, monitoring_configuration_id=configuration_id, scope_type="repository_branch",
        instance_fingerprint="a" * 64, gitlab_group_id=None, gitlab_project_id=42, branch="main",
        full_path="group/repo",
    ))
    session.flush()
    session.add(AuthorPolicyAuthorRecord(policy_id=policy_id, normalized_email="alice@example.com",
                                         display_email="alice@example.com"))
    session.flush()
    with pytest.raises(IntegrityError):
        session.add(AuthorPolicyAuthorRecord(policy_id=policy_id, normalized_email="alice@example.com",
                                             display_email="alice@example.com"))
        session.flush()
    session.rollback()


def test_postgres_policy_identity_unique_and_scope_shape_checks(pg_uow_factory):
    uow = pg_uow_factory()
    session = uow.session
    configuration_id = seed_configuration(session)
    values = dict(
        monitoring_configuration_id=configuration_id, scope_type="group", instance_fingerprint="b" * 64,
        gitlab_group_id=17, gitlab_project_id=None, branch=None, full_path="group",
    )
    session.add(AuthorPolicyRecord(id=uuid4(), **values))
    session.flush()
    with pytest.raises(IntegrityError):
        session.add(AuthorPolicyRecord(id=uuid4(), **values))
        session.flush()
    session.rollback()
    invalid = dict(values, scope_type="group", gitlab_project_id=42, branch="main")
    with pytest.raises(IntegrityError):
        session.add(AuthorPolicyRecord(id=uuid4(), **invalid))
        session.flush()
