from fastapi.testclient import TestClient

from app.api.dependencies import get_credential_cipher, get_gitlab_client, get_uow
from app.api.main import create_app
from app.domain.value_objects.connection_validation_result import ConnectionValidationResult
from tests.fakes import FakeCipher, FakeGitLabClient, MemoryUnitOfWork


def test_saved_and_candidate_validation_contracts_are_isolated_and_safe():
    uow = MemoryUnitOfWork(); app = create_app(); fake_client = FakeGitLabClient()
    app.dependency_overrides[get_uow] = lambda: uow; app.dependency_overrides[get_credential_cipher] = FakeCipher; app.dependency_overrides[get_gitlab_client] = lambda: fake_client
    client = TestClient(app); identifier = client.post("/api/v1/monitoring-configurations", json={"name": "A", "gitlab_url": "https://gitlab.example"}).json()["id"]
    root = f"/api/v1/monitoring-configurations/{identifier}/gitlab-connection"
    assert client.post(f"{root}/validate", json={}).status_code == 409
    candidate = client.post(f"{root}/validate", json={"token": "candidate"})
    assert candidate.status_code == 200 and candidate.json()["credential_source"] == "candidate_token"
    assert client.get(root).json()["credential_configured"] is False
    client.put(f"{root}/credential", json={"token": "saved"})
    saved = client.post(f"{root}/validate", json={})
    assert saved.status_code == 200 and saved.json()["state"] == "validated"
    assert all(word not in saved.text for word in ("candidate-token-value", "saved-token-value", "revision", "fingerprint", "encrypted"))
