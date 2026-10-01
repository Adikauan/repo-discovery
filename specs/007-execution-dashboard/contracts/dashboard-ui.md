# UI Contract: Execution Dashboard

## Route and entry

- Use the existing `/executions/:id` route and `ExecutionDetailsPage` route registration; implement the page as the execution dashboard in place.
- Global execution history links to `/executions/{id}` and supplies `/executions` as its return context.
- Configuration execution history links to `/executions/{id}` and supplies `/monitoring-configurations/{configurationId}/executions` as its return context.
- Return context is internal route state only. If absent or invalid on direct entry/reload, use `/executions`.
- Do not add a route, fetch current Monitoring Configuration data, or change shell navigation.

## Data contract

- Fetch one `ExecutionDetail` using existing `executionsApi.get(id)` and Feature 006 `GET /api/v1/executions/{executionId}`.
- The existing response is complete. No backend endpoint, DTO extension, persistence model, or migration is in scope.
- Snapshot context always comes from `detail.snapshot`; counters always come from `detail.counters`.
- Use `detail.durationSeconds`, `detail.completionMeaning`, and `detail.error` when present. Do not hardcode alternate mining outcome data or meaning.
- Render only safe snapshot metadata already returned by the execution detail response. Do not query current Monitoring Configuration data, substitute live values, call GitLab, revalidate GitLab entities, or resolve selected groups into repositories.

## Page hierarchy

1. `PageHeader` / execution header prioritizes execution ID, snapshot configuration name, status, and trigger, with return navigation and refresh action.
2. Keyboard-accessible tabs/sections: Overview, Repositories, Findings, Details.
3. Overview: created/started/completed timestamps when available, duration when calculable, snapshot GitLab URL, completion meaning where present, exactly four persisted metric cards, safe error summary where present, and separately summarized selected groups and repositories. The header and Overview collectively provide all required identity and lifecycle information; duplication is optional.
5. Repositories: honest explanation that repository processing details are not available; no rows or fake result types.
6. Findings: honest explanation that finding details are not available; finding count remains a distinct persisted metric; no sample findings.
7. Details: useful safe execution metadata such as ID, trigger, timestamps, normalized error code and safe summary; no raw/debug/internal fields.

## Status and metrics

- Supported wire statuses remain `pending`, `running`, `completed`, `partially_completed`, `failed`.
- Reuse `ExecutionBadge`/`StatusBadge` text, icon, and theme styling; color is supplementary.
- Render all four persisted counter values, including `0`; never label a persisted zero as unavailable.
- An unavailable repository/findings subsection describes absent detail records, not absent counters.

## Loading, errors, refresh

- Initial fetch shows shared accessible loading feedback.
- Normalized 404 shows an execution-not-found message and global history path.
- Other normalized retrieval failures use shared error feedback and retry.
- A manual refresh refetches the same detail endpoint and preserves the selected section/tab.
- Refresh loading and failure feedback remain accessible and normalized; refresh must not query current configuration or GitLab.
- Do not poll, stream progress, open WebSockets/SSE, or make GitLab calls.

## Accessibility and responsive behavior

- One semantic `h1`, ordered section headings, explicit metric labels, accessible tab/list/panel semantics and keyboard operation.
- Loading and retrieval failures use shared live feedback patterns; retry and return actions are keyboard accessible with visible focus.
- Status has visible text and an icon; no color-only communication.
- Snapshot group and repository collections use meaningful list semantics. Long identifiers/paths wrap without losing the full accessible value.
- Use shared design tokens/layout primitives. Metric cards adapt from multiple columns to stacked narrow layout; at 375px, 768px and 1440px the page has no unintended horizontal overflow.

## Prohibited behavior

No repository mining or execution processing, repository/finding entities, fake rows or counts, generated progress, current configuration substitution, GitLab lookups, charts without real data, polling, scheduler, or new chart/state-management dependency.

