# Feature 013 Read-only Presentation Projections

## Compatibility boundary

Feature 013 approves exactly three additive read-only projections: this Home summary endpoint, nullable `scheduleSummary` on Monitoring Configuration list items, and `findingCount` on execution list items. They are backwards-compatible, derived from existing persisted data, and are not authoritative new domain state. Existing routes, fields, meanings, filters, ordering, and write semantics remain unchanged. These projections add no persistence, migration, business rule, or write behavior. Reuse existing endpoint/DTO data when it already exposes a value cleanly; no additional projection or endpoint is approved by this contract.

The Home projection aggregates existing execution, repository execution, and Finding data only. It does not persist historical analytics, fabricate trend history, or create Finding categories.

## Configuration and execution list projections

The nullable configuration `scheduleSummary` and execution `findingCount` projections are specified below with the existing list-item contract extensions. They do not alter scheduling recurrence/persistence, Finding detection, or execution semantics.

## Endpoint

`GET /api/v1/dashboard/summary`

No query parameters, request body, or mutation semantics. The response is derived from existing persisted MiningExecution, RepositoryExecution, and Finding rows. No credentials, author emails, raw GitLab data, or full snapshots are returned.

## Response

```json
{
  "window": {
    "start": "2026-09-24T00:00:00Z",
    "end": "2026-09-30T14:30:00Z",
    "timezone": "UTC"
  },
  "metrics": {
    "executionCount": 12,
    "repositoriesProcessed": 48,
    "findingCount": 15,
    "successRatePercent": 73,
    "terminalExecutionCount": 11
  },
  "statusDistribution": {
    "pending": 0,
    "running": 1,
    "completed": 8,
    "partiallyCompleted": 1,
    "failed": 2
  },
  "dailyExecutions": [
    { "date": "2026-09-24", "count": 0 },
    { "date": "2026-09-25", "count": 0 },
    { "date": "2026-09-26", "count": 0 },
    { "date": "2026-09-27", "count": 0 },
    { "date": "2026-09-28", "count": 0 },
    { "date": "2026-09-29", "count": 2 },
    { "date": "2026-09-30", "count": 10 }
  ],
  "recentExecutions": [
    {
      "id": "43edf8e5-a78d-462d-b958-72d04e139e55",
      "configurationName": "Platform Configuration",
      "status": "completed",
      "triggerType": "manual",
      "createdAt": "2026-09-30T12:06:00Z",
      "startedAt": "2026-09-30T12:06:01Z",
      "completedAt": "2026-09-30T12:08:49Z",
      "durationSeconds": 168,
      "findingCount": 1
    }
  ],
  "findingsByRule": [
    { "ruleId": "unauthorized_commit_author", "label": "Unauthorized commit author", "count": 15 }
  ]
}
```

The example values above are illustrative only and MUST NOT be used as application fixtures or defaults.

## Additive existing-list projections

These read-only fields are added to existing response items to support table presentation without per-row detail requests. Existing fields, routes, filters, pagination, ordering, mutations, and error behavior are unchanged.

### Execution list item

Add:

```json
{ "findingCount": 1 }
```

`findingCount` is the read-only count of persisted Finding rows associated with the execution through RepositoryExecution. It is not recomputed from current repository state and does not imply Finding severity or type. This presentation value does not replace or change the existing execution counter semantics.

### Monitoring Configuration list item

Add nullable `scheduleSummary`:

```json
{
  "scheduleSummary": {
    "recurrenceType": "weekly",
    "enabled": true,
    "executionTime": "09:00",
    "timezone": "America/Sao_Paulo",
    "dayOfWeek": 1,
    "dayOfMonth": null
  }
}
```

The field is `null` when no schedule exists. A configured schedule returns its stored fields, including `enabled: false` when the persisted schedule is disabled. Daily schedules have null weekday/month-day values; weekly schedules have the existing ISO weekday; monthly schedules have the existing day of month. Do not calculate a next occurrence in this list projection. The summary is loaded in the existing list query/read projection, not by one schedule request per list row.

The example schedule values are illustrative and MUST NOT be used as configuration defaults.

## Semantics

- `window.start` is inclusive, `window.end` exclusive. The window starts at 00:00 UTC six days before the current UTC date and ends at request evaluation time. It covers seven UTC calendar dates.
- `executionCount` and `statusDistribution` include MiningExecutions created in the window and preserve their actual status at read time.
- `repositoriesProcessed` is the distinct count of GitLab project IDs represented by RepositoryExecution rows related to executions created in the window; it does not mean configured/monitored scope size.
- `findingCount` counts persisted Finding rows through RepositoryExecution and MiningExecution relationships for executions created in the window.
- `terminalExecutionCount` is `completed + partially_completed + failed` in the window.
- `successRatePercent` is `round(completed / terminalExecutionCount * 100)`; pending/running are excluded, partially completed is not counted as fully successful, and the value is `null` when `terminalExecutionCount` is zero.
- `dailyExecutions` contains exactly seven UTC date buckets ordered oldest to newest, zero-filling dates without executions. Counts use execution `createdAt`.
- `recentExecutions` contains at most five rows, newest `createdAt` first and stable execution ID ascending as a tie-breaker.
- `findingsByRule` contains only rule IDs with persisted Finding rows in the window; order by count descending, then rule ID ascending.
- Counts derive from persisted rows; they do not use current configuration, scope, repository state, or transient mining output.
- The endpoint adds no persistence, caching, pagination, external calls, or new business status.

## Error behavior

Use the existing Problem Details response conventions. No provider detail or credential material is included. The Home page maps failures to its existing safe error state and retry interaction.

## Contract tests

Cover an empty window, UTC boundary inclusion/exclusion, seven zero-filled date buckets, each execution status, terminal success-rate denominator/null behavior, distinct project counting across repeated repository executions, persisted Finding counts, five-row cap and deterministic order, actual finding-rule grouping, safe response fields, and read-only behavior.
