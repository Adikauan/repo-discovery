import httpx

from app.infrastructure.gitlab.http_gitlab_connection_client import HttpGitLabConnectionClient


def _group(identifier, name, path, parent=None):
    return {"id": identifier, "name": name, "full_path": path, "parent_id": parent}


def _project(identifier, name, path, namespace_id):
    return {"id": identifier, "name": name, "path": path.rsplit("/", 1)[-1], "path_with_namespace": path,
            "namespace": {"id": namespace_id}}


def test_root_follows_all_pages_deduplicates_and_preserves_mount_path():
    requests = []

    def respond(request):
        requests.append(request)
        page = request.url.params.get("page")
        if page == "1":
            return httpx.Response(200, json=[_group(1, "Root", "root")], headers={"X-Next-Page": "2"})
        return httpx.Response(200, json=[_group(1, "Root", "root"), _group(2, "Other", "other")])

    client = HttpGitLabConnectionClient(httpx.Timeout(5), httpx.MockTransport(respond))
    result = client.list_top_level_groups("https://gitlab.example/gitlab", "secret")
    assert result.succeeded and [node.id for node in result.nodes] == [2, 1]
    assert len(result.nodes) == 2
    assert all(request.url.path == "/gitlab/api/v4/groups" for request in requests)
    assert all(request.url.params["per_page"] == "100" for request in requests)
    assert all(request.headers["PRIVATE-TOKEN"] == "secret" for request in requests)
    assert requests[0].url.params["top_level_only"] == "true"


def test_group_children_lists_direct_subgroups_and_owned_non_shared_projects_only():
    requests = []

    def respond(request):
        requests.append(request)
        page = request.url.params.get("page")
        if request.url.path.endswith("/subgroups"):
            if page == "1":
                return httpx.Response(200, json=[_group(21, "Nested", "root/nested", 20)], headers={"X-Next-Page": "2"})
            return httpx.Response(200, json=[_group(22, "Tools", "root/tools", 20)])
        if page == "1":
            return httpx.Response(200, json=[_project(100, "API", "root/api", 20)], headers={"X-Next-Page": "2"})
        return httpx.Response(200, json=[_project(101, "Worker", "root/worker", 20)])

    client = HttpGitLabConnectionClient(httpx.Timeout(5), httpx.MockTransport(respond))
    result = client.list_group_children("https://gitlab.example", "secret", 20)
    assert result.succeeded
    assert {(node.id, node.type) for node in result.nodes} == {
        (21, "group"), (22, "group"), (100, "repository"), (101, "repository")}
    assert [node.id for node in result.nodes] == [21, 22, 100, 101]
    project_request = next(request for request in requests if request.url.path.endswith("/projects"))
    assert project_request.url.params["include_subgroups"] == "false"
    assert project_request.url.params["with_shared"] == "false"
    assert len(requests) == 4


def test_later_page_failure_returns_no_apparent_partial_success():
    def respond(request):
        if request.url.params.get("page") == "1":
            return httpx.Response(200, json=[_group(1, "Root", "root")], headers={"X-Next-Page": "2"})
        return httpx.Response(503)

    client = HttpGitLabConnectionClient(httpx.Timeout(5), httpx.MockTransport(respond))
    result = client.list_top_level_groups("https://gitlab.example", "secret")
    assert result.outcome == "provider_unavailable" and result.nodes == ()


def test_malformed_payload_timeout_and_invalid_url_are_normalized():
    malformed = HttpGitLabConnectionClient(
        httpx.Timeout(5), httpx.MockTransport(lambda request: httpx.Response(200, json={"unexpected": []})))
    assert malformed.list_top_level_groups("https://gitlab.example", "secret").outcome == "invalid_response"
    timeout = HttpGitLabConnectionClient(
        httpx.Timeout(5), httpx.MockTransport(lambda request: (_ for _ in ()).throw(httpx.ReadTimeout("secret"))))
    assert timeout.list_top_level_groups("https://gitlab.example", "secret").outcome == "timeout"
    assert malformed.list_top_level_groups("ftp://invalid", "secret").outcome == "invalid_url"
