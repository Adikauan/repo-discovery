# Normalized GitLab Commit History Port

Application/domain code uses a GitLab repository port; it never receives HTTPX types or raw provider DTOs.

## Operations

The existing repository port gains equivalent operations:

- `get_branch_head(instance_url, credential, project_id, branch) -> NormalizedCommit`
- `is_commit_reachable(instance_url, credential, project_id, commit_sha, branch) -> bool`
- `list_commits_after(instance_url, credential, project_id, branch, checkpoint_sha, head_sha, max_items) -> complete tuple[NormalizedCommit, ...]`

The adapter validates the requested project/branch and SHA values, normalizes provider failure classes, follows every response page/continuation, deduplicates by full commit hash, and fails on malformed/incomplete pagination. It reads no commit diffs, repository blobs, archives, or local clones.

## NormalizedCommit

| Field | Type | Notes |
|---|---|---|
| `commit_hash` | full SHA string | Stable identity |
| `author_email` | string or null | Raw provider value remains transient in infrastructure until normalized; invalid raw values are discarded before domain result construction |
| `author_name` | string or null | Optional safe display context |
| `authored_at` | timezone-aware datetime or null | Invalid timestamps normalize to null when optional; malformed required SHA/page fails response |
| `message` | string or null | Sanitized and bounded before Finding persistence |
| `parent_hashes` | tuple of full SHA values | Used only for normalized graph/reachability operations as needed |

## Range and bounded retrieval semantics

Use full commit identities, not timestamp `since`/`until`, for incremental correctness. For an existing checkpoint, prove it remains reachable from the selected branch before accepting the range. The commit range is strictly after checkpoint and through captured HEAD. The adapter requests no more than `configured_max + 1` unique commits; the extra item detects overflow. It returns the complete range in deterministic oldest-to-newest order only when the range is within limit. Otherwise it raises normalized `commit_range_limit_exceeded` and does not return a partial candidate list.

Provider pagination must not rely on `x-total` or `x-total-pages`, which the Commits API omits. Follow available `Link`/next-page metadata, with validated page exhaustion fallback consistent with the existing GitLab adapter. Authentication, authorization, not-found, timeout, invalid-response, unreachable-checkpoint, and range-limit errors are represented by normalized safe codes. No raw response bodies, token, authorization header, or exception message crosses the port.

## Rule boundary

`UnauthorizedCommitAuthorRule.execute(commits, allowed_author_emails)` consumes normalized commit values and returns immutable normalized finding candidates. It does not call the GitLab port or persistence. The application layer persists the candidates.
