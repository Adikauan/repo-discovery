from fastapi.testclient import TestClient
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.api.dependencies import get_uow
from app.api.main import create_app
from tests.fakes import MemoryUnitOfWork


def test_update_requires_etag_and_rejects_stale_version():
    uow = MemoryUnitOfWork()
    app = create_app(); app.dependency_overrides[get_uow] = lambda: uow
    client = TestClient(app)
    created = client.post("/api/v1/monitoring-configurations", json={"name": "Versioned", "gitlab_url": "https://gitlab.example"}).json()
    path = f"/api/v1/monitoring-configurations/{created['id']}"
    payload = {"name": "Edited", "description": None, "gitlab_url": created["gitlab_url"], "enabled": True}
    assert client.put(path, json=payload).status_code == 428
    saved = client.put(path, headers={"If-Match": '"1"'}, json=payload)
    assert saved.status_code == 200 and saved.headers["etag"] == '"2"'
    assert client.put(path, headers={"If-Match": '"1"'}, json={**payload, "name": "Stale"}).status_code == 412


def test_update_validation_noop_and_unavailable_resource():
    uow = MemoryUnitOfWork()
    app = create_app(); app.dependency_overrides[get_uow] = lambda: uow
    client = TestClient(app)
    created = client.post("/api/v1/monitoring-configurations", json={"name": "Stable", "gitlab_url": "https://gitlab.example"}).json()
    path = f"/api/v1/monitoring-configurations/{created['id']}"
    original = {"name": created["name"], "description": created["description"], "gitlab_url": created["gitlab_url"], "enabled": created["enabled"]}
    unchanged = client.put(path, headers={"If-Match": '"1"'}, json=original)
    assert unchanged.status_code == 200 and unchanged.json()["version"] == "1"
    invalid = client.put(path, headers={"If-Match": '"1"'}, json={**original, "gitlab_url": "ftp://invalid.example"})
    assert invalid.status_code == 422
    assert client.get(path).json()["gitlab_url"] == created["gitlab_url"]
    assert client.put("/api/v1/monitoring-configurations/00000000-0000-0000-0000-000000000001",
                      headers={"If-Match": '"1"'}, json=original).status_code == 404


def test_enable_does_not_require_obsolete_scope_branch_configuration():
    uow = MemoryUnitOfWork(); app = create_app(scheduler_enabled=False)
    app.dependency_overrides[get_uow] = lambda: uow
    client = TestClient(app)
    created = client.post("/api/v1/monitoring-configurations", json={
        "name": "Policy target", "gitlab_url": "https://gitlab.example"}).json()
    path = f"/api/v1/monitoring-configurations/{created['id']}"
    payload = {"name": created["name"], "description": None, "gitlab_url": created["gitlab_url"], "enabled": True}
    enabled = client.put(path, headers={"If-Match": '"1"'}, json=payload)
    assert enabled.status_code == 200 and enabled.json()["enabled"] is True


def test_allowed_author_update_uses_etag_and_preserves_values_when_omitted():
    app = create_app(scheduler_enabled=False); uow = MemoryUnitOfWork()
    app.dependency_overrides[get_uow] = lambda: uow
    client = TestClient(app)
    created = client.post("/api/v1/monitoring-configurations", json={"name": "Allowed", "gitlab_url": "https://gitlab.example",
        "allowed_author_emails": [" Alice@example.com "]}).json()
    path = f"/api/v1/monitoring-configurations/{created['id']}"
    changed = {"name": created["name"], "description": None, "gitlab_url": created["gitlab_url"], "enabled": False,
               "allowed_author_emails": ["bob@example.com"]}
    response = client.put(path, headers={"If-Match": '"1"'}, json=changed)
    assert response.status_code == 200 and response.json()["allowed_author_emails"] == ["bob@example.com"]
    response = client.put(path, headers={"If-Match": '"2"'}, json={key: value for key, value in changed.items() if key != "allowed_author_emails"})
    assert response.status_code == 200 and response.json()["allowed_author_emails"] == ["bob@example.com"]
