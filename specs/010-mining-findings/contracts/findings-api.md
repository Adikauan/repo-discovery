# Findings Read API Contract

All routes use the existing `/api/v1` prefix, wire-model camelCase convention, normalized Problem Details errors, and page/pageSize bounds already used by execution APIs. Finding APIs are read-only.

## List findings for execution

`GET /api/v1/executions/{execution_id}/findings`

Optional query parameters:

- `page` (default 1, minimum 1)
- `pageSize` (default 25, range 1–100)
- `repositoryExecutionId` (UUID)
- `ruleId` (stable rule identifier)
- `severity` (`warning` for the initial rule)

Returns a deterministic page ordered by `authoredAt DESC NULLS LAST, id ASC`, plus `page`, `pageSize`, `totalItems`, and `totalPages`. A repository filter must be verified as belonging to the requested execution.

## List findings for a repository execution

`GET /api/v1/executions/{execution_id}/repositories/{repository_execution_id}/findings`

Uses the same pagination, ordering, and optional rule/severity filters. Return normalized not-found behavior if either identifier does not exist or the repository does not belong to the execution.

## Finding detail

`GET /api/v1/findings/{finding_id}`

Returns one safe Finding DTO. The response derives execution ID and repository display path through RepositoryExecution; it does not allow ownership reassignment.

## Finding DTO

```json
{
  "id": "uuid",
  "repositoryExecutionId": "uuid",
  "executionId": "uuid",
  "ruleId": "unauthorized-commit-author",
  "ruleVersion": "1",
  "severity": "warning",
  "title": "Unauthorized commit author",
  "summary": "A commit author is not in the execution's allowed author list.",
  "repositoryName": "service",
  "repositoryFullPath": "group/service",
  "filePath": null,
  "lineStart": null,
  "lineEnd": null,
  "commitHash": "full-sha",
  "authorEmail": "contributor@example.com",
  "authorEmailState": "valid",
  "authorName": "Contributor",
  "authoredAt": "2026-09-30T12:00:00Z",
  "commitMessageSummary": "A bounded sanitized message",
  "createdAt": "2026-09-30T12:01:00Z"
}
```

`authorEmail` and `authorName` may be null. `authorEmailState` is `valid`, `missing`, or `malformed`. For missing/malformed author identity, `authorEmail` is null and malformed raw input is never returned. `repositoryName`/`repositoryFullPath` are historical values from the owning RepositoryExecution. File path and line fields are null for this rule. The DTO omits credentials, raw provider payloads, raw exception text, database details, snapshot allowlist, and internal checkpoint state.

## Finding count

Existing execution and repository DTO counters continue to report persisted row counts. The API must not infer findings from commit counts or return a fabricated result row.
