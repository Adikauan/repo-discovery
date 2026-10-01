from fastapi.testclient import TestClient
import pytest
from app.api.main import create_app
from app.api.dependencies import get_uow
from tests.unit.test_create_manual_execution import setup, seed


@pytest.fixture
def execution_api():
    uow, config = setup()
    app = create_app()
    app.dependency_overrides[get_uow] = lambda: uow
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, uow, config


def test_create_bodyless_completed_and_replay(execution_api):
    client, uow, config = execution_api
    url = f'/api/v1/monitoring-configurations/{config.id}/executions'
    result = client.post(url, headers={'Idempotency-Key': 'execution-test'})
    assert result.status_code == 201
    data = result.json()
    assert data['status'] == 'failed' and data['triggerType'] == 'manual'
    assert data['snapshot']['configurationEnabled'] is False
    assert data['completionMeaning'] is None
    assert data['error']['code'] == 'gitlab_credential_missing'
    assert all(v == 0 for v in data['counters'].values())
    assert result.headers['Location'] == f"/api/v1/executions/{data['id']}"
    assert client.post(url, headers={'Idempotency-Key': 'execution-test'}).json()['id'] == data['id']
    assert client.post(url, json={'status': 'scheduled'}).status_code == 400
    assert client.post(url, headers={'Idempotency-Key': 'bad key'}).status_code == 400
    assert client.patch(result.headers['Location'], json={'status': 'running'}).status_code == 405


def test_missing_retired_and_safe_failure(execution_api):
    client, uow, config = execution_api
    from uuid import uuid4
    assert client.post(f'/api/v1/monitoring-configurations/{uuid4()}/executions').status_code == 404
    uow.configurations[config.id] = config.retire(config.created_at)
    uow.commit()
    assert client.post(f'/api/v1/monitoring-configurations/{config.id}/executions').status_code == 404


def test_non_stale_conflict_and_stale_reconciliation(execution_api):
    from datetime import UTC, datetime, timedelta
    from dataclasses import replace
    client, uow, config = execution_api
    old = seed(uow, config)
    now = datetime.now(UTC)
    uow.executions[old.id] = replace(old, created_at=now)
    uow.commit()
    url = f'/api/v1/monitoring-configurations/{config.id}/executions'
    result = client.post(url)
    assert result.status_code == 409 and result.json()['code'] == 'conflict'
    assert uow.executions[old.id].status == 'pending'
    uow.executions[old.id] = replace(old, created_at=now - timedelta(minutes=6))
    uow.commit()
    assert client.post(url).status_code == 201
    assert uow.executions[old.id].status == 'failed'
