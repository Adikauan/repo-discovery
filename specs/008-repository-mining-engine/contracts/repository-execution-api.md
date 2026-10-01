# Repository Execution API Contract

Feature 008 adds read-only repository history under the existing `/api/v1` API. No new execution or repository status mutation endpoint is permitted. All response bodies are explicit Pydantic projections; never serialize SQLAlchemy rows, snapshot JSON, or GitLab DTOs directly.

## List repository executions

`GET /api/v1/executions/{executionId}/repositories?page=1&pageSize=25`

### Query

| Parameter | Rules |
|---|---|
| `page` | Integer, minimum 1, default 1. |
| `pageSize` | Integer 1–100, default 25. |

### Response `200`

```json
{
  "items": [
    {
      "id": "uuid",
      "miningExecutionId": "uuid",
      "gitlabProjectId": 42,
      "repositoryName": "service",
      "repositoryFullPath": "group/service",
      "status": "completed",
      "startedAt": "2026-09-29T12:00:00Z",
      "completedAt": "2026-09-29T12:00:03Z",
      "processedBranch": "release/stable",
      "fileCount": 37,
      "findingCount": 0,
      "error": null
    }
  ],
  "page": 1,
  "pageSize": 25,
  "totalItems": 1,
  "totalPages": 1
}
```

Ordering is `repositoryFullPath` ascending with `gitlabProjectId` ascending as a stable tie-breaker. Values are persisted RepositoryExecution snapshots/results. The list may omit observed extension detail to keep the history response concise.

### Response `404`

Normalized not-found response if the MiningExecution does not exist. Other backend failures use existing normalized API error handling without raw details.

## Repository execution detail

`GET /api/v1/executions/{executionId}/repositories/{repositoryExecutionId}`

### Response `200`

Contains the list row fields plus:

```json
{
  "observedExtensions": [".py", ".toml", "(none)"],
  "extensionsTruncated": false
}
```

Extensions are bounded by the configured `repository_mining_max_extensions` value (1–100, default 100); the API contract never returns more than 100 distinct values. `findingCount` remains zero for Feature 008.

### Response `404`

Return normalized not-found both when the parent execution is absent and when the repository record is absent or belongs to another execution. Do not reveal cross-execution record existence.

## Execution detail additive fields

`GET /api/v1/executions/{executionId}` retains its current response and adds:

- `scopeResolutionFailureCount`: nonnegative integer (zero for existing rows/backfilled data).
- `error`: existing `{code, summary}` projection may be present for `failed`, or for `partially_completed` only when scope resolution was incomplete. Allowed scope codes are curated `scope_resolution_incomplete` and `scope_resolution_failed` with generic safe summaries. Repository-level provider details remain on their RepositoryExecution rows.

`repositoryCount`, `successfulRepositoryCount`, and `failedRepositoryCount` continue to reconcile exactly with persisted RepositoryExecution rows. Scope failures affect aggregate status separately and do not inflate `failedRepositoryCount`. The existing `completionMeaning` projection must no longer claim that successful Feature 008 executions completed without mining: for completed zero-scope it communicates successful completion with no resolved repositories; for non-empty successful completion it communicates that repository processing completed. It is absent when not applicable.

## Repository status/error vocabulary

Statuses: `pending`, `running`, `completed`, `failed`.

Safe error codes include `gitlab_credential_missing`, `gitlab_instance_mismatch`, `scope_entity_unavailable`, `repository_not_found`, `repository_forbidden`, `repository_timeout`, `repository_invalid_response`, `repository_default_branch_missing`, `repository_tree_limit_exceeded`, and `repository_processing_failed`. Only allow-listed code/summary pairs are returned. No raw response body, exception, token, header, fingerprint, SQL detail, or stack trace is exposed.

## Security and compatibility

- Existing endpoint paths and response fields remain backward-compatible; fields are additive.
- No credential or encrypted credential field appears in these DTOs.
- Internal GitLab instance fingerprints, raw scope snapshot, provider response fields, rule internals, and database concurrency metadata are not returned.
- Authenticated application access policy remains the same as other execution history endpoints.
- All reads are deterministic; no endpoint performs GitLab access or revalidates scope.
