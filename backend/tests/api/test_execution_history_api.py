from tests.api.test_manual_execution_api import execution_api


def test_lists_filters_pagination_and_retired_history(execution_api):
    client, uow, config = execution_api
    root = f'/api/v1/monitoring-configurations/{config.id}/executions'
    for _ in range(3):
        assert client.post(root).status_code == 201
    for path in ['/api/v1/executions', root]:
        result = client.get(path + '?pageSize=2').json()
        assert len(result['items']) == 2 and result['totalItems'] == 3 and result['totalPages'] == 2
        assert result['items'][0]['createdAt'] >= result['items'][1]['createdAt']
        assert len(client.get(path + '?status=failed').json()['items']) == 3
        assert client.get(path + '?triggerType=scheduled').json()['items'] == []
        for query in ['page=0', 'pageSize=101', 'status=bad', 'triggerType=bad']:
            response = client.get(path + '?' + query)
            assert response.status_code == 422 and response.json()['code'] == 'validation_error'
    uow.configurations[config.id] = config.retire(config.created_at)
    uow.commit()
    assert client.get(root).json()['totalItems'] == 3
