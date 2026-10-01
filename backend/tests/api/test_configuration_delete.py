from fastapi.testclient import TestClient

from app.api.dependencies import get_uow
from app.api.main import create_app
from tests.fakes import MemoryUnitOfWork


def test_delete_retires_only_the_requested_resource_and_returns_no_body():
    uow = MemoryUnitOfWork()
    app = create_app(); app.dependency_overrides[get_uow] = lambda: uow
    client = TestClient(app)
    created = client.post("/api/v1/monitoring-configurations", json={"name": "Retire me", "gitlab_url": "https://gitlab.example"}).json()
    response = client.delete(f"/api/v1/monitoring-configurations/{created['id']}")
    assert response.status_code == 204 and response.content == b""
    assert uow.configurations[next(iter(uow.configurations))].name == "Retire me"
    assert client.get(f"/api/v1/monitoring-configurations/{created['id']}").status_code == 404
