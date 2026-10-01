from fastapi.testclient import TestClient

from app.api.dependencies import get_credential_cipher, get_uow
from app.api.main import create_app
from tests.fakes import FakeCipher, MemoryUnitOfWork


def client_with_configuration():
    uow = MemoryUnitOfWork(); app = create_app(); app.dependency_overrides[get_uow] = lambda: uow; app.dependency_overrides[get_credential_cipher] = FakeCipher
    client = TestClient(app); created = client.post("/api/v1/monitoring-configurations", json={"name": "A", "gitlab_url": "https://gitlab.example"}).json()
    return client, uow, created


def test_credential_contract_rejects_invalid_values_without_mutation_or_echo():
    client, uow, created = client_with_configuration(); path = f"/api/v1/monitoring-configurations/{created['id']}/gitlab-connection/credential"
    assert client.put(path, json={"token": "x" * 2048}).status_code == 200
    before = uow.credentials.copy()
    for payload in [{}, {"token": ""}, {"token": "   "}, {"token": "é" * 1025}]:
        response = client.put(path, json=payload)
        assert response.status_code == 422 and "é" not in response.text and uow.credentials == before


def test_status_never_exposes_secret_or_internal_metadata_and_remove_is_idempotent():
    client, _, created = client_with_configuration(); root = f"/api/v1/monitoring-configurations/{created['id']}/gitlab-connection"
    secret = "sentinel-super-secret"; assert client.put(f"{root}/credential", json={"token": secret}).status_code == 200
    status = client.get(root); assert status.status_code == 200
    assert secret not in status.text and "encrypted" not in status.text and "revision" not in status.text and "fingerprint" not in status.text
    assert client.delete(f"{root}/credential").status_code == 204
    assert client.delete(f"{root}/credential").status_code == 204
