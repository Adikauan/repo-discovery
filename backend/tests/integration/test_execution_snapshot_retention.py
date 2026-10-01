from uuid import uuid4
import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from app.application.use_cases.create_manual_execution import CreateManualExecution
from app.domain.entities.mining_scope import MiningScope, SelectedGitLabGroup, SelectedGitLabRepository
from app.infrastructure.database.models import MonitoringConfigurationRecord
from tests.integration.test_manual_execution_concurrency import owner
from tests.unit.test_mining_execution import NOW


def test_history_survives_configuration_scope_credential_schedule_and_retirement(pg_uow_factory):
    config = owner(pg_uow_factory)
    uow = pg_uow_factory()
    fingerprint = 'a' * 64
    group = SelectedGitLabGroup(uuid4(), fingerprint, 91, 'Group', 'group', None, NOW)
    repo = SelectedGitLabRepository(uuid4(), fingerprint, 712, 'Repo', 'group/repo', 91, NOW)
    assert uow.mining_scope_repository.replace(MiningScope(config.id, 1, NOW, (group,), (repo,)), 0)
    assert uow.credential_repository.replace(config.id, b'original-ciphertext', None, NOW)
    uow.commit()
    execution = CreateManualExecution(pg_uow_factory(), clock=lambda: NOW).execute(config.id)
    snapshot = execution.snapshot.model_dump(mode='json')
    edit = pg_uow_factory()
    assert edit.configuration_repository.update(config.update(name='Changed', description='Changed', gitlab_url='https://other.example.com', enabled=True, now=NOW), config.revision)
    assert edit.mining_scope_repository.replace(MiningScope(config.id, 2, NOW), 1)
    assert edit.credential_repository.replace(config.id, b'replacement-ciphertext', 1, NOW)
    replaced_credential = edit.credential_repository.get(config.id)
    assert replaced_credential.revision == 2
    assert replaced_credential.encrypted_token == b'replacement-ciphertext'
    # Schedule mutations have no snapshot relationship; use the existing application use case.
    edit.commit()
    from app.application.use_cases.replace_monitoring_schedule import ReplaceMonitoringSchedule
    ReplaceMonitoringSchedule(pg_uow_factory(), now=lambda: NOW).execute(config.id, dict(recurrence_type='daily', enabled=True, execution_time='09:00', timezone='UTC'), 0)
    retire = pg_uow_factory()
    retire.configuration_repository.retire(retire.configuration_repository.get_active(config.id).retire(NOW))
    retire.commit()
    historical = pg_uow_factory().execution_repository.get(execution.id)
    assert historical.snapshot.model_dump(mode='json') == snapshot
    assert historical.snapshot.groups[0].gitlab_group_id == 91
    assert historical.snapshot.repositories[0].gitlab_project_id == 712
    assert historical.snapshot.groups[0].instance_fingerprint == fingerprint
    assert historical.snapshot.repositories[0].instance_fingerprint == fingerprint
    assert 'ciphertext' not in historical.snapshot.model_dump_json()
    removal = pg_uow_factory()
    with pytest.raises(IntegrityError):
        removal.session.execute(delete(MonitoringConfigurationRecord).where(MonitoringConfigurationRecord.id == config.id))
        removal.commit()
    removal.rollback()
    assert pg_uow_factory().execution_repository.get(execution.id) == historical
