from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_uow
from app.api.main import create_app
from app.domain.entities.execution_snapshot import ExecutionSnapshotV1
from app.domain.entities.mining_execution import MiningExecution
from app.domain.monitoring_configuration import MonitoringConfiguration
from tests.fakes import MemoryUnitOfWork

NOW = datetime(2026, 9, 30, 12, tzinfo=UTC)


def test_scheduled_execution_uses_normal_history_detail_and_repository_routes_without_internal_context():
    uow = MemoryUnitOfWork()
    configuration = MonitoringConfiguration.create(identifier=uuid4(), name="Scheduled history",
        gitlab_url="https://gitlab.example", now=NOW)
    uow.configuration_repository.add(configuration)
    snapshot = ExecutionSnapshotV1.capture(configuration, uow.mining_scope_repository.get(configuration.id),
        trigger_type="scheduled", scheduled_occurrence=NOW+timedelta(days=1), schedule_version=9)
    execution = MiningExecution.create(snapshot, NOW).transition("running", NOW, expected_status="pending")
    execution = execution.transition("completed", NOW+timedelta(seconds=2), expected_status="running")
    uow.execution_repository.add(execution)
    uow.commit()

    app = create_app(scheduler_enabled=False)
    app.dependency_overrides[get_uow] = lambda: uow
    with TestClient(app) as client:
        global_history = client.get("/api/v1/executions")
        configuration_history = client.get(f"/api/v1/monitoring-configurations/{configuration.id}/executions")
        detail = client.get(f"/api/v1/executions/{execution.id}")
        repositories = client.get(f"/api/v1/executions/{execution.id}/repositories")

    assert global_history.status_code == configuration_history.status_code == detail.status_code == 200
    assert global_history.json()["items"][0]["triggerType"] == "scheduled"
    assert configuration_history.json()["items"][0]["id"] == str(execution.id)
    body = detail.json()
    assert body["triggerType"] == "scheduled" and body["status"] == "completed"
    assert body["counters"] == {"repositoryCount": 0, "successfulRepositoryCount": 0,
        "failedRepositoryCount": 0, "findingCount": 0, "scopeResolutionFailureCount": 0}
    assert repositories.status_code == 200 and repositories.json()["items"] == []
    serialized = str(body) + str(global_history.json()) + str(repositories.json())
    for private_field in ("scheduleContext", "scheduledOccurrence", "scheduledOccurrenceAt", "scheduleVersion"):
        assert private_field not in serialized
