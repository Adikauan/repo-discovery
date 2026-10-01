from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import UTC, datetime

from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
from app.application.use_cases.process_repository import ProcessRepository
from app.application.use_cases.transition_execution import TransitionExecution
from app.domain.entities.mining_execution import SAFE_EXECUTION_ERRORS
from app.domain.entities.repository_execution import RepositoryExecution
from app.domain.value_objects.mining_failure import MiningFailure
from app.domain.errors import CredentialServiceUnavailable
from app.domain.entities.execution_snapshot import ExecutionSnapshotV4
import logging

logger = logging.getLogger(__name__)


class ProcessMiningExecution:
    """Runs snapshot-bound repository jobs; repository workers are bounded and failures isolated."""
    def __init__(self, uow, provider, cipher, *, concurrency=4, max_file_bytes=1_048_576,
                 max_extensions=100, max_commits=1000, clock=None, worker_uow_factory=None):
        self.uow, self.provider, self.cipher = uow, provider, cipher
        self.concurrency, self.max_file_bytes, self.max_extensions = concurrency, max_file_bytes, max_extensions
        self.max_commits = max_commits
        self.clock = clock or (lambda: datetime.now(UTC))
        self.worker_uow_factory = worker_uow_factory

    def _preflight(self, execution):
        snapshot = execution.snapshot
        credential = self.uow.credential_repository.get(execution.monitoring_configuration_id)
        configuration = self.uow.configuration_repository.get(execution.monitoring_configuration_id)
        fingerprint = normalized_url_fingerprint(snapshot.gitlab_url)
        if configuration is None or normalized_url_fingerprint(configuration.gitlab_url) != fingerprint:
            raise MiningFailure("gitlab_instance_mismatch")
        if any(item.instance_fingerprint != fingerprint for item in (*snapshot.groups, *snapshot.repositories)) \
                or any(item.instance_fingerprint != fingerprint for item in getattr(snapshot, "target_branch_rules", ())) \
                or any(item.instance_fingerprint != fingerprint for item in getattr(snapshot, "mining_targets", ())):
            raise MiningFailure("gitlab_instance_mismatch")
        if credential is None or credential.last_validation_result != "success" or credential.validated_url_fingerprint != fingerprint:
            raise MiningFailure("gitlab_credential_missing")
        if self.cipher is None:
            raise MiningFailure("gitlab_credential_missing")
        try:
            token = self.cipher.decrypt(credential.encrypted_token)
        except CredentialServiceUnavailable as error:
            raise MiningFailure("gitlab_credential_missing") from error
        if not token:
            raise MiningFailure("gitlab_credential_missing")
        return token

    def execute(self, execution_id):
        execution = self.uow.execution_repository.get(execution_id)
        if execution is None or execution.status != "running":
            return execution
        try:
            token = self._preflight(execution)
            if not isinstance(execution.snapshot, ExecutionSnapshotV4):
                logger.warning("Pending execution snapshot predates Policy mining targets; refusing to infer a branch",
                    extra={"execution_id": str(execution_id), "snapshot_version": execution.snapshot.schema_version})
                raise MiningFailure("orchestration_failed")
            self.uow.commit()
        except MiningFailure as error:
            code = error.code if error.code in SAFE_EXECUTION_ERRORS else "orchestration_failed"
            TransitionExecution(self.uow, self.clock).execute(execution_id, "running", "failed", error_code=code)
            return self.uow.execution_repository.get(execution_id)

        rows = []
        row_errors = {}
        for item in execution.snapshot.mining_targets:
            rows.append(RepositoryExecution.create(execution_id, item.gitlab_project_id, item.name,
                item.full_path, item.branch))
        for row in rows:
            self.uow.repository_execution_repository.add(row)
        self.uow.commit()

        def process(row):
            target_uow = self.worker_uow_factory() if self.worker_uow_factory else self.uow
            try:
                return ProcessRepository(target_uow, self.provider, clock=self.clock,
                    max_file_bytes=self.max_file_bytes, max_extensions=self.max_extensions,
                    max_commits=self.max_commits).execute(row, execution.snapshot, token,
                                                         preflight_error_code=row_errors.get(row.id))
            finally:
                if target_uow is not self.uow:
                    target_uow.session.close()

        # With a SQLAlchemy session factory every worker owns its own short-lived UOW.
        if self.worker_uow_factory and len(rows) > 1:
            with ThreadPoolExecutor(max_workers=self.concurrency, thread_name_prefix="repository-mining") as pool:
                iterator = iter(rows)
                pending = {pool.submit(process, row) for row in [next(iterator) for _ in range(min(self.concurrency, len(rows)))]}
                while pending:
                    finished, pending = wait(pending, return_when=FIRST_COMPLETED)
                    for future in finished:
                        future.result()
                        try:
                            pending.add(pool.submit(process, next(iterator)))
                        except StopIteration:
                            pass
        else:
            for row in rows:
                process(row)

        persisted, total = self.uow.repository_execution_repository.list_for_execution(execution_id, page=1, page_size=max(1, len(rows)))
        successes = sum(item.status == "completed" for item in persisted)
        failures = sum(item.status == "failed" for item in persisted)
        finding_count = sum(item.finding_count for item in persisted)
        scope_failures = 0
        if successes and (failures or scope_failures):
            target, code = "partially_completed", "scope_resolution_incomplete" if scope_failures else None
        elif successes or (total == 0 and not scope_failures):
            target, code = "completed", None
        else:
            target, code = "failed", "scope_resolution_failed" if scope_failures else None
        self.uow.execution_repository.update_counters(execution_id,
            repository_count=total, successful_count=successes, failed_count=failures,
            finding_count=finding_count, scope_failures=scope_failures)
        self.uow.commit()
        result = TransitionExecution(self.uow, self.clock).execute(execution_id, "running", target,
            error_code=code, repository_mining_completed=True if target == "completed" else None)
        return result
