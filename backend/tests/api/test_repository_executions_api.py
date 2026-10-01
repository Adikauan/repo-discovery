from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

from app.domain.entities.execution_snapshot import ExecutionSnapshotV1
from app.domain.entities.mining_execution import MiningExecution
from app.domain.entities.repository_execution import RepositoryExecution
from tests.unit.test_create_manual_execution import setup
from tests.unit.test_mining_execution import NOW
from app.api.main import create_app
from app.api.dependencies import get_uow
from fastapi.testclient import TestClient


def test_read_api_returns_interrupted_running_state_without_debug_metadata():
    uow, config = setup()
    execution = MiningExecution.create(ExecutionSnapshotV1.capture(config, uow.mining_scope_repository.get(config.id)), NOW)
    execution = execution.transition("running", NOW + timedelta(seconds=1), expected_status="pending")
    uow.execution_repository.add(execution)
    row = RepositoryExecution.create(execution.id, 100, "worker", "team/worker", "qualidade").transition("running", NOW + timedelta(seconds=2), expected_status="pending")
    uow.repository_execution_repository.add(row); uow.commit()
    app = create_app(); app.dependency_overrides[get_uow] = lambda: uow
    with TestClient(app) as client:
        detail = client.get(f"/api/v1/executions/{execution.id}/repositories").json()
        parent = client.get(f"/api/v1/executions/{execution.id}").json()
        repository = client.get(f"/api/v1/executions/{execution.id}/repositories/{row.id}").json()
    assert parent["status"] == "running"
    assert detail["items"][0]["status"] == "running"
    assert repository["completedAt"] is None and repository["processedBranch"] is None
    assert repository["targetBranch"] == "qualidade"
    assert repository["fileCount"] == 0 and repository["findingCount"] == 0
    assert "secret" not in str(detail) and "traceback" not in str(repository).lower()


def test_repository_error_api_projects_only_normalized_safe_summary():
    uow, config = setup()
    execution = MiningExecution.create(ExecutionSnapshotV1.capture(config, uow.mining_scope_repository.get(config.id)), NOW)
    execution = execution.transition("running", NOW + timedelta(seconds=1), expected_status="pending")
    uow.execution_repository.add(execution)
    row = RepositoryExecution.create(execution.id, 101, "private", "team/private")
    row = row.transition("running", NOW + timedelta(seconds=2), expected_status="pending")
    row = row.fail("repository_timeout", NOW + timedelta(seconds=3))
    uow.repository_execution_repository.add(row); uow.commit()
    app = create_app(); app.dependency_overrides[get_uow] = lambda: uow
    with TestClient(app) as client:
        result = client.get(f"/api/v1/executions/{execution.id}/repositories/{row.id}")
    assert result.status_code == 200
    assert result.json()["error"] == {"code": "repository_timeout", "summary": "The repository request timed out."}
    assert "PRIVATE-TOKEN" not in result.text and "encrypted_token" not in result.text


def test_repository_list_is_paginated_and_deterministically_ordered():
    uow, config = setup()
    execution = MiningExecution.create(ExecutionSnapshotV1.capture(config, uow.mining_scope_repository.get(config.id)), NOW)
    execution = execution.transition("running", NOW + timedelta(seconds=1), expected_status="pending")
    uow.execution_repository.add(execution)
    for project_id, path in ((3, "team/z"), (2, "team/a"), (1, "team/m")):
        row = RepositoryExecution.create(execution.id, project_id, path.rsplit("/", 1)[-1], path,
            "qualidade" if project_id == 2 else None)
        uow.repository_execution_repository.add(row)
    uow.commit()
    app = create_app(); app.dependency_overrides[get_uow] = lambda: uow
    with TestClient(app) as client:
        result = client.get(f"/api/v1/executions/{execution.id}/repositories?page=1&pageSize=2")
    body = result.json()
    assert result.status_code == 200
    assert [item["repositoryFullPath"] for item in body["items"]] == ["team/a", "team/m"]
    assert body["items"][0]["targetBranch"] == "qualidade"
    assert body["totalItems"] == 3 and body["totalPages"] == 2
