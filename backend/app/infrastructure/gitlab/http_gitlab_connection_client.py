from urllib.parse import urlsplit, urlunsplit

import httpx

from app.domain.value_objects.connection_validation_result import ConnectionValidationResult
from app.domain.value_objects.gitlab_discovery_result import GitLabDiscoveryResult
from app.domain.value_objects.gitlab_hierarchy_node import GitLabHierarchyNode


MESSAGES = {
    "success": "GitLab connection validated.",
    "invalid_url": "The GitLab URL is invalid.",
    "invalid_credentials": "GitLab rejected the credential.",
    "forbidden": "The credential cannot access the validation endpoint.",
    "unreachable": "The GitLab instance could not be reached.",
    "timeout": "The GitLab validation request timed out.",
    "invalid_response": "GitLab returned an unexpected response.",
    "rate_limited": "GitLab rate-limited the validation request.",
    "provider_unavailable": "GitLab is temporarily unavailable.",
}


class HttpGitLabConnectionClient:
    def __init__(self, timeout: httpx.Timeout, transport=None):
        self.timeout = timeout
        self.transport = transport

    @staticmethod
    def _base(root: str) -> str:
        parsed = urlsplit(root.strip())
        if (parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None):
            raise ValueError("invalid GitLab URL")
        path = "/" + "/".join(part for part in parsed.path.split("/") if part)
        if path == "/":
            path = ""
        return urlunsplit((parsed.scheme.lower(), parsed.netloc, f"{path}/api/v4", "", ""))

    @classmethod
    def _endpoint(cls, root: str) -> str:
        return f"{cls._base(root)}/user"

    @staticmethod
    def _outcome(status_code: int) -> str:
        if status_code == 401:
            return "invalid_credentials"
        if status_code == 403:
            return "forbidden"
        if status_code == 404:
            return "not_found"
        if status_code == 429:
            return "rate_limited"
        if status_code >= 500:
            return "provider_unavailable"
        return "invalid_response"

    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=self.timeout, follow_redirects=False,
                            transport=self.transport, verify=True)

    def validate(self, gitlab_url: str, token: str) -> ConnectionValidationResult:
        try:
            endpoint = self._endpoint(gitlab_url)
        except (ValueError, TypeError):
            return ConnectionValidationResult("invalid_url", MESSAGES["invalid_url"])
        try:
            with self._client() as client:
                response = client.get(endpoint, headers={"PRIVATE-TOKEN": token})
            if response.status_code == 200:
                body = response.json()
                outcome = "success" if isinstance(body, dict) and body.get("id") is not None else "invalid_response"
            else:
                outcome = self._outcome(response.status_code)
        except httpx.TimeoutException:
            outcome = "timeout"
        except (httpx.ConnectError, httpx.NetworkError):
            outcome = "unreachable"
        except (ValueError, TypeError):
            outcome = "invalid_response"
        return ConnectionValidationResult(outcome, MESSAGES[outcome])

    @staticmethod
    def _node(data: object, kind: str, parent_group_id: int | None = None) -> GitLabHierarchyNode | None:
        if not isinstance(data, dict):
            return None
        identifier = data.get("id")
        name = data.get("name")
        full_path = data.get("full_path") or data.get("path")
        if not isinstance(identifier, int) or identifier <= 0 or not isinstance(name, str) or not name.strip():
            return None
        if not isinstance(full_path, str) or not full_path.strip():
            return None
        if kind == "group":
            raw_parent = data.get("parent_id")
            parent = raw_parent if isinstance(raw_parent, int) and raw_parent > 0 else parent_group_id
            return GitLabHierarchyNode(identifier, "group", name, full_path, parent, True)
        namespace = data.get("namespace")
        namespace_id = namespace.get("id") if isinstance(namespace, dict) else parent_group_id
        parent = namespace_id if isinstance(namespace_id, int) and namespace_id > 0 else parent_group_id
        return GitLabHierarchyNode(identifier, "repository", name, full_path, parent, False)

    def _get(self, client: httpx.Client, url: str, token: str, params: dict | None = None):
        try:
            response = client.get(url, headers={"PRIVATE-TOKEN": token}, params=params)
        except httpx.TimeoutException:
            return "timeout", None, None
        except (httpx.ConnectError, httpx.NetworkError):
            return "unreachable", None, None
        if response.status_code != 200:
            return self._outcome(response.status_code), None, None
        try:
            return "success", response.json(), response.headers
        except (ValueError, TypeError):
            return "invalid_response", None, None

    def _list(self, url: str, token: str, kind: str, parent_group_id: int | None = None,
              extra_params: dict | None = None) -> GitLabDiscoveryResult:
        nodes: dict[int, GitLabHierarchyNode] = {}
        page = "1"
        visited: set[str] = set()
        try:
            with self._client() as client:
                while page:
                    if page in visited:
                        return GitLabDiscoveryResult("invalid_response")
                    visited.add(page)
                    params = {"per_page": 100, "page": page, **(extra_params or {})}
                    outcome, payload, headers = self._get(client, url, token, params)
                    if outcome != "success":
                        return GitLabDiscoveryResult(outcome)
                    if not isinstance(payload, list):
                        return GitLabDiscoveryResult("invalid_response")
                    for data in payload:
                        node = self._node(data, kind, parent_group_id)
                        if node is None:
                            return GitLabDiscoveryResult("invalid_response")
                        nodes[node.id] = node
                    page = (headers.get("X-Next-Page", "") or "").strip()
        except (ValueError, TypeError):
            return GitLabDiscoveryResult("invalid_url")
        ordered = tuple(sorted(nodes.values(), key=lambda item: (item.type, item.full_path.casefold(), item.id)))
        return GitLabDiscoveryResult("success", ordered)

    def list_top_level_groups(self, gitlab_url: str, token: str) -> GitLabDiscoveryResult:
        try:
            url = f"{self._base(gitlab_url)}/groups"
        except (ValueError, TypeError):
            return GitLabDiscoveryResult("invalid_url")
        return self._list(url, token, "group", extra_params={"top_level_only": "true", "all_available": "true"})

    def list_group_children(self, gitlab_url: str, token: str, group_id: int) -> GitLabDiscoveryResult:
        try:
            base = self._base(gitlab_url)
        except (ValueError, TypeError):
            return GitLabDiscoveryResult("invalid_url")
        groups = self._list(f"{base}/groups/{group_id}/subgroups", token, "group", group_id)
        if not groups.succeeded:
            return groups
        projects = self._list(
            f"{base}/groups/{group_id}/projects", token, "repository", group_id,
            {"include_subgroups": "false", "with_shared": "false"},
        )
        if not projects.succeeded:
            return projects
        by_key = {(item.type, item.id): item for item in (*groups.nodes, *projects.nodes)}
        ordered = tuple(sorted(by_key.values(), key=lambda item: (item.type, item.full_path.casefold(), item.id)))
        return GitLabDiscoveryResult("success", ordered)

    def _get_entity(self, gitlab_url: str, token: str, path: str, kind: str,
                    parent_group_id: int | None = None) -> GitLabDiscoveryResult:
        try:
            url = f"{self._base(gitlab_url)}/{path}"
        except (ValueError, TypeError):
            return GitLabDiscoveryResult("invalid_url")
        try:
            with self._client() as client:
                outcome, payload, _ = self._get(client, url, token)
        except (ValueError, TypeError):
            return GitLabDiscoveryResult("invalid_url")
        if outcome != "success":
            return GitLabDiscoveryResult(outcome)
        node = self._node(payload, kind, parent_group_id)
        return GitLabDiscoveryResult("success", (node,)) if node else GitLabDiscoveryResult("invalid_response")

    def get_group(self, gitlab_url: str, token: str, group_id: int) -> GitLabDiscoveryResult:
        return self._get_entity(gitlab_url, token, f"groups/{group_id}", "group")

    def get_project(self, gitlab_url: str, token: str, project_id: int) -> GitLabDiscoveryResult:
        return self._get_entity(gitlab_url, token, f"projects/{project_id}", "repository")
