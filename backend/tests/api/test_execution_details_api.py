from uuid import uuid4
from dataclasses import replace
import pytest
from app.api.v1.execution_schemas import ExecutionDetail
from tests.api.test_manual_execution_api import execution_api
from tests.unit.test_mining_execution import pending, NOW


def test_detail_and_missing(execution_api):
    client, _, config = execution_api
    created = client.post(f'/api/v1/monitoring-configurations/{config.id}/executions')
    result = client.get(created.headers['Location'])
    assert result.status_code == 200 and result.json() == created.json()
    missing = client.get(f'/api/v1/executions/{uuid4()}')
    assert missing.status_code == 404 and missing.json()['code'] == 'not_found'


@pytest.mark.parametrize('status', ['pending','running','completed','partially_completed','failed'])
def test_completion_meaning_only_completed(status):
    item = pending()
    if status != 'pending':
        item = item.transition('running', NOW, expected_status='pending')
    if status not in ('pending','running'):
        item = item.transition(status, NOW, expected_status='running', error_code='orchestration_failed' if status == 'failed' else None)
    dto = ExecutionDetail.from_entity(item)
    assert (dto.completion_meaning is not None) == (status == 'completed')


def test_completion_meaning_distinguishes_legacy_orchestration_from_feature008_empty_scope():
    legacy = pending().transition('running', NOW, expected_status='pending').transition('completed', NOW, expected_status='running')
    assert ExecutionDetail.from_entity(legacy).completion_meaning == 'Feature 006 orchestration completed; repository mining was not performed.'
    mined_empty = replace(legacy, repository_mining_completed=True)
    assert ExecutionDetail.from_entity(mined_empty).completion_meaning == 'Repository processing completed successfully; the effective scope contained no repositories.'
