import hashlib
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.application.ports.create_request_store import CreateRequestReceipt
from app.application.use_cases.transition_execution import TransitionExecution, persist_transition
from app.domain.entities.execution_snapshot import ExecutionSnapshotV1, ExecutionSnapshotV2, ExecutionSnapshotV3, ExecutionSnapshotV4
from app.domain.entities.mining_execution import MiningExecution, TriggerType
from app.domain.errors import (ConflictError, DuplicateIdempotencyKey, DuplicateScheduledOccurrence,
                               IdempotencyConflict, NotFoundError)
from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
from app.application.use_cases.resolve_mining_targets import ResolveMiningTargets
from app.domain.errors import FieldValidationError
from app.domain.errors import CredentialServiceUnavailable


@dataclass(frozen=True, slots=True)
class ExecutionCreationResult:
    outcome: str
    execution: MiningExecution | None = None


class CreateMiningExecution:
    """One guarded creation/lifecycle boundary shared by manual and scheduled triggers."""

    def __init__(self, uow, clock=None, threshold=300, orchestration=None, before_start=None, mining_pipeline=None):
        if not math.isfinite(threshold) or threshold <= 0:
            raise ValueError('Execution staleness threshold must be finite and greater than zero.')
        self.uow = uow
        self.clock = clock or (lambda: datetime.now(UTC))
        self.threshold = threshold
        self.orchestration = orchestration or (lambda: None)
        self.before_start = before_start or (lambda: None)
        self.mining_pipeline = mining_pipeline

    def _reconcile(self, item, now):
        if not item.active:
            return item
        if not item.is_stale(now, self.threshold):
            raise ConflictError('An execution is already active for this configuration.')
        return persist_transition(self.uow, item, 'failed', now, error_code='execution_interrupted')

    def _replay(self, receipt, fingerprint, now):
        if receipt.request_fingerprint != fingerprint:
            raise IdempotencyConflict('This idempotency key was already used for a different request.')
        item = self.uow.execution_repository.get(UUID(receipt.response_snapshot['execution_id']), for_update=True)
        if item is None:
            raise RuntimeError('Execution receipt is unavailable.')
        item = self._reconcile(item, now)
        self.uow.commit()
        return ExecutionCreationResult('replayed', item)

    def execute(self, configuration_id, *, trigger_type='manual', idempotency_key=None,
                scheduled_occurrence=None, expected_schedule_version=None):
        trigger = TriggerType(trigger_type)
        if trigger == TriggerType.MANUAL and (scheduled_occurrence is not None or expected_schedule_version is not None):
            raise ValueError('Manual executions cannot include scheduled occurrence context.')
        if trigger == TriggerType.SCHEDULED:
            if idempotency_key is not None:
                raise ValueError('Scheduled executions use occurrence idempotency, not request idempotency keys.')
            if scheduled_occurrence is None or expected_schedule_version is None:
                raise ValueError('Scheduled executions require an occurrence and expected schedule version.')
            if scheduled_occurrence.tzinfo is None or scheduled_occurrence.utcoffset() is None:
                raise ValueError('Scheduled occurrence must be timezone-aware.')
        request_fingerprint = hashlib.sha256(f'manual-execution:{configuration_id}'.encode()).hexdigest()
        try:
            self.uow.begin_execution_creation()
            configuration = self.uow.configuration_repository.lock_active(configuration_id)
            if configuration is None:
                raise NotFoundError('Monitoring Configuration not found.')
            now = self.clock()
            schedule = None
            if trigger == TriggerType.SCHEDULED:
                if not configuration.enabled:
                    self.uow.rollback()
                    return ExecutionCreationResult('ineligible')
                schedule = self.uow.schedule_repository.get(configuration_id, for_update=True)
                occurrence_utc = scheduled_occurrence.astimezone(UTC)
                if (not schedule.configured or not schedule.enabled or schedule.version != expected_schedule_version
                        or schedule.updated_at is None or occurrence_utc <= schedule.updated_at.astimezone(UTC)
                        or occurrence_utc > now.astimezone(UTC)):
                    self.uow.rollback()
                    return ExecutionCreationResult('ineligible')
            if idempotency_key:
                receipt = self.uow.receipt_repository.get(idempotency_key)
                if receipt:
                    return self._replay(receipt, request_fingerprint, now)
            active = self.uow.execution_repository.active_for(configuration_id)
            if active is not None:
                try:
                    self._reconcile(active, now)
                except ConflictError:
                    if trigger == TriggerType.SCHEDULED:
                        self.uow.rollback()
                        return ExecutionCreationResult('conflict')
                    raise
            scope = self.uow.mining_scope_repository.get(configuration_id)
            author_policies = self.uow.author_policy_repository.list_for_configuration(configuration_id) \
                if hasattr(self.uow, "author_policy_repository") else []
            instance_fingerprint = normalized_url_fingerprint(configuration.gitlab_url)
            provider = getattr(self.mining_pipeline, "provider", None)
            cipher = getattr(self.mining_pipeline, "cipher", None)
            if provider is not None and cipher is not None:
                credential = self.uow.credential_repository.get(configuration_id)
                if (credential is None or credential.last_validation_result != "success"
                        or credential.validated_url_fingerprint != instance_fingerprint):
                    raise FieldValidationError("gitlabConnection", "credential_required",
                        "A valid GitLab credential is required before execution.")
                try:
                    token = cipher.decrypt(credential.encrypted_token)
                except CredentialServiceUnavailable as error:
                    raise FieldValidationError("gitlabConnection", "credential_unavailable",
                        "The GitLab credential is unavailable. Revalidate the connection and try again.") from error
                mining_targets = ResolveMiningTargets(provider).execute(configuration, scope, token, author_policies)
                snapshot = ExecutionSnapshotV4.capture(configuration, scope, mining_targets=mining_targets,
                    trigger_type=trigger.value,
                    scheduled_occurrence=scheduled_occurrence if trigger == TriggerType.SCHEDULED else None,
                    schedule_version=expected_schedule_version if trigger == TriggerType.SCHEDULED else None)
            else:
                # Compatibility for non-production callers that create records without the mining pipeline.
                legacy_policies = [policy for policy in author_policies
                    if policy.instance_fingerprint == instance_fingerprint and policy.scope_type == "repository_branch"]
                snapshot = ExecutionSnapshotV2.capture(configuration, scope, policies=legacy_policies,
                    trigger_type=trigger.value,
                    scheduled_occurrence=scheduled_occurrence if trigger == TriggerType.SCHEDULED else None,
                    schedule_version=expected_schedule_version if trigger == TriggerType.SCHEDULED else None)
            item = MiningExecution.create(snapshot, now)
            self.uow.execution_repository.add(item)
            if idempotency_key:
                self.uow.receipt_repository.add(CreateRequestReceipt(idempotency_key, request_fingerprint, {'execution_id': str(item.id)}))
            self.uow.commit()
        except DuplicateScheduledOccurrence:
            self.uow.rollback()
            return ExecutionCreationResult('duplicate')
        except DuplicateIdempotencyKey:
            self.uow.rollback()
            try:
                receipt = self.uow.receipt_repository.get(idempotency_key)
                if receipt is None:
                    raise ConflictError('The execution request could not be replayed. Try again.')
                return self._replay(receipt, request_fingerprint, self.clock())
            except Exception:
                self.uow.rollback()
                raise
        except Exception:
            self.uow.rollback()
            raise

        lifecycle = TransitionExecution(self.uow, self.clock)
        try:
            self.before_start()
        except Exception:
            failed = lifecycle.execute(item.id, 'pending', 'failed', error_code='orchestration_failed')
            return ExecutionCreationResult('started', failed)
        lifecycle.execute(item.id, 'pending', 'running')
        if self.mining_pipeline is not None:
            try:
                self.mining_pipeline.execute(item.id)
            except Exception:
                current = self.uow.execution_repository.get(item.id)
                if current is not None and current.status == 'running':
                    lifecycle.execute(item.id, 'running', 'failed', error_code='orchestration_failed')
            return ExecutionCreationResult('started', self.uow.execution_repository.get(item.id))
        try:
            self.orchestration()
        except Exception:
            failed = lifecycle.execute(item.id, 'running', 'failed', error_code='orchestration_failed')
            return ExecutionCreationResult('started', failed)
        completed = lifecycle.execute(item.id, 'running', 'completed')
        return ExecutionCreationResult('started', completed)
