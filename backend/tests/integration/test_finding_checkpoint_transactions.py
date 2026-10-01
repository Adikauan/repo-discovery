from datetime import timedelta
from uuid import uuid4
import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.entities.execution_snapshot import ExecutionSnapshotV1
from app.domain.entities.finding import Finding
from app.domain.entities.mining_execution import MiningExecution
from app.domain.entities.repository_checkpoint import RepositoryCheckpoint
from app.domain.entities.repository_execution import RepositoryExecution
from app.domain.monitoring_configuration import MonitoringConfiguration
from tests.unit.test_mining_execution import NOW


def prepared(uow):
    configuration = MonitoringConfiguration.create(identifier=uuid4(), name="Findings", gitlab_url="https://gitlab.example.com", now=NOW)
    uow.configuration_repository.add(configuration); uow.commit()
    execution = MiningExecution.create(ExecutionSnapshotV1.capture(configuration, uow.mining_scope_repository.get(configuration.id)), NOW)
    execution = execution.transition("running", NOW + timedelta(seconds=1), expected_status="pending")
    uow.execution_repository.add(execution); uow.commit()
    repository = RepositoryExecution.create(execution.id, 987, "repo", "group/repo").transition(
        "running", NOW + timedelta(seconds=2), expected_status="pending")
    uow.repository_execution_repository.add(repository); uow.commit()
    return configuration, execution, repository


def candidate(repository, *, sha="a" * 40):
    return Finding(uuid4(), repository.id, "unauthorized-commit-author", "1", "warning",
        "Unauthorized commit author", "Author is not allowed.", sha, "author@example.com", "valid",
        None, NOW, None, None, None, None, NOW + timedelta(seconds=3))


def test_checkpoint_finding_uniqueness_and_atomic_rollback(pg_uow_factory):
    uow = pg_uow_factory()
    configuration, execution, repository = prepared(uow)
    checkpoint = RepositoryCheckpoint(uuid4(), configuration.id, 987, "main", "a" * 40, NOW)
    finding = candidate(repository)
    uow.finding_repository.add(finding)
    uow.repository_checkpoint_repository.put(checkpoint)
    uow.commit()
    fresh = pg_uow_factory()
    assert fresh.repository_checkpoint_repository.get(configuration.id, 987, "main").last_successful_commit_hash == "a" * 40
    assert fresh.finding_repository.get(finding.id) == finding

    duplicate = pg_uow_factory()
    duplicate.finding_repository.add(candidate(repository))
    with pytest.raises(IntegrityError): duplicate.commit()
    duplicate.rollback()
    assert pg_uow_factory().finding_repository.get(finding.id) == finding

    rollback = pg_uow_factory()
    rollback.finding_repository.add(candidate(repository, sha="b" * 40))
    rollback.repository_checkpoint_repository.put(RepositoryCheckpoint(uuid4(), configuration.id, 987, "main", "b" * 40, NOW + timedelta(seconds=1)))
    rollback.rollback()
    verify = pg_uow_factory()
    assert verify.repository_checkpoint_repository.get(configuration.id, 987, "main").last_successful_commit_hash == "a" * 40
    assert verify.finding_repository.list_for_repository(repository.id)[1] == 1
