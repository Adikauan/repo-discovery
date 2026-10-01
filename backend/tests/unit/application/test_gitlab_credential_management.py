from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.use_cases.get_gitlab_connection_status import GetGitLabConnectionStatus
from app.application.use_cases.remove_gitlab_credential import RemoveGitLabCredential
from app.application.use_cases.save_gitlab_credential import SaveGitLabCredential
from app.domain.errors import CredentialReplacementConflict
from app.domain.monitoring_configuration import MonitoringConfiguration
from tests.fakes import FakeCipher, MemoryUnitOfWork


def configured_uow():
    uow = MemoryUnitOfWork(); identifier = uuid4(); now = datetime(2026, 9, 28, tzinfo=UTC)
    uow.configurations[identifier] = MonitoringConfiguration.create(
        identifier=identifier, name="Test", gitlab_url="https://gitlab.example", now=now)
    return uow, identifier, now


def test_save_replace_status_remove_and_idempotent_remove():
    uow, identifier, now = configured_uow(); use_case = SaveGitLabCredential(uow, FakeCipher(), lambda: now)
    status = use_case.execute(identifier, "first")
    assert status.credential_configured and status.state == "configured_not_validated"
    assert uow.credentials[identifier].revision == 1
    use_case.execute(identifier, "second")
    assert uow.credentials[identifier].revision == 2
    assert b"first" not in uow.credentials[identifier].encrypted_token
    RemoveGitLabCredential(uow).execute(identifier); RemoveGitLabCredential(uow).execute(identifier)
    assert GetGitLabConnectionStatus(uow).execute(identifier).state == "not_configured"


def test_stale_internal_revision_maps_to_safe_conflict():
    uow, identifier, now = configured_uow(); SaveGitLabCredential(uow, FakeCipher(), lambda: now).execute(identifier, "first")
    original = uow.credential_repository.replace
    uow.credential_repository.replace = lambda *args: False
    with pytest.raises(CredentialReplacementConflict) as caught:
        SaveGitLabCredential(uow, FakeCipher(), lambda: now).execute(identifier, "secret")
    assert "secret" not in str(caught.value)
    uow.credential_repository.replace = original
