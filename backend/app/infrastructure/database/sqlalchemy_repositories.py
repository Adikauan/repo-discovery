import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select, update, func, distinct, cast, Date, literal_column
from sqlalchemy.exc import IntegrityError, DBAPIError
from contextlib import contextmanager
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.application.ports.create_request_store import CreateRequestReceipt
from app.domain.entities.mining_scope import MiningScope, SelectedGitLabGroup, SelectedGitLabRepository
from app.domain.errors import DuplicateIdempotencyKey, DuplicateScheduledOccurrence, ConflictError
from app.domain.entities.mining_execution import MiningExecution
from app.domain.entities.repository_execution import RepositoryExecution
from app.domain.entities.execution_snapshot import load_execution_snapshot
from app.infrastructure.database.models import MiningExecutionRecord, RepositoryExecutionRecord
from app.infrastructure.database.models import (FindingRecord, RepositoryCheckpointRecord,
    AuthorPolicyRecord, AuthorPolicyAuthorRecord)
from app.domain.entities.finding import Finding
from app.domain.entities.repository_checkpoint import RepositoryCheckpoint
from app.domain.author_policy import AuthorPolicy
from app.infrastructure.database.session import begin_execution_snapshot


@contextmanager
def execution_conflicts():
    try:
        yield
    except DBAPIError as error:
        code = getattr(error.orig, 'sqlstate', None)
        constraint = getattr(getattr(error.orig, 'diag', None), 'constraint_name', None)
        if code in ('55P03', '40001', '40P01') or constraint == 'uq_execution_active_configuration':
            raise ConflictError('Another execution operation is in progress. Reload before trying again.') from error
        raise
from app.domain.ports.gitlab_credential_repository import CredentialSnapshot
from app.application.ports.mining_scope_repository import MiningScopeRepository
from app.application.ports.monitoring_schedule_repository import MonitoringScheduleRepository
from app.domain.entities.monitoring_schedule import MonitoringSchedule, RecurrenceType
from app.domain.monitoring_configuration import MonitoringConfiguration
from app.infrastructure.database.models import (CreateRequestReceiptRecord, GitLabCredentialRecord,
                                                MonitoringConfigurationRecord, MiningScopeStateRecord,
                                                SelectedGitLabGroupRecord, SelectedGitLabRepositoryRecord,
                                                MonitoringScheduleRecord)


def _entity(row: MonitoringConfigurationRecord) -> MonitoringConfiguration:
    return MonitoringConfiguration(row.id, row.name, row.description, row.gitlab_url, row.enabled,
                                   row.created_at, row.updated_at, row.revision, row.retired_at,
                                   tuple(getattr(row, "allowed_author_emails", None) or ()),
                                   getattr(row, "author_policy_mode", "legacy"))


class SqlAlchemyConfigurationRepository:
    def __init__(self, session: Session): self.session = session

    def get(self, identifier: UUID):
        row = self.session.get(MonitoringConfigurationRecord, identifier)
        return _entity(row) if row else None

    def lock_active(self, identifier: UUID):
        with execution_conflicts():
            row = self.session.scalar(select(MonitoringConfigurationRecord).where(
                MonitoringConfigurationRecord.id == identifier,
                MonitoringConfigurationRecord.retired_at.is_(None)).with_for_update(nowait=True).execution_options(populate_existing=True))
            return _entity(row) if row else None

    def add(self, item: MonitoringConfiguration) -> None:
        self.session.add(MonitoringConfigurationRecord(id=item.id, name=item.name, description=item.description,
            gitlab_url=item.gitlab_url, enabled=item.enabled, created_at=item.created_at,
            updated_at=item.updated_at, revision=item.revision, retired_at=item.retired_at,
            allowed_author_emails=list(item.allowed_author_emails), author_policy_mode=item.author_policy_mode))

    def get_active(self, identifier: UUID):
        row = self.session.scalar(select(MonitoringConfigurationRecord).where(
            MonitoringConfigurationRecord.id == identifier, MonitoringConfigurationRecord.retired_at.is_(None)))
        return _entity(row) if row else None

    def list_active(self, search: str | None = None):
        query = select(MonitoringConfigurationRecord).where(MonitoringConfigurationRecord.retired_at.is_(None))
        if search:
            # Use ! as an explicit SQL escape character and escape it as well as LIKE metacharacters.
            escaped = search.replace("!", "!!").replace("%", "!%").replace("_", "!_")
            query = query.where(MonitoringConfigurationRecord.name.ilike(f"%{escaped}%", escape="!"))
        query = query.order_by(MonitoringConfigurationRecord.created_at.desc())
        return [_entity(row) for row in self.session.scalars(query).all()]

    def list_active_with_schedules(self, search: str | None = None):
        """Return configurations with their existing schedule row in one bounded query."""
        query = select(MonitoringConfigurationRecord, MonitoringScheduleRecord).outerjoin(
            MonitoringScheduleRecord,
            MonitoringScheduleRecord.monitoring_configuration_id == MonitoringConfigurationRecord.id,
        ).where(MonitoringConfigurationRecord.retired_at.is_(None))
        if search:
            escaped = search.replace("!", "!!").replace("%", "!%").replace("_", "!_")
            query = query.where(MonitoringConfigurationRecord.name.ilike(f"%{escaped}%", escape="!"))
        query = query.order_by(MonitoringConfigurationRecord.created_at.desc())
        return [( _entity(configuration), schedule if schedule and schedule.configured else None)
                for configuration, schedule in self.session.execute(query).all()]

    def update(self, item: MonitoringConfiguration, expected_revision: int) -> bool:
        result = self.session.execute(update(MonitoringConfigurationRecord).where(
            MonitoringConfigurationRecord.id == item.id, MonitoringConfigurationRecord.retired_at.is_(None),
            MonitoringConfigurationRecord.revision == expected_revision).values(name=item.name,
            description=item.description, gitlab_url=item.gitlab_url, enabled=item.enabled,
            updated_at=item.updated_at, revision=item.revision,
            allowed_author_emails=list(item.allowed_author_emails), author_policy_mode=item.author_policy_mode))
        return result.rowcount == 1

    def retire(self, item: MonitoringConfiguration) -> bool:
        result = self.session.execute(update(MonitoringConfigurationRecord).where(
            MonitoringConfigurationRecord.id == item.id, MonitoringConfigurationRecord.retired_at.is_(None)).values(
            retired_at=item.retired_at, updated_at=item.updated_at))
        return result.rowcount == 1


class SqlAlchemyAuthorPolicyRepository:
    def __init__(self, session: Session): self.session = session

    def _entity(self, row: AuthorPolicyRecord) -> AuthorPolicy:
        authors = self.session.scalars(select(AuthorPolicyAuthorRecord).where(
            AuthorPolicyAuthorRecord.policy_id == row.id).order_by(AuthorPolicyAuthorRecord.normalized_email)).all()
        return AuthorPolicy.create(identifier=row.id, configuration_id=row.monitoring_configuration_id,
            instance_fingerprint=row.instance_fingerprint, full_path=row.full_path,
            gitlab_group_id=row.gitlab_group_id, gitlab_project_id=row.gitlab_project_id,
            branch=row.branch, allowed_author_emails=[item.normalized_email for item in authors])

    def list_for_configuration(self, configuration_id: UUID) -> list[AuthorPolicy]:
        rows = self.session.scalars(select(AuthorPolicyRecord).where(
            AuthorPolicyRecord.monitoring_configuration_id == configuration_id).order_by(
            AuthorPolicyRecord.scope_type, AuthorPolicyRecord.full_path, AuthorPolicyRecord.branch)).all()
        return [self._entity(row) for row in rows]

    def get(self, policy_id: UUID) -> AuthorPolicy | None:
        row = self.session.get(AuthorPolicyRecord, policy_id)
        return self._entity(row) if row else None

    def upsert(self, policy: AuthorPolicy) -> None:
        identity = [AuthorPolicyRecord.monitoring_configuration_id == policy.monitoring_configuration_id,
                    AuthorPolicyRecord.instance_fingerprint == policy.instance_fingerprint,
                    AuthorPolicyRecord.scope_type == policy.scope_type]
        identity.append(AuthorPolicyRecord.gitlab_group_id == policy.gitlab_group_id if policy.scope_type == "group"
                        else AuthorPolicyRecord.gitlab_project_id == policy.gitlab_project_id)
        if policy.scope_type == "repository_branch": identity.append(AuthorPolicyRecord.branch == policy.branch)
        existing = self.session.scalar(select(AuthorPolicyRecord).where(*identity).with_for_update())
        if existing:
            existing.full_path = policy.full_path
            self.session.execute(delete(AuthorPolicyAuthorRecord).where(AuthorPolicyAuthorRecord.policy_id == existing.id))
            policy_id = existing.id
        else:
            policy_id = policy.id
            self.session.add(AuthorPolicyRecord(id=policy_id, monitoring_configuration_id=policy.monitoring_configuration_id,
                scope_type=policy.scope_type, instance_fingerprint=policy.instance_fingerprint, full_path=policy.full_path,
                gitlab_group_id=policy.gitlab_group_id, gitlab_project_id=policy.gitlab_project_id, branch=policy.branch))
            self.session.flush()
        self.session.add_all([AuthorPolicyAuthorRecord(policy_id=policy_id, normalized_email=email,
            display_email=email) for email in policy.allowed_author_emails])

    def delete(self, policy_id: UUID, configuration_id: UUID) -> bool:
        result = self.session.execute(delete(AuthorPolicyRecord).where(
            AuthorPolicyRecord.id == policy_id,
            AuthorPolicyRecord.monitoring_configuration_id == configuration_id))
        return result.rowcount == 1


class SqlAlchemyReceiptRepository:
    def __init__(self, session: Session): self.session = session

    def get(self, key: str):
        row = self.session.get(CreateRequestReceiptRecord, key)
        return CreateRequestReceipt(row.request_key, row.request_fingerprint, json.loads(row.response_snapshot)) if row else None

    def add(self, receipt: CreateRequestReceipt):
        self.session.add(CreateRequestReceiptRecord(request_key=receipt.request_key,
            request_fingerprint=receipt.request_fingerprint, response_snapshot=json.dumps(receipt.response_snapshot)))


class SqlAlchemyGitLabCredentialRepository:
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _snapshot(row: GitLabCredentialRecord) -> CredentialSnapshot:
        return CredentialSnapshot(
            configuration_id=row.monitoring_configuration_id,
            encrypted_token=row.encrypted_token,
            revision=row.credential_revision,
            last_validation_result=row.last_validation_result,
            last_validated_at=row.last_validated_at,
            last_successful_validation_at=row.last_successful_validation_at,
            validated_url_fingerprint=row.validated_url_fingerprint,
        )

    def get(self, configuration_id: UUID):
        row = self.session.get(GitLabCredentialRecord, configuration_id)
        return self._snapshot(row) if row else None

    def replace(self, configuration_id: UUID, encrypted_token: bytes,
                expected_revision: int | None, now: datetime) -> bool:
        if expected_revision is None:
            result = self.session.execute(pg_insert(GitLabCredentialRecord).values(
                monitoring_configuration_id=configuration_id, encrypted_token=encrypted_token,
                credential_revision=1, created_at=now, updated_at=now,
            ).on_conflict_do_nothing(index_elements=["monitoring_configuration_id"]).returning(
                GitLabCredentialRecord.monitoring_configuration_id))
            return result.scalar_one_or_none() is not None
        result = self.session.execute(update(GitLabCredentialRecord).where(
            GitLabCredentialRecord.monitoring_configuration_id == configuration_id,
            GitLabCredentialRecord.credential_revision == expected_revision,
        ).values(
            encrypted_token=encrypted_token, credential_revision=expected_revision + 1,
            updated_at=now, last_validation_result=None, last_validated_at=None,
            last_successful_validation_at=None, validated_url_fingerprint=None,
        ))
        return result.rowcount == 1

    def remove(self, configuration_id: UUID) -> None:
        self.session.execute(delete(GitLabCredentialRecord).where(
            GitLabCredentialRecord.monitoring_configuration_id == configuration_id))

    def update_validation(self, configuration_id: UUID, expected_revision: int,
                          url_fingerprint: str, result: str, checked_at: datetime) -> bool:
        values = {
            "last_validation_result": result,
            "last_validated_at": checked_at,
            "validated_url_fingerprint": url_fingerprint,
        }
        if result == "success":
            values["last_successful_validation_at"] = checked_at
        update_result = self.session.execute(update(GitLabCredentialRecord).where(
            GitLabCredentialRecord.monitoring_configuration_id == configuration_id,
            GitLabCredentialRecord.credential_revision == expected_revision,
        ).values(**values))
        return update_result.rowcount == 1


class SqlAlchemyMiningScopeRepository(MiningScopeRepository):
    def __init__(self, session: Session):
        self.session = session

    def get(self, configuration_id: UUID) -> MiningScope:
        state = self.session.get(MiningScopeStateRecord, configuration_id)
        if state is None:
            return MiningScope(configuration_id, 0, None)
        groups = self.session.scalars(select(SelectedGitLabGroupRecord).where(
            SelectedGitLabGroupRecord.configuration_id == configuration_id
        ).order_by(SelectedGitLabGroupRecord.selection_id)).all()
        repositories = self.session.scalars(select(SelectedGitLabRepositoryRecord).where(
            SelectedGitLabRepositoryRecord.configuration_id == configuration_id
        ).order_by(SelectedGitLabRepositoryRecord.selection_id)).all()
        return MiningScope(
            configuration_id=configuration_id,
            version=state.version,
            updated_at=state.updated_at,
            groups=tuple(SelectedGitLabGroup(
                selection_id=row.selection_id,
                instance_fingerprint=row.instance_fingerprint,
                gitlab_group_id=row.gitlab_group_id,
                name=row.name,
                full_path=row.full_path,
                parent_group_id=row.parent_group_id,
                updated_at=row.updated_at,
            ) for row in groups),
            repositories=tuple(SelectedGitLabRepository(
                selection_id=row.selection_id,
                instance_fingerprint=row.instance_fingerprint,
                gitlab_project_id=row.gitlab_project_id,
                name=row.name,
                full_path=row.full_path,
                parent_group_id=row.parent_group_id,
                updated_at=row.updated_at,
            ) for row in repositories),
        )

    def replace(self, scope: MiningScope, expected_version: int) -> bool:
        """Replace a complete scope set and advance its independent version by CAS."""
        if expected_version == 0:
            result = self.session.execute(pg_insert(MiningScopeStateRecord).values(
                configuration_id=scope.configuration_id,
                version=1,
                updated_at=scope.updated_at or datetime.now(UTC),
            ).on_conflict_do_nothing(index_elements=["configuration_id"]).returning(
                MiningScopeStateRecord.configuration_id))
            if result.scalar_one_or_none() is None:
                return False
        else:
            result = self.session.execute(update(MiningScopeStateRecord).where(
                MiningScopeStateRecord.configuration_id == scope.configuration_id,
                MiningScopeStateRecord.version == expected_version,
            ).values(version=expected_version + 1, updated_at=scope.updated_at or datetime.now(UTC)))
            if result.rowcount != 1:
                return False

        self.session.execute(delete(SelectedGitLabGroupRecord).where(
            SelectedGitLabGroupRecord.configuration_id == scope.configuration_id))
        self.session.execute(delete(SelectedGitLabRepositoryRecord).where(
            SelectedGitLabRepositoryRecord.configuration_id == scope.configuration_id))
        self.session.add_all([SelectedGitLabGroupRecord(
            selection_id=item.selection_id,
            configuration_id=scope.configuration_id,
            instance_fingerprint=item.instance_fingerprint,
            gitlab_group_id=item.gitlab_group_id,
            name=item.name,
            full_path=item.full_path,
            parent_group_id=item.parent_group_id,
            updated_at=item.updated_at,
        ) for item in scope.groups])
        self.session.add_all([SelectedGitLabRepositoryRecord(
            selection_id=item.selection_id,
            configuration_id=scope.configuration_id,
            instance_fingerprint=item.instance_fingerprint,
            gitlab_project_id=item.gitlab_project_id,
            name=item.name,
            full_path=item.full_path,
            parent_group_id=item.parent_group_id,
            updated_at=item.updated_at,
        ) for item in scope.repositories])
        return True

    def refresh_metadata(self, scope: MiningScope) -> None:
        for item in scope.groups:
            self.session.execute(update(SelectedGitLabGroupRecord).where(
                SelectedGitLabGroupRecord.selection_id == item.selection_id,
                SelectedGitLabGroupRecord.configuration_id == scope.configuration_id,
            ).values(name=item.name, full_path=item.full_path, parent_group_id=item.parent_group_id,
                     updated_at=item.updated_at))
        for item in scope.repositories:
            self.session.execute(update(SelectedGitLabRepositoryRecord).where(
                SelectedGitLabRepositoryRecord.selection_id == item.selection_id,
                SelectedGitLabRepositoryRecord.configuration_id == scope.configuration_id,
            ).values(name=item.name, full_path=item.full_path, parent_group_id=item.parent_group_id,
                     updated_at=item.updated_at))


class SqlAlchemyMonitoringScheduleRepository(MonitoringScheduleRepository):
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _entity(row: MonitoringScheduleRecord | None, configuration_id: UUID) -> MonitoringSchedule:
        if row is None:
            return MonitoringSchedule.unconfigured(configuration_id)
        if not row.configured:
            return MonitoringSchedule.unconfigured(configuration_id, row.version, row.updated_at)
        return MonitoringSchedule(
            monitoring_configuration_id=configuration_id, configured=True, version=row.version,
            recurrence_type=RecurrenceType(row.recurrence_type), enabled=row.enabled,
            execution_time=row.execution_time, timezone=row.timezone, day_of_week=row.day_of_week,
            day_of_month=row.day_of_month, created_at=row.created_at, updated_at=row.updated_at,
        )

    def get(self, configuration_id: UUID, *, for_update: bool = False) -> MonitoringSchedule:
        if not for_update:
            row = self.session.get(MonitoringScheduleRecord, configuration_id)
            return self._entity(row, configuration_id)
        query = select(MonitoringScheduleRecord).where(
            MonitoringScheduleRecord.monitoring_configuration_id == configuration_id)
        query = query.with_for_update(nowait=True)
        row = self.session.scalar(query.execution_options(populate_existing=True))
        return self._entity(row, configuration_id)

    def list_eligible(self):
        query = select(MonitoringConfigurationRecord, MonitoringScheduleRecord).join(
            MonitoringScheduleRecord,
            MonitoringScheduleRecord.monitoring_configuration_id == MonitoringConfigurationRecord.id,
        ).where(
            MonitoringConfigurationRecord.enabled.is_(True),
            MonitoringConfigurationRecord.retired_at.is_(None),
            MonitoringScheduleRecord.configured.is_(True),
            MonitoringScheduleRecord.enabled.is_(True),
        ).order_by(MonitoringConfigurationRecord.id.asc())
        return [(_entity(configuration), self._entity(schedule, configuration.id))
                for configuration, schedule in self.session.execute(query).all()]

    @staticmethod
    def _values(schedule: MonitoringSchedule) -> dict:
        return {
            "configured": schedule.configured,
            "recurrence_type": schedule.recurrence_type.value if schedule.recurrence_type else None,
            "enabled": schedule.enabled,
            "execution_time": schedule.execution_time,
            "timezone": schedule.timezone,
            "day_of_week": schedule.day_of_week,
            "day_of_month": schedule.day_of_month,
            "created_at": schedule.created_at,
            "updated_at": schedule.updated_at,
        }

    def replace(self, schedule: MonitoringSchedule, expected_version: int) -> bool:
        values = self._values(schedule)
        next_version = expected_version + 1
        if expected_version == 0:
            result = self.session.execute(pg_insert(MonitoringScheduleRecord).values(
                monitoring_configuration_id=schedule.monitoring_configuration_id,
                version=next_version, **values,
            ).on_conflict_do_nothing(index_elements=["monitoring_configuration_id"]).returning(
                MonitoringScheduleRecord.monitoring_configuration_id))
            return result.scalar_one_or_none() is not None
        result = self.session.execute(update(MonitoringScheduleRecord).where(
            MonitoringScheduleRecord.monitoring_configuration_id == schedule.monitoring_configuration_id,
            MonitoringScheduleRecord.version == expected_version,
        ).values(version=next_version, **values))
        return result.rowcount == 1


class SqlAlchemyUnitOfWork:
    def __init__(self, session: Session):
        self.session = session
        self.configuration_repository = SqlAlchemyConfigurationRepository(session)
        self.receipt_repository = SqlAlchemyReceiptRepository(session)
        self.credential_repository = SqlAlchemyGitLabCredentialRepository(session)
        self.mining_scope_repository = SqlAlchemyMiningScopeRepository(session)
        self.schedule_repository = SqlAlchemyMonitoringScheduleRepository(session)
        self.execution_repository = SqlAlchemyMiningExecutionRepository(session)
        self.repository_execution_repository = SqlAlchemyRepositoryExecutionRepository(session)
        self.finding_repository = SqlAlchemyFindingRepository(session)
        self.repository_checkpoint_repository = SqlAlchemyRepositoryCheckpointRepository(session)
        self.author_policy_repository = SqlAlchemyAuthorPolicyRepository(session)
        self.dashboard_summary_repository = SqlAlchemyDashboardSummaryRepository(session)

    def begin_execution_creation(self):
        begin_execution_snapshot(self.session)

    def commit(self):
        try:
            with execution_conflicts():
                self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            if "create_request_receipts" in str(exc.orig): raise DuplicateIdempotencyKey() from exc
            if getattr(getattr(exc.orig, "diag", None), "constraint_name", None) == "uq_execution_scheduled_occurrence":
                raise DuplicateScheduledOccurrence() from exc
            raise

    def rollback(self): self.session.rollback()


class SqlAlchemyMiningExecutionRepository:
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _entity(row):
        if row is None:
            return None
        return MiningExecution(**{key: getattr(row, key) for key in (
            'id', 'monitoring_configuration_id', 'trigger_type', 'status', 'created_at', 'scheduled_occurrence_at', 'started_at', 'completed_at',
            'repository_count', 'successful_repository_count', 'failed_repository_count', 'finding_count', 'error_code', 'error_summary')},
            scope_resolution_failure_count=getattr(row, 'scope_resolution_failure_count', 0),
            repository_mining_completed=getattr(row, 'repository_mining_completed', False),
            snapshot=load_execution_snapshot(row.snapshot))

    def add(self, execution):
        values = {key: getattr(execution, key) for key in (
            'id', 'monitoring_configuration_id', 'trigger_type', 'status', 'created_at', 'scheduled_occurrence_at', 'started_at', 'completed_at',
            'repository_count', 'successful_repository_count', 'failed_repository_count', 'finding_count', 'error_code', 'error_summary', 'scope_resolution_failure_count', 'repository_mining_completed')}
        self.session.add(MiningExecutionRecord(**values, snapshot=execution.snapshot.model_dump(mode='json')))

    def get(self, identifier, *, for_update=False):
        query = select(MiningExecutionRecord).where(MiningExecutionRecord.id == identifier).execution_options(populate_existing=True)
        if for_update:
            query = query.with_for_update()
        with execution_conflicts():
            return self._entity(self.session.scalar(query))

    def active_for(self, configuration_id):
        with execution_conflicts():
            row = self.session.scalar(select(MiningExecutionRecord).where(
                MiningExecutionRecord.monitoring_configuration_id == configuration_id,
                MiningExecutionRecord.status.in_(['pending', 'running'])).with_for_update().execution_options(populate_existing=True))
            return self._entity(row)

    def transition(self, execution, expected_status):
        with execution_conflicts():
            result = self.session.execute(update(MiningExecutionRecord).where(
                MiningExecutionRecord.id == execution.id, MiningExecutionRecord.status == expected_status).values(
                status=execution.status, started_at=execution.started_at, completed_at=execution.completed_at,
                error_code=execution.error_code, error_summary=execution.error_summary,
                repository_mining_completed=execution.repository_mining_completed))
            return result.rowcount == 1

    def update_snapshot(self, execution):
        result = self.session.execute(update(MiningExecutionRecord).where(
            MiningExecutionRecord.id == execution.id,
            MiningExecutionRecord.status == "running").values(
                snapshot=execution.snapshot.model_dump(mode="json")))
        return result.rowcount == 1

    def update_counters(self, identifier, *, repository_count, successful_count, failed_count, finding_count, scope_failures=0, repository_mining_completed=False):
        return self.session.execute(update(MiningExecutionRecord).where(MiningExecutionRecord.id == identifier).values(
            repository_count=repository_count, successful_repository_count=successful_count,
            failed_repository_count=failed_count, finding_count=finding_count,
            scope_resolution_failure_count=scope_failures,
            repository_mining_completed=repository_mining_completed)).rowcount == 1

    def page(self, *, page, page_size, configuration_id=None, status=None, trigger_type=None):
        conditions = []
        if configuration_id is not None:
            conditions.append(MiningExecutionRecord.monitoring_configuration_id == configuration_id)
        if status is not None:
            conditions.append(MiningExecutionRecord.status == status)
        if trigger_type is not None:
            conditions.append(MiningExecutionRecord.trigger_type == trigger_type)
        total = self.session.scalar(select(func.count()).select_from(MiningExecutionRecord).where(*conditions))
        rows = self.session.scalars(select(MiningExecutionRecord).where(*conditions).order_by(
            MiningExecutionRecord.created_at.desc(), MiningExecutionRecord.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
        return [self._entity(row) for row in rows], total


class SqlAlchemyRepositoryExecutionRepository:
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _entity(row):
        if row is None:
            return None
        return RepositoryExecution(
            id=row.id, mining_execution_id=row.mining_execution_id,
            gitlab_project_id=row.gitlab_project_id, repository_name=row.repository_name,
            repository_full_path=row.repository_full_path, status=row.status,
            started_at=row.started_at, completed_at=row.completed_at,
            target_branch=row.target_branch,
            processed_branch=row.processed_branch, file_count=row.file_count,
            observed_extensions=tuple(row.observed_extensions or ()),
            extensions_truncated=row.extensions_truncated, finding_count=row.finding_count,
            error_code=row.error_code, error_summary=row.error_summary)

    def add(self, item):
        self.session.add(RepositoryExecutionRecord(
            id=item.id, mining_execution_id=item.mining_execution_id,
            gitlab_project_id=item.gitlab_project_id, repository_name=item.repository_name,
            repository_full_path=item.repository_full_path, status=item.status,
            started_at=item.started_at, completed_at=item.completed_at,
            target_branch=item.target_branch,
            processed_branch=item.processed_branch, file_count=item.file_count,
            observed_extensions=list(item.observed_extensions), extensions_truncated=item.extensions_truncated,
            finding_count=item.finding_count, error_code=item.error_code, error_summary=item.error_summary))

    def get(self, identifier, execution_id=None, *, for_update=False):
        query = select(RepositoryExecutionRecord).where(RepositoryExecutionRecord.id == identifier)
        if execution_id is not None:
            query = query.where(RepositoryExecutionRecord.mining_execution_id == execution_id)
        if for_update:
            query = query.with_for_update()
        return self._entity(self.session.scalar(query.execution_options(populate_existing=True)))

    def get_by_project(self, execution_id, project_id):
        row = self.session.scalar(select(RepositoryExecutionRecord).where(
            RepositoryExecutionRecord.mining_execution_id == execution_id,
            RepositoryExecutionRecord.gitlab_project_id == project_id))
        return self._entity(row)

    def transition(self, item, expected_status):
        result = self.session.execute(update(RepositoryExecutionRecord).where(
            RepositoryExecutionRecord.id == item.id,
            RepositoryExecutionRecord.status == expected_status).values(
                status=item.status, started_at=item.started_at, completed_at=item.completed_at,
                target_branch=item.target_branch,
                processed_branch=item.processed_branch, file_count=item.file_count,
                observed_extensions=list(item.observed_extensions), extensions_truncated=item.extensions_truncated,
                finding_count=item.finding_count, error_code=item.error_code, error_summary=item.error_summary))
        return result.rowcount == 1

    def save_summary(self, item, expected_status='running'):
        result = self.session.execute(update(RepositoryExecutionRecord).where(
            RepositoryExecutionRecord.id == item.id,
            RepositoryExecutionRecord.status == expected_status).values(
            target_branch=item.target_branch,
            processed_branch=item.processed_branch, file_count=item.file_count,
            observed_extensions=list(item.observed_extensions), extensions_truncated=item.extensions_truncated,
            finding_count=item.finding_count))
        return result.rowcount == 1

    def list_for_execution(self, execution_id, *, page=1, page_size=25):
        conditions = [RepositoryExecutionRecord.mining_execution_id == execution_id]
        total = self.session.scalar(select(func.count()).select_from(RepositoryExecutionRecord).where(*conditions))
        rows = self.session.scalars(select(RepositoryExecutionRecord).where(*conditions).order_by(
            RepositoryExecutionRecord.repository_full_path.asc(), RepositoryExecutionRecord.gitlab_project_id.asc(),
            RepositoryExecutionRecord.target_branch.asc().nulls_last()
        ).offset((page - 1) * page_size).limit(page_size)).all()
        return [self._entity(row) for row in rows], total

    def update_execution_counters(self, execution_id, *, repository_count, successful_count, failed_count, finding_count, scope_failures=0):
        return self.session.execute(update(MiningExecutionRecord).where(MiningExecutionRecord.id == execution_id).values(
            repository_count=repository_count, successful_repository_count=successful_count,
            failed_repository_count=failed_count, finding_count=finding_count,
            scope_resolution_failure_count=scope_failures)).rowcount == 1


class SqlAlchemyRepositoryCheckpointRepository:
    def __init__(self, session): self.session = session

    def get(self, configuration_id, project_id, branch):
        row = self.session.scalar(select(RepositoryCheckpointRecord).where(
            RepositoryCheckpointRecord.monitoring_configuration_id == configuration_id,
            RepositoryCheckpointRecord.gitlab_project_id == project_id,
            RepositoryCheckpointRecord.branch == branch))
        if row is None: return None
        return RepositoryCheckpoint(row.id, row.monitoring_configuration_id, row.gitlab_project_id,
                                    row.branch, row.last_successful_commit_hash, row.updated_at)

    def put(self, item):
        stmt = pg_insert(RepositoryCheckpointRecord).values(
            id=item.id, monitoring_configuration_id=item.monitoring_configuration_id,
            gitlab_project_id=item.gitlab_project_id, branch=item.branch,
            last_successful_commit_hash=item.last_successful_commit_hash, updated_at=item.updated_at)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_repository_checkpoint_identity",
            set_={"last_successful_commit_hash": item.last_successful_commit_hash, "updated_at": item.updated_at})
        self.session.execute(stmt)


class SqlAlchemyFindingRepository:
    def __init__(self, session): self.session = session

    def add(self, item):
        self.session.add(FindingRecord(**{key: getattr(item, key) for key in (
            "id", "repository_execution_id", "rule_id", "rule_version", "severity", "title", "summary",
            "commit_hash", "author_email", "author_email_state", "author_name", "authored_at",
            "commit_message_summary", "file_path", "line_start", "line_end", "created_at")}))

    @staticmethod
    def entity(row):
        return Finding(**{key: getattr(row, key) for key in Finding.__dataclass_fields__})

    def get(self, identifier):
        row = self.session.get(FindingRecord, identifier)
        return self.entity(row) if row else None

    def count_by_executions(self, execution_ids):
        if not execution_ids:
            return {}
        rows = self.session.execute(select(RepositoryExecutionRecord.mining_execution_id,
            func.count(FindingRecord.id)).join(FindingRecord,
            FindingRecord.repository_execution_id == RepositoryExecutionRecord.id)
            .where(RepositoryExecutionRecord.mining_execution_id.in_(execution_ids))
            .group_by(RepositoryExecutionRecord.mining_execution_id)).all()
        return {execution_id: int(count) for execution_id, count in rows}

    def list_for_execution(self, execution_id, *, page=1, page_size=25, repository_id=None, rule_id=None, severity=None):
        query = select(FindingRecord, RepositoryExecutionRecord.repository_full_path).join(
            RepositoryExecutionRecord, FindingRecord.repository_execution_id == RepositoryExecutionRecord.id
        ).where(RepositoryExecutionRecord.mining_execution_id == execution_id)
        if repository_id is not None: query = query.where(RepositoryExecutionRecord.id == repository_id)
        if rule_id is not None: query = query.where(FindingRecord.rule_id == rule_id)
        if severity is not None: query = query.where(FindingRecord.severity == severity)
        count_query = select(func.count()).select_from(query.subquery())
        total = self.session.scalar(count_query)
        rows = self.session.execute(query.order_by(FindingRecord.authored_at.desc().nullslast(), FindingRecord.id.asc())
                                    .offset((page - 1) * page_size).limit(page_size)).all()
        return [(self.entity(row[0]), row[1]) for row in rows], total

    def list_for_repository(self, repository_execution_id, *, page=1, page_size=25, rule_id=None, severity=None):
        conditions = [FindingRecord.repository_execution_id == repository_execution_id]
        if rule_id is not None: conditions.append(FindingRecord.rule_id == rule_id)
        if severity is not None: conditions.append(FindingRecord.severity == severity)
        query = select(FindingRecord).where(*conditions)
        total = self.session.scalar(select(func.count()).select_from(FindingRecord).where(*conditions))
        rows = self.session.scalars(query.order_by(FindingRecord.authored_at.desc().nullslast(), FindingRecord.id.asc())
                                    .offset((page - 1) * page_size).limit(page_size)).all()
        return [self.entity(row) for row in rows], total


class SqlAlchemyDashboardSummaryRepository:
    """Bounded aggregate reads over the existing execution/result tables."""
    def __init__(self, session: Session):
        self.session = session

    def summarize(self, start: datetime, end: datetime) -> dict:
        window = (MiningExecutionRecord.created_at >= start,
                  MiningExecutionRecord.created_at < end)
        status_rows = self.session.execute(select(MiningExecutionRecord.status, func.count())
            .where(*window).group_by(MiningExecutionRecord.status)).all()
        utc_day = cast(func.timezone(literal_column("'UTC'"), MiningExecutionRecord.created_at), Date)
        daily_rows = self.session.execute(select(utc_day, func.count())
            .where(*window).group_by(utc_day)).all()
        repository_count = self.session.scalar(select(func.count(distinct(RepositoryExecutionRecord.gitlab_project_id))
            ).join(MiningExecutionRecord, MiningExecutionRecord.id == RepositoryExecutionRecord.mining_execution_id)
            .where(*window)) or 0
        finding_count = self.session.scalar(select(func.count(FindingRecord.id)
            ).join(RepositoryExecutionRecord, FindingRecord.repository_execution_id == RepositoryExecutionRecord.id
            ).join(MiningExecutionRecord, MiningExecutionRecord.id == RepositoryExecutionRecord.mining_execution_id)
            .where(*window)) or 0
        rule_rows = self.session.execute(select(FindingRecord.rule_id, func.count(FindingRecord.id))
            .join(RepositoryExecutionRecord, FindingRecord.repository_execution_id == RepositoryExecutionRecord.id
            ).join(MiningExecutionRecord, MiningExecutionRecord.id == RepositoryExecutionRecord.mining_execution_id)
            .where(*window).group_by(FindingRecord.rule_id)
            .order_by(func.count(FindingRecord.id).desc(), FindingRecord.rule_id.asc())).all()
        finding_count_by_execution = select(FindingRecord.repository_execution_id,
            func.count(FindingRecord.id).label("finding_count")).group_by(FindingRecord.repository_execution_id).subquery()
        recent_rows = self.session.execute(select(MiningExecutionRecord,
            func.coalesce(func.sum(finding_count_by_execution.c.finding_count), 0).label("finding_count"))
            .outerjoin(RepositoryExecutionRecord, RepositoryExecutionRecord.mining_execution_id == MiningExecutionRecord.id)
            .outerjoin(finding_count_by_execution, finding_count_by_execution.c.repository_execution_id == RepositoryExecutionRecord.id)
            .where(*window).group_by(MiningExecutionRecord.id)
            .order_by(MiningExecutionRecord.created_at.desc(), MiningExecutionRecord.id.asc()).limit(5)).all()
        return {
            "status_distribution": dict(status_rows),
            "daily_executions": {day.isoformat(): int(count) for day, count in daily_rows},
            "repositories_processed": int(repository_count),
            "finding_count": int(finding_count),
            "findings_by_rule": [{"rule_id": rule, "label": rule.replace("_", " ").capitalize(), "count": int(count)}
                                 for rule, count in rule_rows],
            "recent_executions": [{
                "id": row.id, "configuration_name": row.snapshot.get("configuration_name", ""),
                "status": row.status, "trigger_type": row.trigger_type,
                "created_at": row.created_at, "started_at": row.started_at,
                "completed_at": row.completed_at,
                "duration_seconds": ((row.completed_at - row.started_at).total_seconds()
                                     if row.completed_at and row.started_at else None),
                "finding_count": int(count),
            } for row, count in recent_rows],
        }
