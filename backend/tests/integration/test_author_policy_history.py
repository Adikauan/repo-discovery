from datetime import UTC, datetime
from uuid import uuid4

from app.application.use_cases.author_policies import MigrateAuthorPolicyMode
from app.application.use_cases.create_manual_execution import CreateManualExecution
from app.domain.author_policy import AuthorPolicy
from app.domain.entities.finding import Finding
from app.domain.entities.repository_checkpoint import RepositoryCheckpoint
from app.domain.entities.repository_execution import RepositoryExecution
from app.domain.monitoring_configuration import MonitoringConfiguration


NOW = datetime(2026, 9, 30, 12, tzinfo=UTC)


def test_scope_policy_change_preserves_legacy_execution_finding_and_checkpoint(pg_uow_factory):
    creation = pg_uow_factory()
    configuration = MonitoringConfiguration.create(identifier=uuid4(), name="Legacy policy history",
        gitlab_url="https://gitlab.example", allowed_author_emails=["Alice@example.com"], now=NOW)
    creation.configuration_repository.add(configuration)
    creation.commit()

    execution = CreateManualExecution(pg_uow_factory(), clock=lambda: NOW).execute(configuration.id)
    snapshot = execution.snapshot.model_dump(mode="json")
    run_uow = pg_uow_factory()
    repository = RepositoryExecution.create(execution.id, 42, "API", "team/api")
    run_uow.repository_execution_repository.add(repository)
    run_uow.commit()
    finding = Finding(id=uuid4(), repository_execution_id=repository.id, rule_id="unauthorized_commit_author",
        rule_version="1", severity="warning", title="Unauthorized commit author",
        summary="Commit author is not allowed by the captured configuration.", commit_hash="a" * 40,
        author_email="outsider@example.com", author_email_state="valid", author_name="Outside",
        authored_at=NOW, commit_message_summary="Update service", file_path=None, line_start=None,
        line_end=None, created_at=NOW)
    run_uow.finding_repository.add(finding)
    checkpoint = RepositoryCheckpoint(uuid4(), configuration.id, 42, "main", "b" * 40, NOW)
    run_uow.repository_checkpoint_repository.put(checkpoint)
    run_uow.commit()

    switch = pg_uow_factory()
    current = switch.configuration_repository.get_active(configuration.id)
    policy = AuthorPolicy.repository_branch(identifier=uuid4(), configuration_id=configuration.id,
        instance_fingerprint="a" * 64, gitlab_project_id=42, branch="main", full_path="team/api",
        allowed_author_emails=["new@example.com"])
    switch.author_policy_repository.upsert(policy)
    switch.commit()
    MigrateAuthorPolicyMode(pg_uow_factory(), clock=lambda: NOW).execute(configuration.id, current.revision)

    historical = pg_uow_factory()
    saved_execution = historical.execution_repository.get(execution.id)
    saved_finding = historical.finding_repository.get(finding.id)
    saved_checkpoint = historical.repository_checkpoint_repository.get(configuration.id, 42, "main")
    saved_configuration = historical.configuration_repository.get(configuration.id)
    assert saved_execution.snapshot.model_dump(mode="json") == snapshot
    assert saved_execution.snapshot.legacy_allowed_author_emails == ("alice@example.com",)
    assert saved_finding == finding
    assert saved_checkpoint == checkpoint
    assert saved_configuration.allowed_author_emails == ("alice@example.com",)
    assert saved_configuration.author_policy_mode == "scope_aware"
