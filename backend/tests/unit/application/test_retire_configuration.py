from datetime import UTC, datetime

import pytest

from app.application.use_cases.create_monitoring_configuration import CreateMonitoringConfiguration
from app.application.use_cases.retire_monitoring_configuration import RetireMonitoringConfiguration
from app.domain.errors import NotFoundError
from tests.fakes import MemoryUnitOfWork
from app.application.use_cases.save_gitlab_credential import SaveGitLabCredential
from tests.fakes import FakeCipher


def test_retirement_hides_record_but_retains_values_and_repeated_retirement_is_not_found():
    uow = MemoryUnitOfWork()
    created = CreateMonitoringConfiguration(uow, clock=lambda: datetime(2026, 9, 28, tzinfo=UTC)).execute(
        {"name": "Retained", "description": "Record", "gitlab_url": "https://gitlab.example"})
    identifier = next(iter(uow.configurations))
    SaveGitLabCredential(uow, FakeCipher()).execute(identifier, "retire-me")
    RetireMonitoringConfiguration(uow).execute(identifier)
    retained = uow.configurations[identifier]
    assert retained.name == "Retained" and retained.retired_at is not None
    assert uow.configuration_repository.get_active(identifier) is None
    assert uow.configuration_repository.list_active() == []
    assert identifier not in uow.credentials
    with pytest.raises(NotFoundError): RetireMonitoringConfiguration(uow).execute(identifier)
    assert created.response_snapshot["name"] == "Retained"
