# Implementation Plan: Execution Dashboard

**Branch**: `007-execution-dashboard` | **Date**: 2026-09-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature 007 specification and planning constraints supplied by the user.

## Summary

Turn the existing `/executions/:id` execution detail page into a structured, accessible dashboard using the Feature 006 `GET /api/v1/executions/{executionId}` detail response. The existing response contains every required persisted field and its safe historical snapshot projection, so this feature needs no API, domain, persistence, or migration changes. Work is confined to the existing React execution feature: organize its header, lifecycle and metrics, snapshot/scope, safe errors, and explicit repository/findings unavailable states; retain loading/error/retry behavior; and preserve history context when navigating from either execution list.

## Technical Context

**Language/Version**: TypeScript with React; Python 3.13–3.14 backend remains unchanged  
**Primary Dependencies**: Existing Vite, Material UI, React Router, FastAPI, SQLAlchemy and Pydantic stack; no new dependencies  
**Storage**: Existing PostgreSQL MiningExecution and immutable snapshot, read through Feature 006; no schema changes  
**Testing**: Vitest, Testing Library, user-event and axe-core for frontend; existing pytest API contract is reused unchanged  
**Target Platform**: Existing browser application and its current API service  
**Project Type**: Web application with a React frontend and Clean Architecture Python API  
**Performance Goals**: No feature-specific latency target is specified. Preserve the existing single detail request and loading behavior; add no polling, timer, or extra configuration/GitLab request.  
**Constraints**: Render only persisted execution fields and safe snapshot display metadata; preserve Feature 006 contract and lifecycle semantics; accessible responsive behavior follows Feature 001; no charts or new dependencies.  
**Scale/Scope**: One Mining Execution per dashboard, with snapshot group and repository selections displayed as captured. No new scale or volume target is introduced.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / gate | Assessment |
|---|---|
| Clean Architecture and responsibility boundaries | Pass. This is presentation work over a read contract. No domain rule, persistence behavior, or infrastructure responsibility moves into UI. |
| Domain-centered business rules | Pass. Lifecycle/status/counters remain authoritative in Feature 006; the UI formats and presents them without recomputing mining outcomes. |
| Explicit, versionable contracts | Pass. Reuse the existing execution detail DTO and frontend type. No API changes are indicated. |
| Abstracted external integrations | Pass. The dashboard makes no GitLab request; historical scope comes from the execution detail response. |
| Secure by construction | Pass. Use only safe DTO fields; no raw snapshot, credentials, fingerprints, or internal execution metadata are rendered. |
| Immutable execution history | Pass. Show snapshot fields from the execution and never substitute current configuration data. |
| One controlled mining pipeline | Pass. No execution creation or processing behavior is changed. |
| Observable execution lifecycle | Pass. Present the persisted status and timestamps. No lifecycle transitions or recovery worker are introduced. |
| Migration-managed persistence | Pass. No schema or persistence changes. |
| Risk-based automated verification | Pass. Frontend tests cover lifecycle states, safe data, empty/error paths, navigation, responsiveness, and accessibility. Existing backend contract/security tests remain the source of evidence for the unchanged API. |
| Deliberate, reusable user experience | Pass. Reuse shell, PageHeader, StatusBadge, MetricCard, ContentCard, and shared feedback components. Provide keyboard-accessible sections and all relevant page states. |
| Incremental simplicity and justified dependencies | Pass. No charting library, state-management package, endpoint, read model, or other dependency is warranted. |

**Gate result**: Pass. No constitutional exception or complexity justification is needed.

## Project Structure

### Documentation (this feature)

```text
specs/007-execution-dashboard/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    └── dashboard-ui.md
```

### Source Code (repository root)

```text
src/
├── app/routes/
│   ├── routeConfig.tsx                  # Keep /executions/:id; mount dashboard page
│   └── navigation.tsx                   # No shell redesign or primary navigation change
├── features/executions/
│   ├── api/executionsApi.ts             # Reuse get(id) without a new endpoint
│   ├── types/execution.ts               # Reuse existing ExecutionDetail contract type
│   ├── pages/
│   │   ├── ExecutionDetailsPage.tsx      # Evolve/rename implementation to ExecutionDashboardPage
│   │   └── ExecutionsPage.tsx            # Existing global history
│   └── components/
│       ├── ExecutionHistory.tsx          # Preserve global/configuration entry context
│       ├── ExecutionHeader.tsx           # Owns execution ID, snapshot configuration name, status and trigger
│       ├── ExecutionMetrics.tsx
│       ├── ExecutionOverview.tsx          # Owns overview lifecycle, snapshot, scope, metric and safe-error presentation
│       ├── ExecutionErrorSummary.tsx
│       ├── ExecutionRepositoriesSection.tsx
│       ├── ExecutionFindingsSection.tsx
│       └── ExecutionDetailsSection.tsx
├── shared/components/
│   ├── dashboard/MetricCard.tsx
│   ├── feedback/{LoadingState,ErrorState,EmptyState,PlaceholderState}.tsx
│   ├── layout/{ContentCard,PageContainer,PageHeader}.tsx
│   └── status/StatusBadge.tsx
└── test/
    ├── features/executions/              # Dashboard, history and accessibility coverage
    ├── app/                              # Existing route/navigation tests
    └── features/responsiveLayouts.test.tsx
```

**Structure Decision**: Use the existing single React application and `src/features/executions` boundary. Keep feature-specific presentation components local to executions. Keep `/executions/:id` and the shared application shell intact. Backend paths are not part of this feature's change set.

## Design Decisions

### Execution detail contract and backend scope

The existing `GET /api/v1/executions/{executionId}` response provides the ID, status, trigger, snapshot configuration name and GitLab URL, selected group/repository metadata, lifecycle timestamps, `durationSeconds`, all four counters, nullable safe `{code, summary}` error data, and nullable `completionMeaning`. The Feature 006 DTO is an explicit safe projection; it omits credentials, internal fingerprints, raw snapshot data, and persistence/concurrency fields. `src/features/executions/types/execution.ts` already models this response and `executionsApi.get(id)` already calls this endpoint.

Therefore Feature 007 adds no endpoint, DTO/read model, domain/application use case, migration, or backend tests. Continue to rely on Feature 006 API tests for projection and non-disclosure. Reconsider this only if implementation discovers a required safe persisted field absent from that contract; any such change must be a minimal additive detail-contract extension with corresponding API/security tests and no persistence change.

### Page composition and presentation boundaries

The existing `ExecutionDetailsPage` becomes the real dashboard at the same route. Compose the page from shared `PageContainer`/`PageHeader`, `ExecutionHeader`, and keyboard-accessible Overview, Repositories, Findings, and Details tabs. Place exactly four `MetricCard`s inside Overview so its required summary counters are present. Tabs use Material UI semantics and retain their selected value during refresh. Feature components accept the typed detail DTO and own only presentation; they do not fetch configuration state, calculate mining results, or implement shared shell rules.

`ExecutionHeader` owns execution identity (including ID), snapshot Monitoring Configuration name, status, and trigger. `ExecutionOverview` owns created/started/completed timestamps when available, API-provided duration when calculable, snapshot GitLab URL and other historical snapshot details, completion meaning when provided, the persisted counters through `ExecutionMetrics`, separate selected group and repository scope summaries, and safe execution error information where appropriate. The header and Overview collectively present the required identity and lifecycle context; fields may appear in both only where useful. Keep these responsibilities execution-feature-specific. Do not create separate `ExecutionStatusSummary`, `ExecutionSnapshotSummary`, or `ExecutionScopeSummary` files unless implementation later demonstrates a clear reuse or complexity need. Details can focus on safe execution metadata without forcing duplicate presentation. `StatusBadge` supplies existing status label, icon and theme styling for all five supported states.

### Data fetching, duration, and recovery

Keep the existing `executionsApi.get(id)` and page-local fetch state pattern. Preserve request cleanup against stale responses. Initial load uses `LoadingState`; a normalized 404 renders an execution-not-found view with a history link; other failures use `ErrorState` and a keyboard-operable retry. Provide a manual refresh action that refetches this same detail resource, announces loading state, and preserves whichever tab is selected across Overview, Repositories, Findings, and Details. Render refreshed data in that active section and never reset to Overview as a refresh side effect. Do not poll or implement live updates.

Use API `durationSeconds` where non-null and the existing date formatter for timestamps; do not persist or independently recompute duration in multiple components. A pending execution has no duration. Feature 006 does not return a running elapsed duration under its existing contract, so show no duration for running rather than add a timer. Final duration is shown only when API timestamps support it. Missing timestamps remain an em dash/explicit unavailable display consistent with current history presentation.

### Snapshot, scope, and completion meaning

Read configuration name, GitLab URL, and separately listed selected groups and repositories only from safe snapshot metadata already returned by the execution detail API. Label this as historical execution context. Render each selected item's available safe name/full path; an empty scope list says no items were selected. Do not query the current Monitoring Configuration, substitute live values, call GitLab, revalidate GitLab entities, or resolve selected groups into repositories. The dashboard remains a historical read-only view over Feature 006 execution data.

Render `completionMeaning` directly from the response and only when non-empty. This keeps the API as the single source for the approved Feature 006 message. Do not copy that message into a competing frontend constant. Error display uses only the response's safe code and summary and appears only when an error object is present; no raw error/debug details are introduced.

### Counters versus unavailable details

`ExecutionMetrics` renders exactly Repositories, Successful repositories, Failed repositories, and Findings from their persisted counter fields. `0` remains a displayed count. Repository and Findings tabs have distinct honest unavailable/empty states because repository-level execution/finding records are not part of Feature 007. Their wording must explain that detail records are not available for this execution at this stage; it must not suggest that a zero counter itself is missing data. Do not create fake rows or types for those records.

### Navigation and history context

Keep both history links targeting `/executions/:id`. When a dashboard is opened from global history, its return path is `/executions`; when opened from a configuration history, preserve `/monitoring-configurations/:configurationId/executions` as internal route state. The dashboard uses this safe, application-local return path for a back link/breadcrumb. On direct entry, missing or invalid route state falls back to `/executions`. Do not fetch the current configuration to construct this navigation. Existing shell breadcrumbs and active primary navigation remain unchanged.

### Responsive and accessible behavior

Reuse Feature 001 theme roles, spacing, `PageContainer`, cards, grid patterns, and breakpoint conventions. Metrics use a four-column wide layout, reduce columns at medium widths, and stack on narrow widths. Tabs remain keyboard-operable and locally contained; snapshot paths/IDs wrap safely rather than causing page overflow. At 375px, 768px, and 1440px, page content remains readable without unintended page-level horizontal scrolling.

Use one semantic page heading, hierarchical section headings, accessible tabs/tab panels, explicit metric labels, text-plus-icon status, labeled scope lists, live loading feedback, alert error feedback, visible keyboard focus, and logical focus order. Reuse `StatusBadge`, which includes a text label and icon so color is supplemental. Validate with existing axe-core conventions and keyboard interaction tests; automated checks supplement, not replace, review of keyboard use and responsive layout.

### Tests and intentional dependency decisions

Extend existing execution detail tests and fixtures rather than building a second harness. Name the contrasting test data explicitly (for example, `historicalExecutionDetail` and `liveMonitoringConfiguration`): give the execution snapshot a historical name, URL, and group/repository scope, and give the current configuration fixture different live values. Assert that only historical values appear and that rendering requests only the execution detail; no current-configuration API lookup is required. Cover loading, not-found, normalized API error/retry, all five statuses, all persisted counters including zero, completion meaning presence/absence, safe error rendering, section-specific empty states, both history entry/return paths, tab keyboard/ARIA behavior, and representative responsive widths. For manual refresh, parameterize across Overview, Repositories, Findings, and Details; verify accessible loading, refetch and changed execution values rendered in the selected context, retained tab selection with no reset to Overview, normalized error feedback on failure, and no current-configuration or GitLab requests. Reuse existing `renderApp`, Vitest, Testing Library, user-event and axe-core conventions; add no polling or live updates.

No backend tests are added because the execution detail contract is unchanged. Feature 007 does not depend on deferred PostgreSQL-specific validation work from Feature 006 (including T036/T037); those Feature 006 limitations do not change frontend-only completion status. No charting dependency is introduced: counters and snapshot metadata have no meaningful time-series or category distribution to chart. Feature 008 repository processing and Feature 010 findings remain deferred and are not simulated.

## Complexity Tracking

No constitution violations or added project/dependency complexity. No entries required.

## Constitution Check (Post-Design)

| Gate | Result after design |
|---|---|
| Read-only presentation, no duplicated model or business rules | Pass |
| Historical snapshot immutability and safe projection | Pass |
| Existing API contract reuse and consistent terminology | Pass |
| No GitLab access, mining, findings, or scheduling behavior | Pass |
| Accessible, responsive shared-design-system presentation | Pass |
| Automated tests proportionate to status, privacy, navigation and UI states | Pass |
| New persistence, migration, endpoint, or dependency | None |

**Post-design gate result**: Pass. Design is ready for task generation.

