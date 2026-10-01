from fastapi.testclient import TestClient
import pytest

from app.api.dependencies import get_gitlab_client, get_uow
from app.api.main import create_app
from app.domain.value_objects.connection_validation_result import ConnectionValidationResult
from tests.fakes import FakeGitLabClient


def test_candidate_validation_is_transient_and_does_not_return_token():
    secret = "candidate-secret-value"
    gitlab = FakeGitLabClient()
    app = create_app(scheduler_enabled=False)
    app.dependency_overrides[get_gitlab_client] = lambda: gitlab

    response = TestClient(app, raise_server_exceptions=False).post("/api/v1/gitlab-connections/validate-candidate", json={
        "gitlab_url": "https://gitlab.example.com", "token": secret,
    })

    assert response.status_code == 200
    assert response.json()["state"] == "validated"
    assert response.json()["result"] == "success"
    assert secret not in response.text
    assert gitlab.calls == [("https://gitlab.example.com", secret)]


def test_candidate_validation_failure_is_normalized_and_does_not_echo_token():
    secret = "candidate-secret-value"
    gitlab = FakeGitLabClient(ConnectionValidationResult("invalid_credentials", secret))
    app = create_app(scheduler_enabled=False)
    app.dependency_overrides[get_gitlab_client] = lambda: gitlab

    response = TestClient(app, raise_server_exceptions=False).post("/api/v1/gitlab-connections/validate-candidate", json={
        "gitlab_url": "https://gitlab.example.com", "token": secret,
    })

    assert response.status_code == 200
    assert response.json()["state"] == "failed"
    assert response.json()["message"] == "GitLab rejected the credential."
    assert secret not in response.text


def test_candidate_validation_rejects_invalid_url_without_calling_gitlab():
    gitlab = FakeGitLabClient()
    app = create_app(scheduler_enabled=False)
    app.dependency_overrides[get_gitlab_client] = lambda: gitlab

    response = TestClient(app).post("/api/v1/gitlab-connections/validate-candidate", json={
        "gitlab_url": "file:///tmp/token", "token": "secret",
    })

    assert response.status_code == 422
    assert gitlab.calls == []


def test_candidate_provider_failure_does_not_echo_or_log_secret_and_never_opens_uow(caplog):
    secret = "candidate-secret-value"

    class FailingGitLabClient:
        def validate(self, gitlab_url: str, token: str):
            raise RuntimeError(f"Authorization header contained {token}")

    def forbidden_uow():
        pytest.fail("transient validation must not access configuration persistence")

    app = create_app(scheduler_enabled=False)
    app.dependency_overrides[get_gitlab_client] = FailingGitLabClient
    app.dependency_overrides[get_uow] = forbidden_uow
    response = TestClient(app, raise_server_exceptions=False).post("/api/v1/gitlab-connections/validate-candidate", json={
        "gitlab_url": "https://gitlab.example.com", "token": secret,
    })

    assert response.status_code == 503
    assert secret not in response.text
    assert secret not in caplog.text
