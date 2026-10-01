import httpx
import pytest

from app.domain.value_objects.mining_failure import MiningFailure
from app.infrastructure.gitlab.http_gitlab_repository_client import HttpGitLabRepositoryClient


def test_project_metadata_does_not_select_default_branch_and_tree_uses_explicit_target():
    calls = []
    def handler(request):
        calls.append(request.url.path)
        if request.url.path.endswith("/projects/10"):
            return httpx.Response(200, json={"id": 10, "name": "Repo", "path_with_namespace": "team/repo", "default_branch": "trunk"})
        page = request.url.params.get("page")
        if page == "1":
            return httpx.Response(200, json=[{"type": "blob", "path": f"f{i}.py", "size": 8_000_000} for i in range(100)])
        return httpx.Response(200, json=[{"type": "blob", "path": "tail.bin"}])
    client = HttpGitLabRepositoryClient(httpx.Timeout(1), transport=httpx.MockTransport(handler))
    project = client.project("https://gitlab.example.com", "secret", 10)
    tree = client.tree("https://gitlab.example.com", "secret", 10, "quality")
    assert "default_branch" not in project and len(tree) == 101
    assert all(item.size_bytes == 8_000_000 for item in tree[:100])
    assert all("repository/files" not in path for path in calls)


def test_full_page_without_next_header_requests_following_page_and_limits_are_enforced():
    pages = []
    def handler(request):
        page = request.url.params.get("page"); pages.append(page)
        return httpx.Response(200, json=[{"type": "blob", "path": f"f{page}-{i}.txt"} for i in range(100)])
    client = HttpGitLabRepositoryClient(httpx.Timeout(1), transport=httpx.MockTransport(handler), max_tree_entries=150)
    with pytest.raises(MiningFailure) as caught:
        client.tree("https://gitlab.example.com", "token", 4, "main")
    assert caught.value.code == "repository_tree_limit_exceeded"
    assert pages == ["1", "2"]


def test_group_resolution_uses_owned_projects_without_shared_projects():
    requests = []
    def handler(request):
        requests.append(request)
        if request.url.path.endswith("/groups/3/subgroups"):
            return httpx.Response(200, json=[{"id": 4, "name": "child", "full_path": "team/child"}])
        if request.url.path.endswith("/groups/3/projects"):
            return httpx.Response(200, json=[{"id": 10, "name": "owned", "path_with_namespace": "team/owned"}])
        return httpx.Response(404, json={"message": "must not be returned"})
    client = HttpGitLabRepositoryClient(httpx.Timeout(1), transport=httpx.MockTransport(handler))
    groups, projects = client.group_children("https://gitlab.example.com", "secret", 3)
    assert [item.id for item in groups] == [4]
    assert [item.id for item in projects] == [10]
    project_request = next(request for request in requests if request.url.path.endswith("/projects"))
    assert project_request.url.params["include_subgroups"] == "false"
    assert project_request.url.params["with_shared"] == "false"


def test_project_without_default_branch_is_still_valid_metadata():
    def handler(_):
        return httpx.Response(200, json={"id": 10, "name": "Repo", "path_with_namespace": "team/repo", "default_branch": None})
    client = HttpGitLabRepositoryClient(httpx.Timeout(1), transport=httpx.MockTransport(handler))
    project = client.project("https://gitlab.example.com", "token", 10)
    assert project == {"id": 10, "name": "Repo", "full_path": "team/repo"}


def test_branch_discovery_paginates_normalizes_and_keeps_empty_as_empty():
    requested = []
    def handler(request):
        requested.append(request.url.params.get("page"))
        if request.url.params.get("page") == "1":
            return httpx.Response(200, headers={"X-Next-Page": "2"}, json=[
                {"name": "release/one", "default": False, "commit": {"id": "B" * 40}},
            ])
        return httpx.Response(200, json=[
            {"name": "main", "default": True, "commit": {"id": "A" * 40}},
        ])
    client = HttpGitLabRepositoryClient(httpx.Timeout(1), transport=httpx.MockTransport(handler))
    rows = client.list_branches("https://gitlab.example.com", "secret", 10)
    assert requested == ["1", "2"]
    assert [(item.name, item.commit_sha, item.default) for item in rows] == [
        ("main", "a" * 40, True), ("release/one", "b" * 40, False)]


def test_branch_discovery_empty_response():
    client = HttpGitLabRepositoryClient(httpx.Timeout(1), transport=httpx.MockTransport(
        lambda _: httpx.Response(200, json=[])))
    assert client.list_branches("https://gitlab.example.com", "secret", 10) == ()


@pytest.mark.parametrize(("response", "expected"), [
    (httpx.Response(403, text="private provider payload"), "repository_forbidden"),
    (httpx.Response(200, json={"name": "not-a-list"}), "repository_invalid_response"),
])
def test_branch_discovery_normalizes_forbidden_and_malformed_responses(response, expected):
    client = HttpGitLabRepositoryClient(httpx.Timeout(1), transport=httpx.MockTransport(lambda _: response))
    with pytest.raises(MiningFailure) as caught:
        client.list_branches("https://gitlab.example.com", "secret-token", 10)
    assert caught.value.code == expected
    assert "private provider payload" not in str(caught.value)
    assert "secret-token" not in str(caught.value)


def test_branch_discovery_timeout_is_safe():
    def timeout(_): raise httpx.ReadTimeout("token=secret provider details")
    client = HttpGitLabRepositoryClient(httpx.Timeout(1), transport=httpx.MockTransport(timeout))
    with pytest.raises(MiningFailure) as caught:
        client.list_branches("https://gitlab.example.com", "secret-token", 10)
    assert caught.value.code == "repository_timeout"
    assert "secret" not in str(caught.value)


def test_selected_group_and_direct_project_are_validated_against_provider_identity():
    def handler(request):
        if request.url.path.endswith("/groups/3"):
            return httpx.Response(200, json={"id": 3, "name": "Group", "full_path": "team/group"})
        return httpx.Response(200, json={"id": 9, "name": "Repo", "path_with_namespace": "team/group/repo"})
    client = HttpGitLabRepositoryClient(httpx.Timeout(1), transport=httpx.MockTransport(handler))
    assert client.get_group("https://gitlab.example.com", "token", 3).full_path == "team/group"
    assert client.get_project_scope("https://gitlab.example.com", "token", 9).full_path == "team/group/repo"


@pytest.mark.parametrize(("headers", "expected"), [
    ({"X-Total-Pages": "1"}, "complete"), ({"X-Next-Page": "2"}, "truncated"), ({}, "unknown"),
])
def test_commit_diff_maps_change_flags_and_completeness(headers, expected):
    def handler(request):
        assert request.url.path.endswith("/projects/11/repository/commits/" + "a" * 40 + "/diff")
        return httpx.Response(200, headers=headers, json=[
            {"old_path": "old", "new_path": "new", "diff": "+x", "renamed_file": True,
             "new_file": False, "deleted_file": False, "collapsed": False, "too_large": False},
        ])
    client = HttpGitLabRepositoryClient(httpx.Timeout(1), transport=httpx.MockTransport(handler))
    result = client.get_commit_diff("https://gitlab.example.com", "secret", 11, "a" * 40, max_files=1 if expected == "truncated" else 10)
    assert result.files_completeness == expected
    assert result.files[0].change_type == "renamed"
    assert result.files[0].old_path == "old" and result.files[0].new_path == "new"
    assert result.files[0].text_diff_available is True


def test_commit_diff_keeps_binary_like_empty_patch_in_file_list_without_guessing_binary():
    def handler(_):
        return httpx.Response(200, headers={"X-Total-Pages": "1"}, json=[
            {"old_path": "a.bin", "new_path": "a.bin", "diff": "", "new_file": False,
             "deleted_file": False, "renamed_file": False},
        ])
    client = HttpGitLabRepositoryClient(httpx.Timeout(1), transport=httpx.MockTransport(handler))
    result = client.get_commit_diff("https://gitlab.example.com", "secret", 11, "a" * 40, max_files=10)
    assert result.files[0].diff is None
    assert result.files[0].binary is None
    assert result.files[0].text_diff_available is False


@pytest.mark.parametrize(("response", "code"), [
    (httpx.Response(404), "commit_not_found"),
    (httpx.Response(403), "commit_diff_forbidden"),
    (httpx.Response(200, json={"unexpected": "object"}), "commit_diff_invalid_response"),
    (httpx.Response(502, text="provider secret response"), "commit_diff_unavailable"),
])
def test_commit_diff_provider_errors_are_normalized(response, code):
    client = HttpGitLabRepositoryClient(httpx.Timeout(1), transport=httpx.MockTransport(lambda _: response))
    with pytest.raises(Exception) as caught:
        client.get_commit_diff("https://gitlab.example.com", "secret", 11, "a" * 40, max_files=10)
    assert getattr(caught.value, "code", None) == code
    assert "provider secret response" not in str(caught.value)


def test_commit_diff_timeout_has_a_safe_normalized_error():
    def timeout(_): raise httpx.ReadTimeout("secret timeout details")
    client = HttpGitLabRepositoryClient(httpx.Timeout(1), transport=httpx.MockTransport(timeout))
    with pytest.raises(Exception) as caught:
        client.get_commit_diff("https://gitlab.example.com", "secret", 11, "a" * 40, max_files=10)
    assert getattr(caught.value, "code", None) == "commit_diff_timeout"
    assert "secret timeout details" not in str(caught.value)


def test_malformed_tree_entry_is_normalized():
    def handler(_): return httpx.Response(200, json=[{"type": "blob"}])
    client = HttpGitLabRepositoryClient(httpx.Timeout(1), transport=httpx.MockTransport(handler))
    with pytest.raises(MiningFailure) as caught:
        client.tree("https://gitlab.example.com", "token", 9, "main")
    assert caught.value.code == "repository_invalid_response"


def test_commit_head_and_incremental_range_follow_every_page_and_return_oldest_first():
    pages = []
    sha = {"head": "c" * 40, "next": "b" * 40, "checkpoint": "a" * 40}
    def handler(request):
        if request.url.path.endswith("/repository/commits") and request.url.params.get("per_page") == "1":
            return httpx.Response(200, json=[{"id": sha["head"], "author_email": "a@b.test"}])
        page = request.url.params.get("page"); pages.append(page)
        if page == "1":
            return httpx.Response(200, headers={"X-Next-Page": "2"}, json=[
                {"id": sha["head"], "author_email": "z@example.com"},
                {"id": sha["next"], "author_email": "y@example.com"}])
        return httpx.Response(200, json=[{"id": sha["checkpoint"], "author_email": "old@example.com"}])
    client = HttpGitLabRepositoryClient(httpx.Timeout(1), transport=httpx.MockTransport(handler))
    assert client.get_branch_head("https://gitlab.example.com", "token", 5, "trunk").commit_hash == sha["head"]
    result = client.list_commits_after("https://gitlab.example.com", "token", 5, "trunk", sha["checkpoint"], sha["head"], max_items=2)
    assert [item.commit_hash for item in result] == [sha["next"], sha["head"]]
    assert pages == ["1", "2"]


def test_commit_range_limit_fails_before_returning_a_partial_batch():
    def handler(request):
        return httpx.Response(200, json=[{"id": value * 40} for value in "cba"])
    client = HttpGitLabRepositoryClient(httpx.Timeout(1), transport=httpx.MockTransport(handler))
    with pytest.raises(MiningFailure) as caught:
        client.list_commits_after("https://gitlab.example.com", "token", 5, "trunk", "a" * 40, "c" * 40, max_items=1)
    assert caught.value.code == "commit_range_limit_exceeded"


def test_commit_checkpoint_reachability_uses_merge_base_and_maps_missing_checkpoint():
    def handler(request):
        return httpx.Response(200, json=[{"name": "trunk", "type": "branch"}])
    client = HttpGitLabRepositoryClient(httpx.Timeout(1), transport=httpx.MockTransport(handler))
    assert client.is_commit_reachable("https://gitlab.example.com", "token", 5, "a" * 40, "trunk")
    missing = HttpGitLabRepositoryClient(httpx.Timeout(1), transport=httpx.MockTransport(lambda _: httpx.Response(404, json={"message": "private"})))
    assert not missing.is_commit_reachable("https://gitlab.example.com", "secret-token", 5, "a" * 40, "trunk")


def test_commit_range_follows_link_header_when_provider_omits_x_next_page():
    pages = []
    def handler(request):
        page = request.url.params.get("page"); pages.append(page)
        if page == "1":
            return httpx.Response(200, headers={"Link": '<https://gitlab.example.com/api/v4/projects/5/repository/commits?page=2>; rel="next"'},
                json=[{"id": "c" * 40}])
        return httpx.Response(200, json=[{"id": "b" * 40}])
    client = HttpGitLabRepositoryClient(httpx.Timeout(1), transport=httpx.MockTransport(handler))
    result = client.list_commits_after("https://gitlab.example.com", "token", 5, "trunk", "a" * 40, "c" * 40, max_items=2)
    assert pages == ["1", "2"]
    assert [item.commit_hash for item in result] == ["b" * 40, "c" * 40]
