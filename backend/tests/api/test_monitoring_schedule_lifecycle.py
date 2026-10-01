from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_uow
from app.api.main import create_app
from app.domain.entities.mining_scope import MiningScope
from app.domain.monitoring_configuration import MonitoringConfiguration
from tests.fakes import MemoryUnitOfWork


def test_disable_reenable_and_remove_preserve_configuration_and_scope():
    uow = MemoryUnitOfWork()
    config = MonitoringConfiguration.create(identifier=uuid4(), name="Lifecycle", description="Keep",
        gitlab_url="https://gitlab.example", now=datetime(2026, 1, 1, tzinfo=UTC))
    config = config.set_enabled(True, datetime(2026, 1, 2, tzinfo=UTC))
    uow.configuration_repository.add(config)
    uow.scopes[config.id] = MiningScope(config.id, 1, datetime(2026, 1, 2, tzinfo=UTC))
    app = create_app()
    app.dependency_overrides[get_uow] = lambda: uow
    client = TestClient(app)
    path = f"/api/v1/monitoring-configurations/{config.id}/schedule"
    schedule = {"recurrenceType": "weekly", "enabled": True, "executionTime": "09:00",
                "timezone": "UTC", "dayOfWeek": 1, "dayOfMonth": None}
    saved = client.put(path, headers={"If-Match": '"0"'}, json=schedule)
    assert saved.status_code == 200 and saved.headers["etag"] == '"1"'
    disabled = client.put(path, headers={"If-Match": '"1"'}, json={**schedule, "enabled": False})
    assert disabled.status_code == 200 and disabled.json()["nextOccurrence"] is None
    assert disabled.json()["schedule"]["dayOfWeek"] == 1
    enabled = client.put(path, headers={"If-Match": '"2"'}, json=schedule)
    assert enabled.status_code == 200 and enabled.headers["etag"] == '"3"'
    removed = client.delete(path, headers={"If-Match": '"3"'})
    assert removed.status_code == 204 and removed.headers["etag"] == '"4"'
    assert client.get(path).json() == {"schedule": None, "nextOccurrence": None}
    assert client.get(path).headers["etag"] == '"4"'
    assert uow.configuration_repository.get_active(config.id) == config
    assert uow.mining_scope_repository.get(config.id) == uow.scopes[config.id]
