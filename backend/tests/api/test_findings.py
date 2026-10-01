from datetime import timedelta
from dataclasses import replace
from uuid import uuid4
from fastapi.testclient import TestClient

from app.api.dependencies import get_uow
from app.api.main import create_app
from app.domain.entities.execution_snapshot import ExecutionSnapshotV1
from app.domain.entities.finding import Finding
from app.domain.entities.mining_execution import MiningExecution
from app.domain.entities.repository_execution import RepositoryExecution
from tests.unit.test_create_manual_execution import setup
from tests.unit.test_mining_execution import NOW


def seeded(branch="main"):
    uow, config = setup()
    execution = MiningExecution.create(ExecutionSnapshotV1.capture(config, uow.mining_scope_repository.get(config.id)), NOW)
    execution = execution.transition("running", NOW + timedelta(seconds=1), expected_status="pending")
    uow.execution_repository.add(execution)
    repository = RepositoryExecution.create(execution.id, 42, "repo", "group/repo").transition(
        "running", NOW + timedelta(seconds=2), expected_status="pending")
    repository = replace(repository, processed_branch=branch)
    uow.repository_execution_repository.add(repository)
    finding = Finding(id=uuid4(), repository_execution_id=repository.id, rule_id="unauthorized-commit-author",
        rule_version="1", severity="warning", title="Unauthorized commit author",
        summary="Commit author is not in the allowed list.", commit_hash="a" * 40,
        author_email="writer@example.com", author_email_state="valid", author_name="Writer",
        authored_at=NOW, commit_message_summary="Update files", file_path=None, line_start=None,
        line_end=None, created_at=NOW + timedelta(seconds=3))
    uow.finding_repository.add(finding); uow.commit()
    app = create_app(scheduler_enabled=False); app.dependency_overrides[get_uow] = lambda: uow
    return TestClient(app), execution, repository, finding


def test_execution_repository_and_detail_finding_reads_are_safe_and_owned():
    client, execution, repository, finding = seeded()
    with client:
        execution_list = client.get("/api/v1/executions")
        first = client.get(f"/api/v1/executions/{execution.id}/findings")
        nested = client.get(f"/api/v1/executions/{execution.id}/repositories/{repository.id}/findings")
        detail = client.get(f"/api/v1/findings/{finding.id}")
    assert execution_list.status_code == first.status_code == nested.status_code == detail.status_code == 200
    assert execution_list.json()["items"][0]["findingCount"] == 1
    assert first.json()["items"][0]["repositoryFullPath"] == "group/repo"
    assert first.json()["items"][0]["repositoryName"] == "repo"
    assert first.json()["items"][0]["branch"] == "main"
    assert first.json()["items"][0]["executionId"] == str(execution.id)
    assert detail.json()["authorEmail"] == "writer@example.com"
    assert "allowedAuthorEmails" not in detail.text and "token" not in detail.text


def test_finding_reads_return_normalized_not_found_and_reject_nested_ownership_mismatch():
    client, execution, repository, _ = seeded()
    with client:
        missing = client.get(f"/api/v1/findings/{uuid4()}")
        wrong = client.get(f"/api/v1/executions/{uuid4()}/repositories/{repository.id}/findings")
    assert missing.status_code == 404 and wrong.status_code == 404


def test_legacy_finding_branch_is_nullable_without_live_gitlab_lookup():
    client, execution, _, _ = seeded(branch=None)
    response = client.get(f"/api/v1/executions/{execution.id}/findings")
    assert response.status_code == 200 and response.json()["items"][0]["branch"] is None
