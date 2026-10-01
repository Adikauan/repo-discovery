from dataclasses import dataclass

import httpx

from app.domain.value_objects.mining_failure import MiningFailure
from app.domain.value_objects.repository_context import RepositoryFileMetadata
from app.infrastructure.gitlab.http_gitlab_connection_client import HttpGitLabConnectionClient
from app.domain.value_objects.normalized_commit import NormalizedCommit
from app.domain.value_objects.commit_diff import CommitDiffFile, CommitDiffProviderResult
from app.domain.errors import CommitDiffError
from datetime import datetime
import re


@dataclass(frozen=True)
class EffectiveProject:
    id: int
    name: str
    full_path: str


@dataclass(frozen=True)
class GitLabBranch:
    name: str
    commit_sha: str
    default: bool


class HttpGitLabRepositoryClient:
    """Metadata-only GitLab API adapter. It never downloads repository archives or blobs."""
    def __init__(self, timeout, *, transport=None, max_tree_entries=50_000):
        self.timeout, self.transport, self.max_tree_entries = timeout, transport, max_tree_entries

    def _client(self):
        return httpx.Client(timeout=self.timeout, follow_redirects=False, transport=self.transport, verify=True)

    @staticmethod
    def _base(url):
        return HttpGitLabConnectionClient._base(url)

    def _request(self, client, url, token, params=None):
        try:
            response = client.get(url, headers={"PRIVATE-TOKEN": token}, params=params)
        except httpx.TimeoutException as error:
            raise MiningFailure("repository_timeout") from error
        except httpx.HTTPError as error:
            raise MiningFailure("repository_processing_failed") from error
        if response.status_code == 404:
            raise MiningFailure("repository_not_found")
        if response.status_code == 403 or response.status_code == 401:
            raise MiningFailure("repository_forbidden")
        if response.status_code != 200:
            raise MiningFailure("repository_invalid_response")
        try:
            return response.json(), response.headers
        except (ValueError, TypeError) as error:
            raise MiningFailure("repository_invalid_response") from error

    def _pages(self, client, url, token, params, limit):
        values, page, visited = [], 1, set()
        while page:
            if page in visited or len(values) > limit:
                raise MiningFailure("repository_tree_limit_exceeded")
            visited.add(page)
            body, headers = self._request(client, url, token, {**params, "per_page": 100, "page": page})
            if not isinstance(body, list):
                raise MiningFailure("repository_invalid_response")
            values.extend(body)
            if len(values) > limit:
                raise MiningFailure("repository_tree_limit_exceeded")
            page = self._next_page(headers, page, len(body))
        return values

    @staticmethod
    def _next_page(headers, current_page, body_length):
        next_page = (headers.get("X-Next-Page") or "").strip()
        if not next_page:
            link = headers.get("Link") or ""
            match = re.search(r'<[^>]*[?&]page=(\d+)[^>]*>\s*;\s*rel="next"', link, re.IGNORECASE)
            if match:
                next_page = match.group(1)
        if next_page:
            try: value = int(next_page)
            except ValueError as error: raise MiningFailure("repository_invalid_response") from error
            if value <= current_page: raise MiningFailure("repository_invalid_response")
            return value
        return current_page + 1 if body_length == 100 else 0

    def project(self, url, token, project_id):
        with self._client() as client:
            body, _ = self._request(client, f"{self._base(url)}/projects/{project_id}", token)
        if not isinstance(body, dict):
            raise MiningFailure("repository_invalid_response")
        project = body.get("id")
        path = body.get("path_with_namespace")
        name = body.get("name")
        if type(project) is not int or project != project_id or not isinstance(path, str) or not path or not isinstance(name, str) or not name:
            raise MiningFailure("repository_invalid_response")
        return {"id": project, "name": name, "full_path": path}

    def list_branches(self, url, token, project_id):
        if type(project_id) is not int or project_id <= 0:
            raise MiningFailure("repository_invalid_response")
        with self._client() as client:
            rows = self._pages(client, f"{self._base(url)}/projects/{project_id}/repository/branches",
                               token, {}, self.max_tree_entries)
        result = []
        seen = set()
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("name"), str) or not row["name"].strip():
                raise MiningFailure("repository_invalid_response")
            commit = row.get("commit")
            sha = commit.get("id") if isinstance(commit, dict) else None
            if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-fA-F]{40,64}", sha):
                raise MiningFailure("repository_invalid_response")
            name = row["name"]
            if name in seen:
                continue
            seen.add(name)
            result.append(GitLabBranch(name, sha.lower(), row.get("default") is True))
        return tuple(sorted(result, key=lambda item: (not item.default, item.name.casefold(), item.name)))

    def tree(self, url, token, project_id, branch):
        with self._client() as client:
            rows = self._pages(client, f"{self._base(url)}/projects/{project_id}/repository/tree", token,
                               {"ref": branch, "recursive": "true"}, self.max_tree_entries)
        result = []
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("path"), str):
                raise MiningFailure("repository_invalid_response")
            kind = row.get("type")
            if kind in {"blob", "file"}:
                size = row.get("size")
                result.append(RepositoryFileMetadata(row["path"], "blob", size if type(size) is int and size >= 0 else None))
        return tuple(sorted(result, key=lambda item: item.path))

    def get_branch_head(self, url, token, project_id, branch):
        with self._client() as client:
            body, _ = self._request(client, f"{self._base(url)}/projects/{project_id}/repository/commits",
                                    token, {"ref_name": branch, "per_page": 1, "page": 1})
        if not isinstance(body, list):
            raise MiningFailure("repository_invalid_response")
        if not body:
            raise MiningFailure("repository_target_branch_unavailable")
        row = body[0]
        if not isinstance(row, dict):
            raise MiningFailure("repository_invalid_response")
        return self._commit(row)

    @staticmethod
    def _commit(row):
        sha = row.get("id") or row.get("short_id")
        if not isinstance(sha, str) or len(sha) not in {40, 64} or any(c not in "0123456789abcdefABCDEF" for c in sha):
            raise MiningFailure("repository_invalid_response")
        email = row.get("author_email")
        name = row.get("author_name")
        authored = row.get("authored_date") or row.get("created_at")
        try:
            authored_at = datetime.fromisoformat(authored.replace("Z", "+00:00")) if isinstance(authored, str) else None
        except ValueError:
            authored_at = None
        message = row.get("message")
        parents = row.get("parent_ids", [])
        if not isinstance(parents, list) or any(not isinstance(value, str) or len(value) not in {40, 64}
                                                or any(c not in "0123456789abcdefABCDEF" for c in value)
                                                for value in parents):
            raise MiningFailure("repository_invalid_response")
        return NormalizedCommit(sha.lower(), email if isinstance(email, str) else None,
            name if isinstance(name, str) else None, authored_at, message if isinstance(message, str) else None,
            tuple(value.lower() for value in parents), author_email_malformed=email is not None and not isinstance(email, str))

    def list_commits_after(self, url, token, project_id, branch, checkpoint, head, *, max_items):
        values, seen, page, visited = [], set(), 1, set()
        endpoint = f"{self._base(url)}/projects/{project_id}/repository/commits"
        with self._client() as client:
            while page:
                if page in visited:
                    raise MiningFailure("repository_invalid_response")
                visited.add(page)
                body, headers = self._request(client, endpoint, token, {
                    "ref_name": f"{checkpoint}..{head}", "per_page": 100, "page": page,
                })
                if not isinstance(body, list):
                    raise MiningFailure("repository_invalid_response")
                for row in body:
                    if not isinstance(row, dict):
                        raise MiningFailure("repository_invalid_response")
                    commit = self._commit(row)
                    if commit.commit_hash == checkpoint.lower():
                        continue
                    if commit.commit_hash not in seen:
                        seen.add(commit.commit_hash)
                        values.append(commit)
                        if len(values) > max_items:
                            raise MiningFailure("commit_range_limit_exceeded")
                page = self._next_page(headers, page, len(body))
        return tuple(reversed(values))

    def is_commit_reachable(self, url, token, project_id, checkpoint, branch):
        with self._client() as client:
            try:
                rows = self._pages(client, f"{self._base(url)}/projects/{project_id}/repository/commits/{checkpoint}/refs",
                                   token, {"type": "branch"}, self.max_tree_entries)
            except MiningFailure as error:
                if error.code == "repository_not_found": return False
                raise
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("name"), str):
                raise MiningFailure("repository_invalid_response")
            if row["name"] == branch and row.get("type") in (None, "branch"):
                return True
        return False

    def get_commit_diff(self, url, token, project_id, commit_hash, *, max_files):
        if type(project_id) is not int or project_id < 1 or not isinstance(commit_hash, str) or not re.fullmatch(r"[0-9a-fA-F]{40,64}", commit_hash):
            raise CommitDiffError("commit_diff_invalid_response")
        endpoint = f"{self._base(url)}/projects/{project_id}/repository/commits/{commit_hash}/diff"
        rows, page, visited, completeness = [], 1, set(), "unknown"
        try:
            with self._client() as client:
                while page:
                    if page in visited:
                        raise CommitDiffError("commit_diff_invalid_response")
                    visited.add(page)
                    try:
                        response = client.get(endpoint, headers={"PRIVATE-TOKEN": token},
                                              params={"per_page": min(100, max_files + 1), "page": page})
                    except httpx.TimeoutException as error:
                        raise CommitDiffError("commit_diff_timeout") from error
                    except httpx.HTTPError as error:
                        raise CommitDiffError("commit_diff_unavailable") from error
                    if response.status_code == 404:
                        raise CommitDiffError("commit_not_found")
                    if response.status_code in (401, 403):
                        raise CommitDiffError("commit_diff_forbidden")
                    if response.status_code != 200:
                        raise CommitDiffError("commit_diff_unavailable")
                    try:
                        body = response.json()
                    except (ValueError, TypeError) as error:
                        raise CommitDiffError("commit_diff_invalid_response") from error
                    if not isinstance(body, list):
                        raise CommitDiffError("commit_diff_invalid_response")
                    for raw in body:
                        if not isinstance(raw, dict):
                            raise CommitDiffError("commit_diff_invalid_response")
                        old_path, new_path, diff = raw.get("old_path"), raw.get("new_path"), raw.get("diff")
                        if not isinstance(old_path, str) or not isinstance(new_path, str) or (diff is not None and not isinstance(diff, str)):
                            raise CommitDiffError("commit_diff_invalid_response")
                        flags = [raw.get("new_file"), raw.get("deleted_file"), raw.get("renamed_file")]
                        if any(value is not None and type(value) is not bool for value in flags):
                            raise CommitDiffError("commit_diff_invalid_response")
                        if flags[0] is True:
                            change_type = "added"
                        elif flags[1] is True:
                            change_type = "deleted"
                        elif flags[2] is True:
                            change_type = "renamed"
                        elif flags == [False, False, False]:
                            change_type = "modified"
                        else:
                            change_type = None
                        for field in ("collapsed", "too_large"):
                            if raw.get(field) is not None and type(raw[field]) is not bool:
                                raise CommitDiffError("commit_diff_invalid_response")
                        rows.append(CommitDiffFile(old_path, new_path, change_type, diff or None, bool(diff),
                            binary=None, collapsed=raw.get("collapsed"), too_large=raw.get("too_large")))
                        if len(rows) > max_files:
                            return CommitDiffProviderResult(tuple(rows[:max_files]), "truncated")
                    headers = response.headers
                    total_pages = headers.get("X-Total-Pages")
                    next_page = (headers.get("X-Next-Page") or "").strip()
                    if total_pages:
                        try: total = int(total_pages)
                        except ValueError as error: raise CommitDiffError("commit_diff_invalid_response") from error
                        if total < page:
                            raise CommitDiffError("commit_diff_invalid_response")
                        completeness = "complete"
                    if next_page:
                        try: candidate = int(next_page)
                        except ValueError as error: raise CommitDiffError("commit_diff_invalid_response") from error
                        if candidate <= page: raise CommitDiffError("commit_diff_invalid_response")
                        if len(rows) >= max_files:
                            return CommitDiffProviderResult(tuple(rows[:max_files]), "truncated")
                        page = candidate
                    elif total_pages:
                        page = page + 1 if total > page else 0
                    else:
                        link = headers.get("Link") or ""
                        match = re.search(r'<[^>]*[?&]page=(\d+)[^>]*>\s*;\s*rel="next"', link, re.IGNORECASE)
                        if match:
                            candidate = int(match.group(1))
                            if candidate <= page: raise CommitDiffError("commit_diff_invalid_response")
                            page = candidate
                        else:
                            if completeness != "complete":
                                completeness = "unknown"
                            page = 0
        except CommitDiffError:
            raise
        except Exception as error:
            raise CommitDiffError("commit_diff_invalid_response") from error
        return CommitDiffProviderResult(tuple(rows), completeness)

    def _list(self, url, token, path, params, limit=50_000):
        with self._client() as client:
            rows = self._pages(client, f"{self._base(url)}/{path}", token, params, limit)
        result = []
        for row in rows:
            if not isinstance(row, dict) or type(row.get("id")) is not int or not isinstance(row.get("name"), str):
                raise MiningFailure("repository_invalid_response")
            full = row.get("full_path") or row.get("path_with_namespace")
            if not isinstance(full, str):
                raise MiningFailure("repository_invalid_response")
            result.append(EffectiveProject(row["id"], row["name"], full))
        return tuple(result)

    def get_group(self, url, token, group_id):
        with self._client() as client:
            body, _ = self._request(client, f"{self._base(url)}/groups/{group_id}", token)
        if not isinstance(body, dict) or type(body.get("id")) is not int or body.get("id") != group_id or not isinstance(body.get("full_path"), str):
            raise MiningFailure("repository_invalid_response")
        return EffectiveProject(body["id"], body.get("name") or body["full_path"], body["full_path"])

    def get_project_scope(self, url, token, project_id):
        with self._client() as client:
            body, _ = self._request(client, f"{self._base(url)}/projects/{project_id}", token)
        if not isinstance(body, dict) or type(body.get("id")) is not int:
            raise MiningFailure("repository_invalid_response")
        full_path = body.get("path_with_namespace")
        name = body.get("name")
        if body["id"] != project_id or not isinstance(full_path, str) or not isinstance(name, str):
            raise MiningFailure("repository_invalid_response")
        return EffectiveProject(project_id, name, full_path)

    def group_children(self, url, token, group_id):
        groups = self._list(url, token, f"groups/{group_id}/subgroups", {})
        projects = self._list(url, token, f"groups/{group_id}/projects", {"include_subgroups": "false", "with_shared": "false"})
        return groups, projects
