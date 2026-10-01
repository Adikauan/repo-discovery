# Data Model: RepoMiner Visual & UX Alignment

## Persistence decision

Feature 013 introduces no persistent entity, column, relationship, enum, lifecycle, or migration. All domain data remains owned by Features 001–012.

## Existing entities presented by this feature

- **MonitoringConfiguration**: Existing name, description, GitLab instance URL, enabled state, revision, global allowed-author emails, scope intent, timestamps, and associated schedule. The UI may reorganize these fields but does not change their persistence or meaning.
- **MonitoringSchedule**: Existing recurrence, local time, IANA timezone, enabled state, revision/ETag behavior, and next-occurrence preview. No recurrence or lifecycle change.
- **MiningExecution**: Existing trigger, status, timestamps, immutable snapshot, counters, completion meaning, safe error, and configuration relationship. Existing manual/scheduled pipeline and history remain unchanged.
- **RepositoryExecution**: Existing repository identity, status, branch, file/extension summary, Finding count, timestamps, and safe error.
- **Finding**: Existing immutable Finding identity, rule, severity, repository association, commit/author context, timestamp, and diff action.

## Transient dashboard response projections

These are additive, read-only API/read-model projections, not domain entities, authoritative new domain state, or persisted values. They derive only from existing Feature 001–012 records. They preserve all existing response fields/meanings and write semantics and are backwards-compatible. These are the only approved presentation projections for Feature 013; no additional projection or endpoint is implied:

- **DashboardSummaryWindow**: Seven UTC calendar days; `start` is inclusive and `end` is exclusive. Start is 00:00 UTC six days before today's UTC date; end is the time of query evaluation.
- **DashboardSummaryMetrics**: Execution count; distinct GitLab project count with a RepositoryExecution in the window; persisted Finding count; status counts; terminal execution success rate.
- **DailyExecutionCount**: UTC date and execution count, with one row for each day in the window, including zero counts.
- **FindingRuleCount**: Existing rule identifier/display label and number of persisted Findings. Only actual rule IDs with matching Finding rows are returned.
- **RecentDashboardExecution**: Existing execution ID, configuration name, status, trigger, created/started/completed timestamps, duration, and persisted Finding count; maximum five rows ordered by creation timestamp descending and stable execution ID ascending as tie-breaker.
- **ExecutionListItem.findingCount**: Additive read-only count of persisted Finding rows associated through RepositoryExecution with the execution; no new field is persisted. This is a presentation projection, not authoritative new domain state.
- **MonitoringConfigurationListItem.scheduleSummary**: Nullable read-only projection of the associated existing schedule's configured state, recurrence, execution time, timezone, recurrence day, and enabled state. No next occurrence is calculated in the list view and no schedule data is duplicated in storage.

The three approved projections are the Home summary, configuration `scheduleSummary`, and execution `findingCount`. `scheduleSummary` does not alter recurrence, scheduler persistence, or next-occurrence behavior. `findingCount` derives from existing persisted Finding rows and does not add a Finding model or change detection/execution semantics. The Home summary creates no historical analytics persistence, fabricated trend history, or Finding categories.

### Derived metric rules

- `executionCount` counts MiningExecution rows created inside the summary window.
- `repositoriesProcessed` counts distinct stable GitLab project IDs represented by RepositoryExecution rows whose parent MiningExecution was created inside the window. It is not a count of currently configured repositories.
- `findingCount` counts persisted Finding rows associated through RepositoryExecution to executions created inside the window; it is not recomputed from current repository state.
- `statusDistribution` includes every execution status in the window, including pending and running.
- `successRatePercent = round(completed / (completed + partially_completed + failed) * 100)`; pending/running are excluded. It is null if there are no terminal executions.
- Daily counts group `created_at` in UTC and always return exactly seven date buckets.
- Recent executions are limited to five and use persisted values only.

## Security and consistency

The response contains no GitLab credential, token, authorization header, raw provider DTO, full execution snapshot, or author email aggregation. Counts are computed from existing related rows in a consistent read transaction where supported by the current unit-of-work/query infrastructure. The projection never mutates executions, repository results, or Findings.
