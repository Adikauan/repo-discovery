from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.use_cases.get_gitlab_scope_tree import GetGitLabScopeTree
from app.application.use_cases.get_mining_scope import GetMiningScope
from app.application.use_cases.replace_mining_scope import ReplaceMiningScope
from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
from app.domain.entities.mining_scope import (EffectiveRepositoryCandidate, MiningScope,
                                               SelectedGitLabGroup, SelectedGitLabRepository,
                                               effective_repositories)
from app.domain.errors import ConflictError, StaleConfigurationError
from app.domain.monitoring_configuration import MonitoringConfiguration
from app.domain.ports.gitlab_credential_repository import CredentialSnapshot
from app.domain.value_objects.gitlab_hierarchy_node import GitLabHierarchyNode
from tests.fakes import FakeCipher, FakeGitLabClient, MemoryUnitOfWork


NOW = datetime(2026, 9, 28, tzinfo=UTC)


def _configuration(identifier):
    return MonitoringConfiguration.create(identifier=identifier, name="Scope", gitlab_url="https://gitlab.example",
                                          now=NOW)


def _credential(identifier, value="secret"):
    return CredentialSnapshot(identifier, b"encrypted:" + value.encode(), 1, None, None, None, None)


def test_effective_coverage_deduplicates_explicit_and_group_rules_by_instance():
    fingerprint = "a" * 64
    stale_fingerprint = "b" * 64
    group = SelectedGitLabGroup(uuid4(), fingerprint, 10, "Platform", "eng/platform", 1, NOW)
    explicit = SelectedGitLabRepository(uuid4(), fingerprint, 100, "API", "eng/platform/api", 10, NOW)
    scope = MiningScope(uuid4(), 1, NOW, (group,), (explicit,))
    candidate = EffectiveRepositoryCandidate(fingerprint, 100, frozenset({1, 10}))
    group_only = EffectiveRepositoryCandidate(fingerprint, 101, frozenset({1, 10}))
    other_origin = EffectiveRepositoryCandidate(stale_fingerprint, 100, frozenset({10}))
    result = effective_repositories([candidate, candidate, group_only, other_origin], scope, fingerprint)
    assert [(item.instance_fingerprint, item.project_id) for item in result] == [(fingerprint, 100), (fingerprint, 101)]


def test_tree_discovery_fetches_root_then_only_the_requested_group(utc_clock):
    identifier = uuid4(); uow = MemoryUnitOfWork()
    uow.configuration_repository.add(_configuration(identifier)); uow.credentials[identifier] = _credential(identifier)
    client = FakeGitLabClient()
    client.children = {}
    child = GitLabHierarchyNode(20, "group", "Child", "root/child", 10, True)
    client.root_result = client.discovery_result([GitLabHierarchyNode(10, "group", "Root", "root", None, True)])
    client.children = {10: client.discovery_result([child])}
    tree = GetGitLabScopeTree(uow, FakeCipher(), client)
    assert [node.id for node in tree.execute(identifier)] == [10]
    assert [node.id for node in tree.execute(identifier, 10)] == [20]
    assert [call[0] for call in client.calls if isinstance(call[0], str)] == ["root", "children"]
    assert client.calls[-1][-1] == 10


def test_thousand_entity_hierarchy_stays_on_requested_branch(utc_clock):
    identifier = uuid4(); uow = MemoryUnitOfWork()
    uow.configuration_repository.add(_configuration(identifier)); uow.credentials[identifier] = _credential(identifier)
    client = FakeGitLabClient()
    client.children = {}
    roots = [GitLabHierarchyNode(100 + index, "group", f"Root {index}", f"root-{index}", None, True)
             for index in range(10)]
    client.root_result = client.discovery_result(roots)
    entity_count = len(roots)
    for root in roots:
        subgroups = [GitLabHierarchyNode(root.id * 10 + index, "group", f"Subgroup {index}",
                     f"{root.full_path}/subgroup-{index}", root.id, True) for index in range(9)]
        direct_project = GitLabHierarchyNode(root.id * 100, "repository", "Direct", f"{root.full_path}/direct",
                                             root.id, False)
        client.children[root.id] = client.discovery_result([*subgroups, direct_project])
        entity_count += len(subgroups) + 1
        for subgroup in subgroups:
            projects = [GitLabHierarchyNode(subgroup.id * 100 + project, "repository", f"Project {project}",
                        f"{subgroup.full_path}/project-{project}", subgroup.id, False) for project in range(10)]
            client.children[subgroup.id] = client.discovery_result(projects)
            entity_count += len(projects)
    assert entity_count == 1010

    tree = GetGitLabScopeTree(uow, FakeCipher(), client)
    assert len(tree.execute(identifier)) == 10
    assert len(tree.execute(identifier, roots[0].id)) == 10
    discovery_calls = [call for call in client.calls if call[0] in {"root", "children"}]
    assert discovery_calls == [("root", "https://gitlab.example", "secret"),
                               ("children", "https://gitlab.example", "secret", roots[0].id)]


def test_tree_discovery_requires_credential_and_normalizes_connection_changes():
    identifier = uuid4(); uow = MemoryUnitOfWork()
    uow.configuration_repository.add(_configuration(identifier))
    with pytest.raises(ConflictError):
        GetGitLabScopeTree(uow, FakeCipher(), FakeGitLabClient()).execute(identifier)

    uow.credentials[identifier] = _credential(identifier)
    client = FakeGitLabClient()
    client.root_result = client.discovery_result(outcome="timeout")
    from app.domain.errors import GitLabDiscoveryError
    with pytest.raises(GitLabDiscoveryError) as error:
        GetGitLabScopeTree(uow, FakeCipher(), client).execute(identifier)
    assert error.value.outcome == "timeout"


def test_reconciliation_preserves_stale_and_unavailable_entries(utc_clock):
    identifier = uuid4(); uow = MemoryUnitOfWork()
    uow.configuration_repository.add(_configuration(identifier)); uow.credentials[identifier] = _credential(identifier)
    current = normalized_url_fingerprint("https://gitlab.example")
    group = SelectedGitLabGroup(uuid4(), current, 10, "Old", "old/path", None, NOW)
    stale = SelectedGitLabRepository(uuid4(), "b" * 64, 100, "Old repo", "old/repo", 10, NOW)
    uow.scopes[identifier] = MiningScope(identifier, 1, NOW, (group,), (stale,))
    client = FakeGitLabClient()
    client.groups = {10: client.discovery_result(outcome="forbidden")}
    scope, status = GetMiningScope(uow, FakeCipher(), client, utc_clock).execute(identifier)
    assert scope.groups[0].name == "Old"
    assert status[group.selection_id] == "unavailable"
    assert status[stale.selection_id] == "stale"
    assert not any(call[0] == "project" for call in client.calls)


def test_credential_replacement_and_removal_preserve_saved_scope_until_explicit_clear(utc_clock):
    identifier = uuid4(); uow = MemoryUnitOfWork()
    configuration = _configuration(identifier)
    uow.configuration_repository.add(configuration)
    old_credential = _credential(identifier, "old-token")
    uow.credentials[identifier] = old_credential
    fingerprint = normalized_url_fingerprint(configuration.gitlab_url)
    group = SelectedGitLabGroup(uuid4(), fingerprint, 10, "Platform", "engineering/platform", None, NOW)
    uow.scopes[identifier] = MiningScope(identifier, 1, NOW, (group,), ())
    assert uow.credential_repository.replace(identifier, b"encrypted:new-token", 1, NOW)

    client = FakeGitLabClient()
    client.groups = {10: client.discovery_result([
        GitLabHierarchyNode(10, "group", "Platform renamed", "engineering/platform-renamed", None, True)])}
    refreshed, availability = GetMiningScope(uow, FakeCipher(), client, utc_clock).execute(identifier)
    assert refreshed.groups[0].selection_id == group.selection_id
    assert refreshed.groups[0].name == "Platform renamed"
    assert availability[group.selection_id] == "available"
    assert uow.credential_repository.get(identifier).revision == 2

    uow.credential_repository.remove(identifier)
    unresolved, status = GetMiningScope(uow, FakeCipher(), client, utc_clock).execute(identifier)
    assert unresolved.groups[0].selection_id == group.selection_id
    assert status[group.selection_id] == "unresolved"
    call_count = len(client.calls)

    current = uow.configuration_repository.get_active(identifier)
    updated = current.update(name=current.name, description=current.description,
                             gitlab_url="https://gitlab.other", enabled=current.enabled, now=utc_clock())
    assert uow.configuration_repository.update(updated, current.revision)
    stale, status = GetMiningScope(uow, FakeCipher(), client, utc_clock).execute(identifier)
    assert stale.groups[0].selection_id == group.selection_id
    assert status[group.selection_id] == "stale"
    assert len(client.calls) == call_count

    cleared = ReplaceMiningScope(uow, FakeCipher(), client, utc_clock).execute(identifier, [], [], stale.version)
    assert cleared.groups == () and cleared.repositories == ()


def test_replacement_allows_empty_scope_without_credential_and_enforces_scope_cas(utc_clock):
    identifier = uuid4(); uow = MemoryUnitOfWork()
    uow.configuration_repository.add(_configuration(identifier))
    use_case = ReplaceMiningScope(uow, FakeCipher(), FakeGitLabClient(), utc_clock)
    saved = use_case.execute(identifier, [], [], 0)
    assert saved.version == 1 and saved.groups == () and saved.repositories == ()
    with pytest.raises(StaleConfigurationError):
        use_case.execute(identifier, [], [], 0)


def test_replacement_round_trips_stale_rules_and_resolves_only_new_rules(utc_clock):
    identifier = uuid4(); uow = MemoryUnitOfWork()
    uow.configuration_repository.add(_configuration(identifier)); uow.credentials[identifier] = _credential(identifier)
    old = SelectedGitLabGroup(uuid4(), "b" * 64, 9, "Old", "old", None, NOW)
    uow.scopes[identifier] = MiningScope(identifier, 1, NOW, (old,), ())
    client = FakeGitLabClient()
    node = GitLabHierarchyNode(12, "repository", "New", "team/new", 10, False)
    client.projects = {12: client.discovery_result([node])}
    saved = ReplaceMiningScope(uow, FakeCipher(), client, utc_clock).execute(
        identifier, [{"selection_id": old.selection_id, "gitlab_id": 9}], [{"gitlab_id": 12}], 1)
    assert saved.version == 2
    assert saved.groups[0].instance_fingerprint == "b" * 64
    assert saved.repositories[0].instance_fingerprint == normalized_url_fingerprint("https://gitlab.example")
    assert saved.repositories[0].full_path == "team/new"
    assert sum(1 for call in client.calls if call[0] == "project") == 1
