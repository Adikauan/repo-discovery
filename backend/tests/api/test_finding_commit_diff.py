from dataclasses import replace
from uuid import uuid4

from app.api.dependencies import get_credential_cipher, get_gitlab_repository_client
from app.api.dependencies import get_uow
from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
from app.domain.entities.finding import Finding
from app.domain.value_objects.commit_diff import CommitDiffFile, CommitDiffProviderResult
from tests.api.test_findings import seeded


class Provider:
    def __init__(self): self.calls = []
    def get_commit_diff(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        raise AssertionError("credential validation should fail before provider access")


class SuccessfulProvider:
    def __init__(self): self.calls = []
    def get_commit_diff(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return CommitDiffProviderResult((CommitDiffFile("old", "new", "renamed", "-x\n+y", True),), "complete")


def test_diff_endpoint_uses_finding_id_only_and_returns_safe_missing_credential_problem():
    client, _, _, finding = seeded()
    provider = Provider()
    client.app.dependency_overrides[get_gitlab_repository_client] = lambda: provider
    client.app.dependency_overrides[get_credential_cipher] = lambda: object()
    with client:
        response = client.get(f"/api/v1/findings/{finding.id}/diff")
        rejected_query = client.get(f"/api/v1/findings/{finding.id}/diff?commitHash=other")
        rejected_body = client.request("GET", f"/api/v1/findings/{finding.id}/diff", json={"commitHash": "other"})
    assert response.status_code == 503
    assert response.json()["code"] == "gitlab_credential_missing"
    assert "PRIVATE-TOKEN" not in response.text and "encrypted" not in response.text
    assert provider.calls == []
    assert rejected_query.status_code == 400
    assert rejected_body.status_code == 400


def test_diff_endpoint_returns_normalized_not_found_for_missing_finding():
    client, _, _, _ = seeded()
    with client:
        response = client.get(f"/api/v1/findings/{uuid4()}/diff")
    assert response.status_code == 404
    assert response.json()["code"] == "finding_not_found"


def test_diff_endpoint_refuses_to_reinterpret_historical_project_on_another_gitlab_instance():
    client, execution, _, finding = seeded()
    uow = client.app.dependency_overrides[get_uow]()
    config = uow.configuration_repository.get(execution.monitoring_configuration_id)
    uow.configurations[config.id] = replace(config, gitlab_url="https://other-gitlab.example.net")
    provider = Provider()
    client.app.dependency_overrides[get_gitlab_repository_client] = lambda: provider
    with client:
        response = client.get(f"/api/v1/findings/{finding.id}/diff")
    assert response.status_code == 409
    assert response.json()["code"] == "gitlab_instance_mismatch"
    assert provider.calls == []


def test_diff_endpoint_returns_normalized_safe_success_contract():
    client, execution, repository, finding = seeded()
    uow = client.app.dependency_overrides[get_uow]()
    configuration = uow.configuration_repository.get(execution.monitoring_configuration_id)
    fingerprint = normalized_url_fingerprint(execution.snapshot.gitlab_url)
    assert uow.credential_repository.replace(configuration.id, b"encrypted-token", None, execution.created_at)
    assert uow.credential_repository.update_validation(configuration.id, 1, fingerprint, "success", execution.created_at)
    provider = SuccessfulProvider()
    client.app.dependency_overrides[get_gitlab_repository_client] = lambda: provider
    client.app.dependency_overrides[get_credential_cipher] = lambda: type("Cipher", (), {"decrypt": lambda self, _: "server-secret"})()
    with client:
        response = client.get(f"/api/v1/findings/{finding.id}/diff")
    assert response.status_code == 200
    body = response.json()
    assert body["findingId"] == str(finding.id) and body["commitHash"] == finding.commit_hash
    assert body["filesCompleteness"] == "complete"
    assert body["files"][0]["textDiffAvailable"] is True
    assert body["files"][0]["changeType"] == "renamed"
    assert "server-secret" not in response.text and "encrypted-token" not in response.text
    assert provider.calls[0][0][2:] == (repository.gitlab_project_id, finding.commit_hash)
