# Repository Dashboard Contract

## Entry and data source

- Reuse the existing `/executions/:id` page and `ExecutionRepositoriesSection`.
- Fetch repository history from `GET /api/v1/executions/{executionId}/repositories` only; do not call GitLab or retrieve current Monitoring Configuration state.
- The execution detail counters remain authoritative; repository list rows come only from persisted RepositoryExecution DTOs.
- Keep the Findings section unavailable for detailed findings until Feature 010. Do not create sample rows, fabricated result types, or analytics.

## Repository rows

Use an accessible semantic table or definition/list layout consistent with existing components. Each row exposes:

- repository full path/name;
- textual status and existing icon/style (color is supplementary);
- processed branch/reference;
- file count;
- finding count (persisted value, zero for Feature 008);
- start/completion timestamps when present;
- normalized safe error code/summary for failed rows.

Long names, paths, IDs, and branch strings wrap without hiding their accessible values. No raw provider data or error text is rendered.

## Loading, error, and empty states

- Initial section request has a perceivable accessible loading state.
- Normalized API errors use shared error feedback and a keyboard-accessible retry; retain the current dashboard tab.
- A completed execution with `repositoryCount=0` and an empty repository list is a valid empty effective scope, not an error.
- A pending/running execution with zero repository rows explains that repository records are not available yet.
- A failed execution with no repository rows explains that processing ended before repository rows were available and may show the safe execution-level error already returned by execution detail.
- A non-empty list displays only returned rows and API pagination; no fabricated placeholders are used as repository records.

## Accessibility and responsiveness

- Preserve existing tabs and keyboard behavior; repository list heading is under the current dashboard section hierarchy.
- Status/error meaning is textual and not color-only.
- Table headers associate labels with cells, or a semantic list has explicit labels.
- Loading/error announcements and retry actions follow shared accessible feedback conventions.
- At 375px, 768px, and 1440px use responsive columns or a readable narrow layout with no forced page-level horizontal overflow.

## Refresh and lifecycle

The repository list may be fetched when its tab is opened and manually retried. No polling, SSE, WebSockets, progress stream, current-configuration query, or provider request is initiated from the browser. The Findings tab remains an honest unavailable state.
