from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from app.domain.entities.mining_scope import MiningScope, SelectedGitLabGroup, SelectedGitLabRepository
from app.infrastructure.database.models import MonitoringConfigurationRecord
from app.domain.monitoring_configuration import MonitoringConfiguration
from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
from app.application.use_cases.get_mining_scope import GetMiningScope
from tests.fakes import FakeCipher, FakeGitLabClient


def test_scope_empty_first_save_reload_and_version_compare_and_swap(scope_uow_factory):
    identifier = uuid4(); now = datetime.now(UTC)
    seed = scope_uow_factory()
    seed.configuration_repository.add(MonitoringConfiguration.create(
        identifier=identifier, name="Scope persistence", gitlab_url="https://gitlab.example", now=now))
    seed.commit()
    assert seed.mining_scope_repository.get(identifier).version == 0
    assert seed.mining_scope_repository.replace(MiningScope(identifier, 1, now), 0)
    seed.commit()
    assert seed.mining_scope_repository.get(identifier).version == 1

    group = SelectedGitLabGroup(uuid4(), "a" * 64, 10, "Platform", "engineering/platform", 1, now)
    repository = SelectedGitLabRepository(uuid4(), "a" * 64, 100, "API", "engineering/platform/api", 10, now)
    left_scope = MiningScope(identifier, 2, now, (group,), (repository,))
    left, right = scope_uow_factory(), scope_uow_factory()
    assert left.mining_scope_repository.get(identifier).version == 1
    assert right.mining_scope_repository.get(identifier).version == 1
    assert left.mining_scope_repository.replace(left_scope, 1)
    left.commit()
    stale_scope = MiningScope(identifier, 2, now, (), ())
    assert not right.mining_scope_repository.replace(stale_scope, 1)
    right.rollback()

    final = scope_uow_factory().mining_scope_repository.get(identifier)
    assert final.version == 2
    assert final.groups == (group,) and final.repositories == (repository,)


def test_scope_rows_survive_credential_and_url_changes_and_retirement(scope_uow_factory):
    identifier = uuid4(); now = datetime.now(UTC)
    setup = scope_uow_factory()
    configuration = MonitoringConfiguration.create(identifier=identifier, name="Retained scope",
        gitlab_url="https://gitlab.example", now=now)
    setup.configuration_repository.add(configuration); setup.commit()
    group = SelectedGitLabGroup(uuid4(), "a" * 64, 10, "Platform", "engineering/platform", 1, now)
    initial = MiningScope(identifier, 1, now, (group,), ())
    assert setup.mining_scope_repository.replace(initial, 0)
    assert setup.credential_repository.replace(identifier, b"cipher-one", None, now)
    setup.commit()

    replacement = scope_uow_factory()
    assert replacement.credential_repository.replace(identifier, b"cipher-two", 1, now)
    replacement.commit()
    after_credential_change = scope_uow_factory().mining_scope_repository.get(identifier)
    assert after_credential_change.groups == (group,)
    assert after_credential_change.version == 1

    url_update = scope_uow_factory()
    current = url_update.configuration_repository.get_active(identifier)
    updated = current.update(name=current.name, description=current.description,
        gitlab_url="https://another-gitlab.example", enabled=current.enabled, now=now)
    assert url_update.configuration_repository.update(updated, current.revision)
    url_update.commit()
    after_url_change = scope_uow_factory().mining_scope_repository.get(identifier)
    assert after_url_change.groups[0].instance_fingerprint == "a" * 64

    clear = scope_uow_factory()
    assert clear.mining_scope_repository.replace(MiningScope(identifier, 2, now), 1)
    clear.commit()
    assert scope_uow_factory().mining_scope_repository.get(identifier).groups == ()

    retained_id = uuid4()
    retained = scope_uow_factory()
    retained.configuration_repository.add(MonitoringConfiguration.create(identifier=retained_id,
        name="Retired with scope", gitlab_url="https://gitlab.example", now=now))
    retained.commit()
    retained_group = SelectedGitLabGroup(uuid4(), "b" * 64, 20, "Research", "research", None, now)
    assert retained.mining_scope_repository.replace(MiningScope(retained_id, 1, now, (retained_group,), ()), 0)
    retained.commit()
    retirement = scope_uow_factory()
    active = retirement.configuration_repository.get_active(retained_id)
    assert retirement.configuration_repository.retire(active.retire(now))
    retirement.commit()
    assert scope_uow_factory().mining_scope_repository.get(retained_id).groups == (retained_group,)


def test_scope_uniqueness_constraint_and_configuration_delete_cascade(scope_uow_factory):
    identifier = uuid4(); now = datetime.now(UTC)
    uow = scope_uow_factory()
    uow.configuration_repository.add(MonitoringConfiguration.create(identifier=identifier,
        name="Scope constraints", gitlab_url="https://gitlab.example", now=now))
    group = SelectedGitLabGroup(uuid4(), "c" * 64, 30, "Tools", "tools", None, now)
    assert uow.mining_scope_repository.replace(MiningScope(identifier, 1, now, (group,), ()), 0)
    uow.commit()

    duplicate = SelectedGitLabGroup(uuid4(), "c" * 64, 30, "Tools duplicate", "tools", None, now)
    invalid = scope_uow_factory()
    assert invalid.mining_scope_repository.replace(MiningScope(identifier, 2, now, (group, duplicate), ()), 1)
    with pytest.raises(IntegrityError):
        invalid.commit()
    preserved = scope_uow_factory().mining_scope_repository.get(identifier)
    assert preserved.version == 1 and preserved.groups == (group,)

    removal = scope_uow_factory()
    removal.session.execute(delete(MonitoringConfigurationRecord).where(MonitoringConfigurationRecord.id == identifier))
    removal.commit()
    cascaded = scope_uow_factory().mining_scope_repository.get(identifier)
    assert cascaded.version == 0 and cascaded.groups == () and cascaded.repositories == ()


def test_scope_rows_survive_provider_reconciliation_failure(scope_uow_factory):
    identifier = uuid4(); now = datetime.now(UTC)
    setup = scope_uow_factory()
    setup.configuration_repository.add(MonitoringConfiguration.create(identifier=identifier,
        name="Unresolved scope", gitlab_url="https://gitlab.example", now=now))
    group = SelectedGitLabGroup(uuid4(), normalized_url_fingerprint("https://gitlab.example"),
        40, "Research", "research", None, now)
    assert setup.mining_scope_repository.replace(MiningScope(identifier, 1, now, (group,), ()), 0)
    assert setup.credential_repository.replace(identifier, b"encrypted:test-token", None, now)
    setup.commit()

    provider = FakeGitLabClient()
    provider.groups = {40: provider.discovery_result(outcome="provider_unavailable")}
    reading = scope_uow_factory()
    projected, availability = GetMiningScope(reading, FakeCipher(), provider).execute(identifier)
    assert projected.groups == (group,)
    assert availability[group.selection_id] == "unresolved"
    persisted = scope_uow_factory().mining_scope_repository.get(identifier)
    assert persisted.version == 1 and persisted.groups == (group,)
