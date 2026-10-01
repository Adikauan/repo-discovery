from datetime import UTC, datetime
from uuid import uuid4

from app.application.use_cases.save_gitlab_credential import SaveGitLabCredential
from app.application.use_cases.validate_gitlab_connection import ValidateGitLabConnection
from app.domain.monitoring_configuration import MonitoringConfiguration
from tests.fakes import FakeCipher, FakeGitLabClient, MemoryUnitOfWork


def test_credential_actions_leave_configuration_fields_and_enabled_state_unchanged():
    now = datetime(2026, 9, 28, tzinfo=UTC); identifier = uuid4(); uow = MemoryUnitOfWork()
    original = MonitoringConfiguration.create(identifier=identifier, name="Scope", description="kept", gitlab_url="https://gitlab.example", now=now)
    uow.configurations[identifier] = original
    SaveGitLabCredential(uow, FakeCipher(), lambda: now).execute(identifier, "token")
    ValidateGitLabConnection(uow, FakeCipher(), FakeGitLabClient(), lambda: now).execute(identifier)
    assert uow.configurations[identifier] == original
