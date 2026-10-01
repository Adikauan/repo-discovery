from uuid import uuid4

from app.domain.entities.repository_checkpoint import RepositoryCheckpoint
from app.domain.monitoring_configuration import MonitoringConfiguration
from tests.unit.test_mining_execution import NOW


def test_checkpoint_identity_is_exact_policy_branch_and_never_crosses_branches(pg_uow_factory):
    owner = pg_uow_factory()
    configuration = MonitoringConfiguration.create(
        identifier=uuid4(), name="Branch checkpoints", gitlab_url="https://gitlab.example.com", now=NOW)
    owner.configuration_repository.add(configuration)
    owner.commit()

    owner.repository_checkpoint_repository.put(RepositoryCheckpoint(
        uuid4(), configuration.id, 987, "master", "a" * 40, NOW))
    owner.repository_checkpoint_repository.put(RepositoryCheckpoint(
        uuid4(), configuration.id, 987, "qualidade", "b" * 40, NOW))
    owner.commit()

    reader = pg_uow_factory()
    assert reader.repository_checkpoint_repository.get(configuration.id, 987, "qualidade").last_successful_commit_hash == "b" * 40
    assert reader.repository_checkpoint_repository.get(configuration.id, 987, "master").last_successful_commit_hash == "a" * 40
    assert reader.repository_checkpoint_repository.get(configuration.id, 987, "release") is None
