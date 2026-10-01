from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from uuid import uuid4
import pytest

from app.application.use_cases.create_manual_execution import CreateManualExecution
from app.application.use_cases.transition_execution import TransitionExecution
from app.application.use_cases.process_mining_execution import ProcessMiningExecution
from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
from app.domain.entities.execution_snapshot import ExecutionSnapshotV1
from app.domain.entities.mining_execution import MiningExecution
from app.domain.monitoring_configuration import MonitoringConfiguration
from app.domain.errors import ConflictError
from tests.unit.test_mining_execution import NOW
from tests.fakes import FakeCipher


def owner(factory):
    uow = factory()
    config = MonitoringConfiguration.create(identifier=uuid4(), name='Concurrency', gitlab_url='https://gitlab.example.com', now=NOW)
    uow.configuration_repository.add(config)
    uow.commit()
    return config


def active(factory, config, status='pending', age=301):
    uow = factory()
    item = MiningExecution.create(ExecutionSnapshotV1.capture(config, uow.mining_scope_repository.get(config.id)), NOW - timedelta(seconds=age))
    if status == 'running':
        item = item.transition('running', item.created_at, expected_status='pending')
    uow.execution_repository.add(item)
    uow.commit()
    return item


@pytest.mark.parametrize('status', ['pending', 'running'])
def test_stale_reconciliation_and_replay(pg_uow_factory, status):
    config = owner(pg_uow_factory)
    old = active(pg_uow_factory, config, status)
    result = CreateManualExecution(pg_uow_factory(), clock=lambda: NOW).execute(config.id, 'same')
    check = pg_uow_factory()
    failed = check.execution_repository.get(old.id)
    assert failed.status == 'failed' and failed.completed_at == NOW and failed.snapshot == old.snapshot
    assert failed.started_at == old.started_at and failed.error_code == 'execution_interrupted'
    assert result.status == 'completed'
    assert CreateManualExecution(pg_uow_factory(), clock=lambda: NOW).execute(config.id, 'same').id == result.id


@pytest.mark.parametrize('stale', [False, True])
def test_two_requests_owner_lock_and_active_uniqueness(pg_uow_factory, stale):
    config = owner(pg_uow_factory)
    old = active(pg_uow_factory, config) if stale else None
    locked, release = Event(), Event()
    first = pg_uow_factory()
    original = first.configuration_repository.lock_active
    def lock(identifier):
        value = original(identifier)
        locked.set()
        assert release.wait(10)
        return value
    first.configuration_repository.lock_active = lock
    with ThreadPoolExecutor(max_workers=2) as pool:
        winner = pool.submit(CreateManualExecution(first, clock=lambda: NOW).execute, config.id)
        assert locked.wait(10)
        try:
            with pytest.raises(ConflictError):
                CreateManualExecution(pg_uow_factory(), clock=lambda: NOW).execute(config.id)
        finally:
            release.set()
        completed = winner.result(10)
    check = pg_uow_factory()
    items, total = check.execution_repository.page(page=1, page_size=100, configuration_id=config.id)
    assert total == (2 if stale else 1) and completed.status == 'completed'
    assert not any(e.active for e in items)
    if old:
        assert check.execution_repository.get(old.id).error_code == 'execution_interrupted'


def test_only_active_guard_winner_enters_mining_pipeline(pg_uow_factory):
    config = owner(pg_uow_factory)
    fingerprint = normalized_url_fingerprint(config.gitlab_url)
    cipher = FakeCipher()
    credential_uow = pg_uow_factory()
    credential_uow.credential_repository.replace(config.id, cipher.encrypt("runtime-token"), None, NOW)
    credential_uow.credential_repository.update_validation(config.id, 1, fingerprint, "success", NOW)
    credential_uow.commit()
    locked, release = Event(), Event()
    first = pg_uow_factory()
    original = first.configuration_repository.lock_active
    def lock(identifier):
        value = original(identifier)
        locked.set()
        assert release.wait(10)
        return value
    first.configuration_repository.lock_active = lock
    entered = []
    class EmptyProvider:
        pass
    class ObservedPipeline:
        def __init__(self, uow):
            self.uow = uow
            self.provider = EmptyProvider()
            self.cipher = cipher
            self.pipeline = ProcessMiningExecution(uow, self.provider, self.cipher, concurrency=8, clock=lambda: NOW)
        def execute(self, identifier):
            current = self.uow.execution_repository.get(identifier)
            entered.append((identifier, current.status))
            return self.pipeline.execute(identifier)
    with ThreadPoolExecutor(max_workers=2) as pool:
        winner = pool.submit(CreateManualExecution(first, clock=lambda: NOW, mining_pipeline=ObservedPipeline(first)).execute, config.id)
        assert locked.wait(10)
        try:
            with pytest.raises(ConflictError):
                losing_uow = pg_uow_factory()
                CreateManualExecution(losing_uow, clock=lambda: NOW, mining_pipeline=ObservedPipeline(losing_uow)).execute(config.id)
        finally:
            release.set()
        result = winner.result(10)
    assert result.status == "completed"
    assert entered == [(result.id, "running")]
    records, count = pg_uow_factory().execution_repository.page(page=1, page_size=20, configuration_id=config.id)
    assert count == 1 and sum(item.active for item in records) == 0


def test_expected_status_and_partial_index(pg_uow_factory):
    config = owner(pg_uow_factory)
    first = active(pg_uow_factory, config, age=1)
    with pytest.raises(ConflictError):
        CreateManualExecution(pg_uow_factory(), clock=lambda: NOW).execute(config.id)
    insert = pg_uow_factory()
    insert.execution_repository.add(MiningExecution.create(first.snapshot, NOW))
    with pytest.raises(ConflictError):
        insert.commit()
    insert.rollback()
    lifecycle = TransitionExecution(pg_uow_factory(), clock=lambda: NOW)
    lifecycle.execute(first.id, 'pending', 'running')
    final = lifecycle.execute(first.id, 'running', 'completed')
    delayed = pg_uow_factory()
    stale_write = first.transition('failed', NOW, expected_status='pending', error_code='execution_interrupted')
    assert not delayed.execution_repository.transition(stale_write, 'pending')
    delayed.commit()
    assert pg_uow_factory().execution_repository.get(first.id) == final


def test_reconcile_creation_failure_rolls_back_both(pg_uow_factory):
    config = owner(pg_uow_factory)
    old = active(pg_uow_factory, config)
    uow = pg_uow_factory()
    def fail(item):
        raise RuntimeError('controlled persistence failure')
    uow.execution_repository.add = fail
    with pytest.raises(RuntimeError):
        CreateManualExecution(uow, clock=lambda: NOW).execute(config.id)
    assert pg_uow_factory().execution_repository.get(old.id) == old


def test_reconciliation_wins_against_delayed_finalizer(pg_uow_factory):
    config = owner(pg_uow_factory)
    old = active(pg_uow_factory, config, 'running')
    reconciler = pg_uow_factory()
    locked, release, finalizing = Event(), Event(), Event()
    original = reconciler.execution_repository.transition
    def pause_reconciliation(item, expected):
        if item.id == old.id:
            locked.set()
            assert release.wait(10)
        return original(item, expected)
    reconciler.execution_repository.transition = pause_reconciliation
    finalizer = pg_uow_factory()
    original_get = finalizer.execution_repository.get
    def get(*args, **kwargs):
        finalizing.set()
        return original_get(*args, **kwargs)
    finalizer.execution_repository.get = get
    with ThreadPoolExecutor(max_workers=2) as pool:
        replacement = pool.submit(CreateManualExecution(reconciler, clock=lambda: NOW).execute, config.id)
        assert locked.wait(10)
        late = pool.submit(TransitionExecution(finalizer, clock=lambda: NOW).execute, old.id, 'running', 'completed')
        assert finalizing.wait(10)
        release.set()
        assert replacement.result(10).status == 'completed'
        with pytest.raises(ConflictError):
            late.result(10)
    persisted = pg_uow_factory().execution_repository.get(old.id)
    assert persisted.status == 'failed' and persisted.error_code == 'execution_interrupted'
    assert persisted.snapshot == old.snapshot
