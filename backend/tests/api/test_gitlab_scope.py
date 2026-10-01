from fastapi.testclient import TestClient
from datetime import UTC, datetime
from dataclasses import replace
from uuid import UUID, uuid4

from app.api.dependencies import get_credential_cipher, get_gitlab_client, get_uow
from app.api.main import create_app
from app.domain.entities.mining_scope import MiningScope, SelectedGitLabGroup
from app.domain.value_objects.gitlab_hierarchy_node import GitLabHierarchyNode
from tests.fakes import FakeCipher, FakeGitLabClient, MemoryUnitOfWork


def _client(with_credential=True):
    uow = MemoryUnitOfWork(); app = create_app(); provider = FakeGitLabClient()
    app.dependency_overrides[get_uow] = lambda: uow
    app.dependency_overrides[get_credential_cipher] = FakeCipher
    app.dependency_overrides[get_gitlab_client] = lambda: provider
    client = TestClient(app)
    created = client.post("/api/v1/monitoring-configurations", json={
        "name": "Scope API", "gitlab_url": "https://gitlab.example"}).json()
    if with_credential:
        client.put(f"/api/v1/monitoring-configurations/{created['id']}/gitlab-connection/credential",
                   json={"token": "api-secret"})
    return client, provider, created, uow


def test_hierarchy_routes_are_lazy_normalized_and_secret_safe(caplog):
    client, provider, configuration, _ = _client()
    provider.root_result = provider.discovery_result([
        GitLabHierarchyNode(10, "group", "Root", "root", None, True)])
    provider.children = {10: provider.discovery_result([
        GitLabHierarchyNode(11, "repository", "Project", "root/project", 10, False)])}
    root = f"/api/v1/monitoring-configurations/{configuration['id']}/gitlab-scope"
    response = client.get(f"{root}/root")
    assert response.status_code == 200 and response.json()["nodes"][0]["id"] == 10
    children = client.get(f"{root}/groups/10/children")
    assert children.status_code == 200 and children.json()["nodes"][0]["type"] == "repository"
    assert [call[0] for call in provider.calls if isinstance(call[0], str)] == ["root", "children"]
    assert all(secret not in response.text + children.text for secret in ("api-secret", "encrypted", "fingerprint", "revision"))
    assert all(secret not in caplog.text for secret in ("api-secret", "encrypted", "fingerprint", "revision"))


def test_scope_read_replace_empty_scope_and_preconditions():
    client, provider, configuration, _ = _client()
    root = f"/api/v1/monitoring-configurations/{configuration['id']}/gitlab-scope"
    empty = client.get(root)
    assert empty.status_code == 200 and empty.headers["etag"] == '"0"'
    assert empty.json() == {"groups": [], "repositories": [], "stale": False}
    assert client.put(root, json={"groups": [], "repositories": []}).status_code == 428

    provider.groups = {10: provider.discovery_result([
        GitLabHierarchyNode(10, "group", "Platform", "engineering/platform", 1, True)])}
    saved = client.put(root, headers={"If-Match": '"0"'}, json={"groups": [{"gitlab_id": 10}], "repositories": []})
    assert saved.status_code == 200 and saved.headers["etag"] == '"1"'
    assert saved.json()["groups"][0]["name"] == "Platform"
    stale = client.put(root, headers={"If-Match": '"0"'}, json={"groups": [], "repositories": []})
    assert stale.status_code == 412
    cleared = client.put(root, headers={"If-Match": '"1"'}, json={"groups": [], "repositories": []})
    assert cleared.status_code == 200 and cleared.json()["groups"] == []
    assert client.get(f"/api/v1/monitoring-configurations/{configuration['id']}").json()["enabled"] is False


def test_saved_scope_can_be_cleared_without_a_credential():
    client, _, configuration, _ = _client(with_credential=False)
    root = f"/api/v1/monitoring-configurations/{configuration['id']}/gitlab-scope"
    saved = client.put(root, headers={"If-Match": '"0"'}, json={"groups": [], "repositories": []})
    assert saved.status_code == 200 and saved.headers["etag"] == '"1"'
    assert client.get(root).json()["groups"] == []


def test_scope_request_rejects_duplicate_ids_and_never_returns_internal_metadata():
    client, provider, configuration, _ = _client()
    provider.groups = {10: provider.discovery_result([
        GitLabHierarchyNode(10, "group", "Platform", "platform", None, True)])}
    root = f"/api/v1/monitoring-configurations/{configuration['id']}/gitlab-scope"
    duplicate = client.put(root, headers={"If-Match": '"0"'}, json={
        "groups": [{"gitlab_id": 10}, {"gitlab_id": 10}], "repositories": []})
    assert duplicate.status_code == 422
    body = client.get(root)
    assert body.status_code == 200
    assert all(word not in body.text for word in ("fingerprint", "instance_fingerprint", "credential_revision", "encrypted_token"))


def test_discovery_without_credential_is_controlled_and_stale_ids_are_never_queried():
    client, provider, configuration, _ = _client(with_credential=False)
    root = f"/api/v1/monitoring-configurations/{configuration['id']}/gitlab-scope"
    missing = client.get(f"{root}/root")
    assert missing.status_code == 409
    assert provider.calls == []

    scoped_client, scoped_provider, scoped_configuration, scoped_uow = _client()
    identifier = UUID(scoped_configuration["id"])
    now = datetime.now(UTC)
    stale_group = SelectedGitLabGroup(uuid4(), "b" * 64, 10, "Old", "old/group", None, now)
    scoped_uow.scopes[identifier] = MiningScope(identifier, 1, now, (stale_group,), ())
    scoped_root = f"/api/v1/monitoring-configurations/{scoped_configuration['id']}/gitlab-scope"
    read = scoped_client.get(scoped_root)
    assert read.status_code == 200
    assert read.json()["groups"][0]["availability"] == "stale"
    assert scoped_provider.calls == []
    assert "b" * 64 not in read.text and "fingerprint" not in read.text


def test_invalid_configured_gitlab_url_returns_safe_validation_problem():
    client, provider, configuration, uow = _client()
    identifier = UUID(configuration["id"])
    current = uow.configuration_repository.get_active(identifier)
    uow.configurations[identifier] = replace(current, gitlab_url="ftp://invalid.example")
    provider.root_result = provider.discovery_result(outcome="invalid_url")

    response = client.get(f"/api/v1/monitoring-configurations/{identifier}/gitlab-scope/root")
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "gitlab_url"
    assert "api-secret" not in response.text and "ftp://invalid.example" not in response.text
