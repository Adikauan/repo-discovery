from datetime import UTC, datetime, timedelta
from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from app.domain.entities.execution_snapshot import ExecutionSnapshotV1
from app.domain.entities.mining_execution import MiningExecution, ExecutionStatus, TriggerType
from app.domain.errors import ConflictError

NOW = datetime(2026, 9, 29, 12, tzinfo=UTC)


def pending():
    snapshot = ExecutionSnapshotV1(configuration_id=uuid4(), configuration_name='Original',
        configuration_enabled=False, gitlab_url='https://gitlab.example.com', configuration_revision=1,
        scope_version=0, trigger_type='manual')
    return MiningExecution.create(snapshot, NOW)


def test_creation_and_timestamp_lifecycle():
    item = pending()
    assert item.status == ExecutionStatus.PENDING and item.trigger_type == TriggerType.MANUAL
    assert item.started_at is None and item.completed_at is None
    running = item.transition('running', NOW + timedelta(seconds=1), expected_status='pending')
    final = running.transition('completed', NOW + timedelta(seconds=2), expected_status='running')
    assert final.created_at == NOW and final.started_at == running.started_at
    assert final.duration_seconds == 1 and not final.active
    assert (final.repository_count, final.successful_repository_count, final.failed_repository_count, final.finding_count) == (0, 0, 0, 0)
    with pytest.raises(FrozenInstanceError):
        final.status = 'running'


@pytest.mark.parametrize('status', ['completed', 'partially_completed', 'failed'])
def test_final_status_is_immutable(status):
    item = pending().transition('running', NOW, expected_status='pending')
    item = item.transition(status, NOW, expected_status='running', error_code='orchestration_failed' if status == 'failed' else None)
    for target in ExecutionStatus:
        with pytest.raises(ConflictError):
            item.transition(target, NOW, expected_status=status)


def test_invalid_guard_transition_time_and_failure():
    item = pending()
    for target, expected, time in [('running', 'running', NOW), ('completed', 'pending', NOW), ('running', 'pending', NOW - timedelta(seconds=1))]:
        with pytest.raises((ConflictError, ValueError)):
            item.transition(target, time, expected_status=expected)
    failed = item.transition('failed', NOW, expected_status='pending', error_code='execution_interrupted')
    assert failed.started_at is None and failed.completed_at == NOW
    assert failed.error_summary == 'The previous execution did not complete.'
    with pytest.raises(ValueError):
        item.transition('failed', NOW, expected_status='pending', error_code='secret exception')


def test_scheduled_execution_requires_matching_immutable_occurrence_context():
    from app.domain.entities.execution_snapshot import ScheduleTriggerContext
    configuration_id = uuid4()
    occurrence = NOW + timedelta(days=1)
    snapshot = ExecutionSnapshotV1(configuration_id=configuration_id, configuration_name='Schedule owner',
        configuration_enabled=True, gitlab_url='https://gitlab.example.com', configuration_revision=1,
        scope_version=0, trigger_type='scheduled',
        schedule_context=ScheduleTriggerContext(scheduled_occurrence=occurrence, schedule_version=7))
    execution = MiningExecution.create(snapshot, NOW)
    assert execution.trigger_type == TriggerType.SCHEDULED
    assert execution.scheduled_occurrence_at == occurrence
    assert execution.snapshot.schedule_context.schedule_version == 7
    with pytest.raises(ValueError):
        MiningExecution(uuid4(), configuration_id, 'scheduled', 'pending', NOW, snapshot)
    with pytest.raises(ValueError):
        ExecutionSnapshotV1.capture(
            type('Config', (), {'id': configuration_id, 'name': 'name', 'enabled': True,
                'gitlab_url': 'https://gitlab.example.com', 'revision': 1})(),
            type('Scope', (), {'version': 0, 'groups': (), 'repositories': ()})(),
            trigger_type='scheduled')


def test_stale_boundary_and_clock():
    item = pending()
    assert not item.is_stale(NOW + timedelta(seconds=300), 300)
    assert item.is_stale(NOW + timedelta(seconds=301), 300)
    running = item.transition('running', NOW + timedelta(seconds=10), expected_status='pending')
    assert not running.is_stale(NOW + timedelta(seconds=310), 300)
    assert running.is_stale(NOW + timedelta(seconds=311), 300)
    with pytest.raises(ValueError):
        MiningExecution.create(item.snapshot, datetime(2026, 1, 1))
