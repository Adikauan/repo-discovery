from dataclasses import replace
from uuid import uuid4
from app.domain.entities.mining_scope import MiningScope, SelectedGitLabGroup, SelectedGitLabRepository
from tests.api.test_manual_execution_api import execution_api
from tests.unit.test_mining_execution import NOW


def test_execution_security_boundary(execution_api, caplog):
    client, uow, config = execution_api
    group = SelectedGitLabGroup(uuid4(), 'private-fingerprint', 12, 'Group', 'group', None, NOW)
    repo = SelectedGitLabRepository(uuid4(), 'private-fingerprint', 34, 'Repo', 'group/repo', 12, NOW)
    uow.scopes[config.id] = MiningScope(config.id, 1, NOW, (group,), (repo,))
    def forbidden(*_):
        raise AssertionError('credential-secret-must-not-be-read')
    uow.credential_repository.get = forbidden
    uow.schedule_repository.get = forbidden
    result = client.post(f'/api/v1/monitoring-configurations/{config.id}/executions')
    assert result.status_code == 201
    detail = result.json()
    assert detail['snapshot']['scope']['groups'][0]['gitlabGroupId'] == 12
    assert detail['snapshot']['scope']['repositories'][0]['gitlabProjectId'] == 34
    for response in (result, client.get(result.headers['Location']), client.get('/api/v1/executions')):
        for sensitive in ['private-fingerprint','schemaVersion','schema_version','credentialRevision','credential_revision','encrypted_token','credential-secret-must-not-be-read']:
            assert sensitive not in response.text
    assert 'credential-secret-must-not-be-read' not in caplog.text
    rejected = client.post(f'/api/v1/monitoring-configurations/{config.id}/executions', json={'token': 'secret-submitted'})
    assert rejected.status_code == 400 and 'secret-submitted' not in rejected.text


def test_failure_response_and_unexpected_error_are_safe(execution_api, monkeypatch):
    import app.api.v1.executions as routes
    from app.application.use_cases.create_manual_execution import CreateManualExecution
    client, uow, config = execution_api
    def failure():
        raise RuntimeError('database password=secret stacktrace provider payload')
    monkeypatch.setattr(routes, 'CreateManualExecution', lambda uow, **kwargs: CreateManualExecution(uow, orchestration=failure, **kwargs))
    response = client.post(f'/api/v1/monitoring-configurations/{config.id}/executions')
    assert response.status_code == 201
    assert response.json()['status'] == 'failed' and response.json()['completedAt'] is not None
    assert response.json()['error']['code'] == 'gitlab_credential_missing'
    assert response.json()['completionMeaning'] is None
    for word in ['password', 'stacktrace', 'provider payload', 'secret']:
        assert word not in response.text
    uow.execution_repository.get = lambda *a, **k: failure()
    response = client.get(f'/api/v1/executions/{uuid4()}')
    assert response.status_code == 500 and response.json()['code'] == 'unexpected_error'
    assert 'password' not in response.text and 'stacktrace' not in response.text
