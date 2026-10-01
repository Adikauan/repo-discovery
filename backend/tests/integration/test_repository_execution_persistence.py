from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.entities.execution_snapshot import ExecutionSnapshotV1
from app.domain.entities.mining_execution import MiningExecution
from app.domain.entities.repository_execution import RepositoryExecution
from app.domain.value_objects.repository_summary import RepositorySummaryResult
from app.infrastructure.database.models import MiningExecutionRecord
from app.domain.monitoring_configuration import MonitoringConfiguration
from tests.unit.test_mining_execution import NOW


def test_interrupted_worker_persists_running_rows_without_fabricated_results(pg_uow_factory):
    owner = pg_uow_factory()
    configuration = MonitoringConfiguration.create(identifier=uuid4(), name="Interrupted", gitlab_url="https://gitlab.example.com", now=NOW)
    owner.configuration_repository.add(configuration); owner.commit()
    execution = MiningExecution.create(ExecutionSnapshotV1.capture(configuration, owner.mining_scope_repository.get(configuration.id)), NOW)
    execution = execution.transition("running", NOW + timedelta(seconds=1), expected_status="pending")
    owner.execution_repository.add(execution)
    row = RepositoryExecution.create(execution.id, 88, "worker", "team/worker").transition(
        "running", NOW + timedelta(seconds=2), expected_status="pending")
    owner.repository_execution_repository.add(row)
    owner.repository_execution_repository.update_execution_counters(execution.id,
        repository_count=1, successful_count=0, failed_count=0, finding_count=0)
    owner.commit()

    # A worker interruption occurs here: its running transition committed, but it never retrieves metadata.
    fresh = pg_uow_factory()
    saved_execution = fresh.execution_repository.get(execution.id)
    saved_repository = fresh.repository_execution_repository.get(row.id)
    assert saved_execution.status == "running" and saved_execution.completed_at is None
    assert saved_execution.repository_count == 1 and saved_execution.successful_repository_count == 0
    assert saved_repository.status == "running" and saved_repository.started_at == row.started_at
    assert saved_repository.completed_at is None and saved_repository.processed_branch is None
    assert saved_repository.file_count == 0 and saved_repository.finding_count == 0
    assert saved_repository.observed_extensions == () and not saved_repository.extensions_truncated
    assert saved_repository.error_code is None and saved_repository.error_summary is None


def test_repository_summary_persistence_uniqueness_and_parent_retention(pg_uow_factory):
    uow = pg_uow_factory()
    configuration = MonitoringConfiguration.create(identifier=uuid4(), name="Persistence", gitlab_url="https://gitlab.example.com", now=NOW)
    uow.configuration_repository.add(configuration); uow.commit()
    execution = MiningExecution.create(ExecutionSnapshotV1.capture(configuration, uow.mining_scope_repository.get(configuration.id)), NOW)
    execution = execution.transition("running", NOW + timedelta(seconds=1), expected_status="pending")
    uow.execution_repository.add(execution); uow.commit()
    pending = RepositoryExecution.create(execution.id, 89, "service", "team/service")
    running = pending.transition("running", NOW + timedelta(seconds=2), expected_status="pending")
    completed = running.with_summary(RepositorySummaryResult("stable", 3, (".py", ".toml"), False, 0)).transition(
        "completed", NOW + timedelta(seconds=3), expected_status="running")
    uow.repository_execution_repository.add(pending); uow.commit()
    uow.repository_execution_repository.transition(running, "pending")
    uow.commit()
    uow.repository_execution_repository.transition(completed, "running")
    uow.commit()
    persisted = pg_uow_factory().repository_execution_repository.get(completed.id)
    assert persisted.status == "completed" and persisted.processed_branch == "stable"
    assert persisted.file_count == 3 and persisted.observed_extensions == (".py", ".toml")

    duplicate_uow = pg_uow_factory()
    duplicate = RepositoryExecution.create(execution.id, 89, "duplicate", "team/duplicate")
    duplicate_uow.repository_execution_repository.add(duplicate)
    with pytest.raises(IntegrityError):
        duplicate_uow.commit()
    duplicate_uow.rollback()

    delete_uow = pg_uow_factory()
    parent_row = delete_uow.session.get(MiningExecutionRecord, execution.id)
    delete_uow.session.delete(parent_row)
    with pytest.raises(IntegrityError):
        delete_uow.commit()
    delete_uow.rollback()
    assert pg_uow_factory().repository_execution_repository.get(completed.id) == persisted
