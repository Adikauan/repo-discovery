from datetime import UTC, datetime

from app.application.use_cases.validate_gitlab_candidate import ValidateGitLabCandidate
from app.domain.value_objects.connection_validation_result import ConnectionValidationResult
from tests.fakes import FakeGitLabClient


def test_candidate_validation_normalizes_url_and_returns_only_safe_result():
    now = datetime(2026, 9, 30, tzinfo=UTC)
    client = FakeGitLabClient()

    result = ValidateGitLabCandidate(client, lambda: now).execute(
        " https://gitlab.example.com/ ", "candidate-secret")

    assert result.state == "validated"
    assert result.result == "success"
    assert result.message == "GitLab connection validated."
    assert result.checked_at == now
    assert client.calls == [("https://gitlab.example.com/", "candidate-secret")]


def test_candidate_validation_never_propagates_provider_message():
    secret = "candidate-secret"
    client = FakeGitLabClient(ConnectionValidationResult("invalid_credentials", secret))

    result = ValidateGitLabCandidate(client).execute("https://gitlab.example.com", secret)

    assert result.state == "failed"
    assert result.message == "GitLab rejected the credential."
    assert secret not in result.message
