from datetime import UTC, datetime
from uuid import uuid4

from app.application.use_cases.save_gitlab_credential import SaveGitLabCredential
from app.application.use_cases.validate_gitlab_connection import ValidateGitLabConnection
from app.domain.monitoring_configuration import MonitoringConfiguration
from app.domain.value_objects.connection_validation_result import ConnectionValidationResult
from tests.fakes import FakeCipher, FakeGitLabClient, MemoryUnitOfWork


def test_candidate_does_not_mutate_saved_metadata_and_saved_failure_preserves_success():
    now = datetime(2026, 9, 28, tzinfo=UTC); identifier = uuid4(); uow = MemoryUnitOfWork()
    uow.configurations[identifier] = MonitoringConfiguration.create(identifier=identifier, name="A", gitlab_url="https://gitlab.example", now=now)
    SaveGitLabCredential(uow, FakeCipher(), lambda: now).execute(identifier, "saved")
    candidate_client = FakeGitLabClient(ConnectionValidationResult("invalid_credentials", "Rejected."))
    result = ValidateGitLabConnection(uow, FakeCipher(), candidate_client, lambda: now).execute(identifier, "candidate")
    assert result.credential_source == "candidate_token" and uow.credentials[identifier].last_validation_result is None
    success = FakeGitLabClient()
    ValidateGitLabConnection(uow, FakeCipher(), success, lambda: now).execute(identifier)
    failed_at = datetime(2026, 9, 29, tzinfo=UTC)
    failed = FakeGitLabClient(ConnectionValidationResult("timeout", "Timed out."))
    ValidateGitLabConnection(uow, FakeCipher(), failed, lambda: failed_at).execute(identifier)
    assert uow.credentials[identifier].last_successful_validation_at == now
    assert uow.credentials[identifier].last_validation_result == "timeout"
