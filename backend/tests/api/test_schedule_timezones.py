from fastapi.testclient import TestClient

from app.api.dependencies import get_uow
from app.api.main import create_app
from app.domain.monitoring_configuration import MonitoringConfiguration
from tests.fakes import MemoryUnitOfWork
from datetime import UTC, datetime
from uuid import uuid4


def test_schedule_timezone_api_preserves_a_supported_alias_exactly():
    uow = MemoryUnitOfWork()
    config = MonitoringConfiguration.create(identifier=uuid4(), name="Timezone alias",
        gitlab_url="https://gitlab.example", now=datetime(2026, 1, 1, tzinfo=UTC))
    uow.configuration_repository.add(config)
    app = create_app()
    app.dependency_overrides[get_uow] = lambda: uow
    client = TestClient(app)
    path = f"/api/v1/monitoring-configurations/{config.id}/schedule"
    body = {"recurrenceType": "daily", "enabled": False, "executionTime": "09:00",
            "timezone": "Etc/UTC", "dayOfWeek": None, "dayOfMonth": None}
    response = client.put(path, headers={"If-Match": '"0"'}, json=body)
    assert response.status_code == 200 and response.json()["schedule"]["timezone"] == "Etc/UTC"
    assert client.get(path).json()["schedule"]["timezone"] == "Etc/UTC"


def test_timezone_catalogue_reports_safe_failure_when_runtime_database_is_missing(monkeypatch):
    from app.application.use_cases import list_schedule_timezones
    monkeypatch.setattr(list_schedule_timezones, "available_timezones",
                        lambda: (_ for _ in ()).throw(OSError("timezone internals SECRET")))
    app = create_app()
    app.dependency_overrides[get_uow] = lambda: MemoryUnitOfWork()
    response = TestClient(app, raise_server_exceptions=False).get("/api/v1/schedule-timezones")
    assert response.status_code == 500
    assert response.json()["code"] == "unexpected_error"
    assert "timezone internals" not in response.text and "SECRET" not in response.text
