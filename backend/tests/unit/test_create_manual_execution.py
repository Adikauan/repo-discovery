from datetime import timedelta
from uuid import uuid4
import pytest
from app.domain.monitoring_configuration import MonitoringConfiguration
from app.domain.entities.execution_snapshot import ExecutionSnapshotV1
from app.domain.entities.mining_execution import MiningExecution
from app.domain.errors import ConflictError, NotFoundError, IdempotencyConflict
from app.application.use_cases.create_manual_execution import CreateManualExecution
from tests.fakes import MemoryUnitOfWork
from tests.unit.test_mining_execution import NOW


def setup():
    uow = MemoryUnitOfWork()
    config = MonitoringConfiguration.create(identifier=uuid4(), name='Original', gitlab_url='https://gitlab.example.com', now=NOW)
    uow.configuration_repository.add(config)
    uow.commit()
    return uow, config


def seed(uow, config, status='pending', age=301):
    item = MiningExecution.create(ExecutionSnapshotV1.capture(config, uow.mining_scope_repository.get(config.id)), NOW - timedelta(seconds=age))
    if status == 'running':
        item = item.transition('running', item.created_at, expected_status='pending')
    uow.execution_repository.add(item)
    uow.commit()
    return item


def test_disabled_configuration_success_and_internal_sequence():
    uow, config = setup()
    statuses = []
    original = uow.execution_repository.transition
    def record(item, expected):
        statuses.append((expected, item.status))
        return original(item, expected)
    uow.execution_repository.transition = record
    item = CreateManualExecution(uow, clock=lambda: NOW).execute(config.id)
    assert statuses == [('pending', 'running'), ('running', 'completed')]
    assert not config.enabled and item.status == 'completed' and not item.active
    assert item.snapshot.configuration_name == config.name
    assert all(getattr(item, field) == 0 for field in ['repository_count','successful_repository_count','failed_repository_count','finding_count'])
    assert uow.execution_repository.active_for(config.id) is None
    assert len(uow.executions) == 1 and not uow.credentials and not uow.schedules


@pytest.mark.parametrize('status', ['pending', 'running'])
@pytest.mark.parametrize('age', [299, 300, 301])
def test_staleness_boundary(status, age):
    uow, config = setup()
    old = seed(uow, config, status, age)
    usecase = CreateManualExecution(uow, clock=lambda: NOW)
    if age <= 300:
        with pytest.raises(ConflictError):
            usecase.execute(config.id)
        assert uow.executions == {old.id: old}
    else:
        new = usecase.execute(config.id)
        failed = uow.execution_repository.get(old.id)
        assert failed.status == 'failed' and failed.completed_at == NOW
        assert failed.started_at == old.started_at and failed.snapshot == old.snapshot
        assert failed.error_code == 'execution_interrupted' and failed.repository_count == 0
        assert new.id != old.id and new.status == 'completed'


def test_controlled_failure_is_safe_final_and_allows_later_request():
    uow, config = setup()
    def fail():
        raise RuntimeError('token-secret database stacktrace')
    failed = CreateManualExecution(uow, clock=lambda: NOW, orchestration=fail).execute(config.id)
    assert failed.status == 'failed' and failed.completed_at == NOW
    assert failed.error_code == 'orchestration_failed'
    assert 'secret' not in repr(failed) and 'stacktrace' not in repr(failed)
    assert not failed.active and failed.finding_count == 0
    assert CreateManualExecution(uow, clock=lambda: NOW).execute(config.id).status == 'completed'


def test_missing_retired_and_idempotency():
    uow, config = setup()
    service = CreateManualExecution(uow, clock=lambda: NOW)
    first = service.execute(config.id, 'same-key')
    assert service.execute(config.id, 'same-key') == first
    assert len(uow.executions) == 1
    other = MonitoringConfiguration.create(identifier=uuid4(), name='Other', gitlab_url=config.gitlab_url, now=NOW)
    uow.configuration_repository.add(other)
    uow.commit()
    with pytest.raises(IdempotencyConflict):
        service.execute(other.id, 'same-key')
    with pytest.raises(NotFoundError):
        service.execute(uuid4())
    uow.configurations[config.id] = config.retire(NOW)
    uow.commit()
    with pytest.raises(NotFoundError):
        service.execute(config.id)


@pytest.mark.parametrize('value', [0, -1, float('nan'), float('inf'), float('-inf')])
def test_invalid_threshold(value):
    uow, _ = setup()
    with pytest.raises(ValueError):
        CreateManualExecution(uow, threshold=value)
    from app.config import Settings
    with pytest.raises(ValueError):
        Settings(execution_staleness_threshold_seconds=value)


def test_pre_start_failure_and_stale_same_key_replay():
    import hashlib
    from app.application.ports.create_request_store import CreateRequestReceipt
    uow, config = setup()
    def fail():
        raise RuntimeError('private pre-start detail')
    failed = CreateManualExecution(uow, clock=lambda: NOW, before_start=fail).execute(config.id)
    assert failed.status == 'failed' and failed.started_at is None and failed.completed_at == NOW
    old = seed(uow, config)
    fingerprint = hashlib.sha256(f'manual-execution:{config.id}'.encode()).hexdigest()
    uow.receipt_repository.add(CreateRequestReceipt('stale-key', fingerprint, {'execution_id': str(old.id)}))
    uow.commit()
    replay = CreateManualExecution(uow, clock=lambda: NOW).execute(config.id, 'stale-key')
    assert replay.id == old.id and replay.status == 'failed' and len(uow.executions) == 2


def test_execution_transition_guard_rejects_lost_race():
    from app.application.use_cases.transition_execution import TransitionExecution
    uow, config = setup()
    old = seed(uow, config)
    uow.execution_repository.transition = lambda *_: False
    with pytest.raises(ConflictError):
        TransitionExecution(uow, clock=lambda: NOW).execute(old.id, 'pending', 'running')
    assert uow.executions[old.id] == old
