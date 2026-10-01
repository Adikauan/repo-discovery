from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_uow
from app.api.main import create_app
from app.domain.monitoring_configuration import MonitoringConfiguration
from tests.fakes import MemoryUnitOfWork


def setup_client():
    uow = MemoryUnitOfWork()
    config = MonitoringConfiguration.create(identifier=uuid4(), name="Schedule API",
        description="Keep this", gitlab_url="https://gitlab.example", now=datetime(2026, 9, 28, tzinfo=UTC))
    uow.configuration_repository.add(config)
    app = create_app()
    app.dependency_overrides[get_uow] = lambda: uow
    return TestClient(app), uow, config


def payload(**overrides):
    return {"recurrenceType": "daily", "enabled": True, "executionTime": "09:30",
            "timezone": "UTC", "dayOfWeek": None, "dayOfMonth": None, **overrides}


def test_schedule_get_put_reload_and_no_public_version():
    client, uow, config = setup_client()
    path = f"/api/v1/monitoring-configurations/{config.id}/schedule"
    initial = client.get(path)
    assert initial.status_code == 200 and initial.headers["etag"] == '"0"'
    assert initial.json() == {"schedule": None, "nextOccurrence": None}
    saved = client.put(path, headers={"If-Match": '"0"'}, json=payload())
    assert saved.status_code == 200 and saved.headers["etag"] == '"1"'
    assert saved.json()["schedule"] == payload()
    assert "version" not in saved.json()["schedule"]
    assert client.get(path).json()["schedule"] == payload()
    listed = client.get("/api/v1/monitoring-configurations").json()["items"][0]
    assert listed["scheduleSummary"] == payload()
    disabled = client.put(path, headers={"If-Match": '"1"'}, json=payload(enabled=False))
    assert disabled.status_code == 200
    assert client.get("/api/v1/monitoring-configurations").json()["items"][0]["scheduleSummary"]["enabled"] is False
    assert uow.configuration_repository.get_active(config.id).description == "Keep this"


def test_stale_and_invalid_requests_preserve_winning_schedule():
    client, uow, config = setup_client()
    path = f"/api/v1/monitoring-configurations/{config.id}/schedule"
    saved = client.put(path, headers={"If-Match": '"0"'}, json=payload())
    winner = saved.json()["schedule"]
    stale = client.put(path, headers={"If-Match": '"0"'}, json=payload(executionTime="10:00"))
    assert stale.status_code == 412 and stale.json()["code"] == "stale_update"
    invalid = client.put(path, headers={"If-Match": '"1"'}, json=payload(dayOfMonth=31))
    assert invalid.status_code == 422 and invalid.json()["code"] == "validation_error"
    assert client.get(path).json()["schedule"] == winner
    assert uow.configuration_repository.get_active(config.id).name == "Schedule API"


def test_preconditions_not_found_and_malformed_request_codes():
    client, _, config = setup_client()
    path = f"/api/v1/monitoring-configurations/{config.id}/schedule"
    assert client.put(path, json=payload()).json()["code"] == "invalid_precondition"
    assert client.put(path, headers={"If-Match": "bad"}, json=payload()).json()["code"] == "invalid_request"
    missing = client.get(f"/api/v1/monitoring-configurations/{uuid4()}/schedule")
    assert missing.status_code == 404 and missing.json()["code"] == "not_found"


def test_timezone_catalogue_is_sorted_and_includes_utc():
    client, _, _ = setup_client()
    response = client.get("/api/v1/schedule-timezones")
    assert response.status_code == 200
    assert response.json()["timezones"] == sorted(response.json()["timezones"])
    assert "UTC" in response.json()["timezones"]
