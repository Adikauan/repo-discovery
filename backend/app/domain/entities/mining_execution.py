from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.entities.execution_snapshot import ExecutionSnapshotV1, ExecutionSnapshotV2, ExecutionSnapshotV3, ExecutionSnapshotV4
from app.domain.errors import ConflictError


class TriggerType(StrEnum):
    MANUAL = 'manual'
    SCHEDULED = 'scheduled'


class ExecutionStatus(StrEnum):
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    PARTIALLY_COMPLETED = 'partially_completed'
    FAILED = 'failed'


SAFE_EXECUTION_ERRORS = {
    'execution_interrupted': 'The previous execution did not complete.',
    'orchestration_failed': 'Execution orchestration could not be completed.',
    'gitlab_credential_missing': 'A usable GitLab credential is unavailable.',
    'gitlab_instance_mismatch': 'The configured GitLab instance differs from the execution snapshot.',
    'scope_resolution_failed': 'The selected execution scope could not be resolved.',
    'scope_resolution_incomplete': 'Some selected scope entries could not be resolved.',
}


def utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('An aware reference instant is required.')
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class MiningExecution:
    id: UUID
    monitoring_configuration_id: UUID
    trigger_type: TriggerType
    status: ExecutionStatus
    created_at: datetime
    snapshot: ExecutionSnapshotV1 | ExecutionSnapshotV2 | ExecutionSnapshotV3 | ExecutionSnapshotV4
    scheduled_occurrence_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    repository_count: int = 0
    successful_repository_count: int = 0
    failed_repository_count: int = 0
    finding_count: int = 0
    scope_resolution_failure_count: int = 0
    repository_mining_completed: bool = False
    error_code: str | None = None
    error_summary: str | None = None

    def __post_init__(self):
        object.__setattr__(self, 'trigger_type', TriggerType(self.trigger_type))
        object.__setattr__(self, 'status', ExecutionStatus(self.status))
        for field in ('created_at', 'started_at', 'completed_at', 'scheduled_occurrence_at'):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, utc(value))
        if self.monitoring_configuration_id != self.snapshot.configuration_id or self.trigger_type != self.snapshot.trigger_type:
            raise ValueError('Execution snapshot ownership must match.')
        context = self.snapshot.schedule_context
        if self.trigger_type == TriggerType.SCHEDULED:
            if context is None or self.scheduled_occurrence_at is None or context.scheduled_occurrence != self.scheduled_occurrence_at:
                raise ValueError('Scheduled execution occurrence must match its immutable snapshot context.')
        elif context is not None or self.scheduled_occurrence_at is not None:
            raise ValueError('Manual execution cannot contain scheduled occurrence context.')
        if type(self.repository_mining_completed) is not bool:
            raise ValueError('Repository mining completion marker must be boolean.')
        if any(type(getattr(self, key)) is not int or getattr(self, key) < 0 for key in (
            'repository_count', 'successful_repository_count', 'failed_repository_count', 'finding_count', 'scope_resolution_failure_count')):
            raise ValueError('Execution counters must be nonnegative integers.')
        if self.started_at and self.started_at < self.created_at:
            raise ValueError('Invalid lifecycle timestamp order.')
        if self.completed_at and self.completed_at < (self.started_at or self.created_at):
            raise ValueError('Invalid lifecycle timestamp order.')
        if self.status == 'pending' and (self.started_at or self.completed_at):
            raise ValueError('Pending timestamps are invalid.')
        if self.status == 'running' and (self.started_at is None or self.completed_at is not None):
            raise ValueError('Running timestamps are invalid.')
        if not self.active and self.completed_at is None:
            raise ValueError('Final executions require completion time.')
        if self.status in ('completed', 'partially_completed') and self.started_at is None:
            raise ValueError('Completed executions require start time.')
        if self.error_code is not None:
            allowed_status = self.status == 'failed' or (self.status == 'partially_completed' and self.error_code == 'scope_resolution_incomplete')
            if not allowed_status or self.error_code not in SAFE_EXECUTION_ERRORS or self.error_summary != SAFE_EXECUTION_ERRORS[self.error_code]:
                raise ValueError('Only controlled execution error metadata is accepted.')
        elif self.error_summary is not None:
            raise ValueError('An error summary requires a safe code.')

    @classmethod
    def create(cls, snapshot: ExecutionSnapshotV1 | ExecutionSnapshotV2 | ExecutionSnapshotV3 | ExecutionSnapshotV4, now: datetime):
        return cls(uuid4(), snapshot.configuration_id, TriggerType(snapshot.trigger_type),
            ExecutionStatus.PENDING, utc(now), snapshot,
            scheduled_occurrence_at=snapshot.schedule_context.scheduled_occurrence if snapshot.schedule_context else None)

    @property
    def active(self):
        return self.status in (ExecutionStatus.PENDING, ExecutionStatus.RUNNING)

    @property
    def duration_seconds(self):
        return (self.completed_at - self.started_at).total_seconds() if self.completed_at and self.started_at else None

    def is_stale(self, now: datetime, threshold: float):
        return self.active and (utc(now) - (self.started_at or self.created_at)).total_seconds() > threshold

    def transition(self, target: ExecutionStatus | str, now: datetime, *, expected_status: ExecutionStatus | str,
                   error_code: str | None = None, repository_mining_completed: bool | None = None):
        allowed = {'pending': {'running', 'failed'}, 'running': {'completed', 'partially_completed', 'failed'}}
        if self.status != expected_status or target not in allowed.get(self.status, set()):
            raise ConflictError('The execution state changed or the transition is not allowed.')
        now = utc(now)
        values = dict(status=ExecutionStatus(target))
        if target == 'running':
            values['started_at'] = now
        else:
            values['completed_at'] = now
        if target in ('failed', 'partially_completed') and error_code is not None:
            if error_code not in SAFE_EXECUTION_ERRORS:
                raise ValueError('A controlled execution error code is required.')
            values.update(error_code=error_code, error_summary=SAFE_EXECUTION_ERRORS[error_code])
        elif error_code is not None:
            raise ValueError('Only failed executions accept error metadata.')
        if repository_mining_completed is not None:
            values['repository_mining_completed'] = repository_mining_completed
        return replace(self, **values)
