from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import (get_credential_cipher, get_gitlab_client,
    get_gitlab_repository_client, get_uow)
from app.api.main import create_app
from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
from app.domain.author_policy import AuthorPolicy
from app.domain.entities.mining_scope import MiningScope, SelectedGitLabGroup, SelectedGitLabRepository
from app.infrastructure.gitlab.http_gitlab_repository_client import GitLabBranch
from tests.fakes import FakeCipher, FakeGitLabClient, MemoryUnitOfWork


class BranchProvider:
    def __init__(self): self.calls = []
    def get_project_scope(self, url, token, project_id):
        return type("Project", (), {"id": project_id, "name": "API", "full_path": "sequor/backend/api"})()
    def get_group(self, url, token, group_id): return object()
    def group_children(self, url, token, group_id): return (), ()
    def list_branches(self, url, token, project_id):
        self.calls.append((url, token, project_id))
        return (GitLabBranch("main", "a" * 40, True), GitLabBranch("release/one", "b" * 40, False))


def setup():
    uow = MemoryUnitOfWork(); app = create_app(); provider = BranchProvider()
    app.dependency_overrides[get_uow] = lambda: uow
    app.dependency_overrides[get_credential_cipher] = FakeCipher
    app.dependency_overrides[get_gitlab_client] = lambda: FakeGitLabClient()
    app.dependency_overrides[get_gitlab_repository_client] = lambda: provider
    client = TestClient(app)
    configuration = client.post("/api/v1/monitoring-configurations", json={
        "name": "Policy API", "gitlab_url": "https://gitlab.example",
        "allowed_author_emails": ["legacy@example.com"]}).json()
    client.put(f"/api/v1/monitoring-configurations/{configuration['id']}/gitlab-connection/credential",
        json={"token": "policy-secret"})
    identifier = UUID(configuration["id"])
    fingerprint = normalized_url_fingerprint("https://gitlab.example")
    credential = uow.credential_repository.get(identifier)
    uow.credential_repository.update_validation(identifier, credential.revision, fingerprint,
        "success", datetime(2026, 9, 30, tzinfo=UTC))
    now = datetime(2026, 9, 30, tzinfo=UTC)
    uow.scopes[identifier] = MiningScope(identifier, 1, now,
        groups=(SelectedGitLabGroup(uuid4(), fingerprint, 12, "Backend", "sequor/backend", 1, now),),
        repositories=(SelectedGitLabRepository(uuid4(), fingerprint, 42, "API", "sequor/backend/api", 12, now),))
    root = f"/api/v1/monitoring-configurations/{identifier}/author-policies"
    return client, provider, configuration, uow, root


def test_group_policy_is_rejected_and_repository_branch_policy_is_normalized_and_cas_protected():
    client, provider, config, _, root = setup()
    group = client.put(f"{root}/groups/12", headers={"If-Match": '"1"'}, json={
        "allowed_author_emails": [" Alice@example.com ", "alice@example.com"]})
    assert group.status_code == 422
    branch = client.put(f"{root}/repositories/42/branches", headers={"If-Match": '"1"'}, json={
        "branch": "release/one", "allowed_author_emails": []})
    assert branch.status_code == 200, branch.json()
    assert branch.json()["allowed_author_emails"] == []
    assert provider.calls == [("https://gitlab.example", "policy-secret", 42)]
    stale = client.put(f"{root}/repositories/42/branches", headers={"If-Match": '"1"'}, json={
        "branch": "release/one", "allowed_author_emails": []})
    assert stale.status_code == 412
    state = client.get(root).json()
    assert {item["scope_type"] for item in state["policies"]} == {"repository_branch"}
    assert state["repositories"][0]["status"] == "configured"
    assert state["legacy_fallback"] == {"active": True, "allowed_author_emails": ["legacy@example.com"]}
    assert "policy-secret" not in client.get(root).text


def test_unselected_repository_never_causes_branch_provider_call():
    client, provider, config, _, root = setup()
    result = client.get(f"{root}/repositories/999/branches")
    assert result.status_code == 422
    assert result.json()["code"] == "scope_repository_not_selected"
    assert provider.calls == []


def test_branch_discovery_uses_server_credentials_and_scoped_repository():
    client, provider, config, _, root = setup()
    result = client.get(f"{root}/repositories/42/branches")
    assert result.status_code == 200, result.json()
    assert [item["name"] for item in result.json()["items"]] == ["main", "release/one"]
    assert provider.calls == [("https://gitlab.example", "policy-secret", 42)]
    assert "policy-secret" not in result.text


def test_policy_read_resolves_group_descendants_as_policy_repositories():
    client, provider, _, uow, root = setup()
    dynamic = type("Project", (), {"id": 43, "name": "Worker", "full_path": "sequor/backend/worker"})()
    provider.group_children = lambda url, token, group_id: ((), (dynamic,))
    result = client.get(root)
    assert result.status_code == 200
    repositories = {item["gitlab_project_id"]: item for item in result.json()["repositories"]}
    assert repositories[43] == {"gitlab_project_id": 43, "name": "Worker",
        "full_path": "sequor/backend/worker", "source": "group", "status": "policy_required"}
    assert repositories[42]["source"] == "direct"
    discovered = client.get(f"{root}/repositories/43/branches")
    assert discovered.status_code == 200
    assert provider.calls[-1] == ("https://gitlab.example", "policy-secret", 43)


def test_explicit_one_way_legacy_transition_retains_global_list_and_stales_old_revision():
    client, _, config, uow, root = setup()
    switched = client.post(f"{root}/migration", headers={"If-Match": '"1"'}, json={})
    assert switched.status_code == 200 and switched.json()["mode"] == "scope_aware"
    assert switched.json()["legacy_fallback"] == {"active": False, "allowed_author_emails": ["legacy@example.com"]}
    current = uow.configuration_repository.get_active(UUID(config["id"]))
    assert current.allowed_author_emails == ("legacy@example.com",)
    stale = client.put(f"{root}/groups/12", headers={"If-Match": '"1"'}, json={"allowed_author_emails": []})
    assert stale.status_code == 412
