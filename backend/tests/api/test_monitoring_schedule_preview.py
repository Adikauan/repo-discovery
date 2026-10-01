from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.dependencies import get_uow
from app.api.main import create_app
from app.domain.monitoring_configuration import MonitoringConfiguration
from tests.fakes import MemoryUnitOfWork


def setup_client():
    uow = MemoryUnitOfWork()
    config = MonitoringConfiguration.create(identifier=__import__("uuid").uuid4(), name="Preview",
        gitlab_url="https://gitlab.example", now=datetime(2026, 1, 1, tzinfo=UTC))
    uow.configuration_repository.add(config)
    app = create_app()
    app.dependency_overrides[get_uow] = lambda: uow
    return TestClient(app), uow, config


def candidate(**overrides):
    return {"recurrenceType": "monthly", "enabled": True, "executionTime": "08:00",
            "timezone": "UTC", "dayOfWeek": None, "dayOfMonth": 31, **overrides}


def test_preview_is_fixed_reference_authoritative_and_does_not_persist():
    client, uow, config = setup_client()
    response = client.post(f"/api/v1/monitoring-configurations/{config.id}/schedule/preview", json={
        "schedule": candidate(), "referenceInstant": "2026-04-01T00:00:00Z"})
    assert response.status_code == 200
    assert response.json()["nextOccurrence"]["instant"] == "2026-04-30T08:00:00Z"
    assert config.id not in uow.schedules


def test_disabled_preview_is_null_and_invalid_preview_is_normalized():
    client, uow, config = setup_client()
    path = f"/api/v1/monitoring-configurations/{config.id}/schedule/preview"
    disabled = client.post(path, json={"schedule": candidate(enabled=False),
                                       "referenceInstant": "2026-04-01T00:00:00Z"})
    assert disabled.status_code == 200 and disabled.json() == {"nextOccurrence": None}
    invalid = client.post(path, json={"schedule": candidate(dayOfMonth=32),
                                      "referenceInstant": "2026-04-01T00:00:00Z"})
    assert invalid.status_code == 422 and invalid.json()["code"] == "validation_error"
    assert config.id not in uow.schedules
