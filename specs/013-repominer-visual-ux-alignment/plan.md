# Implementation Plan: RepoMiner Visual & UX Alignment

**Branch**: `013-repominer-visual-ux-alignment` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

## Summary

Align the existing React application incrementally around its current application shell, shared visual primitives, five-step Monitoring Configuration workflow, Home dashboard, configuration list/details, execution history/details, Findings, and commit-diff dialog. Existing route, API, state, credential, scope, schedule, execution, mining, checkpoint, Finding, and diff behavior remains authoritative. Three additive read-only projections are planned: a Home aggregation response, a schedule summary on configuration-list rows, and persisted Finding count on execution-list rows. These avoid per-row schedule/detail request fanout; they expose only values already persisted and create no new persistence.

The approved reference images inform composition and visual hierarchy, with the Authors image treated as a future-policy visual shell only: the active global allowed-author editor remains the sole editable policy in Feature 013; repository/branch policy affordances are explanatory and disabled.

## Technical Context

**Language/Version**: TypeScript 5.x, React 19, Python 3.13–3.14
**Primary Dependencies**: Existing React Router, Material UI, Material Icons, Vite, FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Alembic, pytest, Vitest, React Testing Library, axe-core
**Storage**: Existing PostgreSQL entities only; no schema changes or migrations
**Testing**: Existing frontend Vitest/component/accessibility suites and backend pytest/API suites
**Target Platform**: Existing desktop-first browser application with tablet/narrow viewport support; existing FastAPI service
**Project Type**: Existing frontend plus backend web application
**Performance Goals**: Keep dashboard summary to one bounded read request; do not load execution details in an unbounded per-row loop. Home summary window is seven UTC calendar days, with at most five recent execution rows.
**Constraints**: Preserve backward compatibility for Features 001–012 public API contracts. The only approved additions are three narrow, additive, read-only projections derived from existing data: Home summary, configuration `scheduleSummary`, and execution `findingCount`. They add no persistence, business rule, write behavior, or authoritative domain state. No new UI framework, migration, mining behavior, author-policy behavior, or unsupported analytics.
**Scale/Scope**: Existing four primary navigation routes and associated configuration, execution, Findings, and diff screens. Refactor in independently reviewable page/workflow increments.

## Constitution Check

- **Clean Architecture and Responsibility Boundaries**: Pass. The Home summary calculation is an application query over a repository port; SQL aggregation remains in infrastructure and the HTTP response mapping remains in API.
- **Domain-Centered Business Rules**: Pass. Existing domain rules are not reimplemented. The summary is a projection of persisted outcomes, not a new mining rule or execution policy.
- **Explicit, Versionable Contracts**: Pass. Three additive read-only projections are documented in the Home summary contract and existing list DTO contracts. They preserve routes, existing fields and meanings, and all write semantics; they are backward-compatible presentations of persisted data, not new domain state.
- **Abstracted External Integrations**: Pass. No new external integration is introduced; existing GitLab access remains unchanged.
- **Secure by Construction**: Pass. Dashboard output contains only existing safe execution/repository/Finding fields and never includes credentials or raw provider data.
- **Immutable and Reproducible Execution History**: Pass. The UI presents existing snapshots and never rewrites history.
- **One Controlled Mining Pipeline**: Pass. Manual and scheduled processing are untouched.
- **Observable Execution Lifecycle**: Pass. Existing statuses/timestamps remain displayed without UI-side status mutation.
- **Migration-Managed Persistence**: Pass. No persistence or schema change is planned.
- **Risk-Based Automated Verification**: Pass. Each migrated flow retains existing regression tests; dashboard summary receives use-case/API tests; responsive and accessibility tests cover shared changes.
- **Deliberate, Reusable User Experience**: Pass. Shared components are limited to genuinely repeated presentation and all affected async states are retained.
- **Incremental Simplicity and Justified Dependencies**: Pass. No dependency is added. Work is split by shell, page, workflow, and result presentation.

No constitution exception is requested. These read-only additions comply with the constitution: Home aggregates existing persisted rows without analytics persistence; `scheduleSummary` projects the existing MonitoringSchedule; `findingCount` counts existing persisted Finding rows. None changes a business rule, introduces a write operation, or breaks an existing contract.

## Approved Reference Images

All ten images under `references/` were inspected. They guide composition and sizing only; they add no business requirements.

| Reference | Existing target | Planning use and boundary |
|---|---|---|
| `01-home-dashboard.png` | `HomePage` | Four metric cards, execution trend/status visualizations, recent executions and rule summary; display only values derived from persisted data. The “Last 7 days” label anchors the bounded summary window; no period selector or comparison metrics are added because those interactions are not required by the spec. |
| `02-monitoring-configurations.png` | `MonitoringConfigurationsPage` | Page heading/action, search, configuration table, status, schedule, and row actions. |
| `03-new-configuration-general.png` | New/edit configuration workflow | Breadcrumb, five-step progress, grouped form card, clear Back/Next actions. |
| `04-gitlab-connection.png` | `GitLabConnectionPanel`, `GitLabCredentialForm` | URL/credential section, validation feedback and safe token interaction. Never reproduce example secrets or identities. |
| `05-scope-selection.png` | `GitLabScopePage`, `RepositoryTree`, `SelectedItemsPanel` | Hierarchical selection and selected-scope summary, preserving dynamic group semantics. |
| `06-author-policies.png` | Authors wizard step | Visual direction for selected-scope rows only. Repository/branch author controls are disabled with an explanatory future-availability state; the current global author list remains the only active editor. Do not imply per-row policy persistence. |
| `07-scheduling.png` | `ScheduleSection`, `ScheduleForm`, `NextOccurrencePreview` | Recurrence/time/timezone, enable state, preview, and existing save/remove actions. |
| `08-executions-list.png` | `ExecutionsPage`, `ExecutionHistory` | Filters, trigger/status columns, timestamps, Finding counts where existing list/summary data supports them, and manual action. |
| `09-execution-findings.png` | `ExecutionDashboardPage`, Findings tab | Preserve four tabs and persisted Finding data/action; branch text from the mock is not a new authorization-policy feature. |
| `10-commit-diff-modal.png` | Existing Feature 011/012 dialog | Preserve modal shell, metadata, changed-file sidebar, selected-file treatment, and split viewer; visual polish only. |

## Architecture and Data Flow

### Frontend

Continue in the existing `src/app`, `src/shared`, and feature-first `src/features` modules. Keep route definitions in `src/app/routes/routeConfig.tsx`, primary navigation in `src/app/routes/navigation.tsx`, theme tokens/theme in `src/app/theme/`, and page-specific business/API behavior in its current feature modules. Refactor presentation around existing `AppShell`, `Sidebar`, `PageContainer`, `PageHeader`, `ContentCard`, `StatusBadge`, form, dashboard, feedback, and wizard components before adding new shared components.

Use a five-step presentation shell for new and edit configuration flows. Existing service boundaries remain authoritative: configuration create/update through current configuration APIs; GitLab URL/credential validation and credential save/remove through existing connection APIs; scope read/replace through existing scope APIs; allowed author emails through the existing configuration update contract; and schedule preview/save/remove through existing schedule APIs. Credentials stay in the existing transient token input and are cleared after submit. New configuration creation continues to use the required existing fields and resource APIs; do not create a draft entity, draft endpoint, or persistence. The Authors step keeps the global author editor functional; future branch/repository policy previews are non-interactive and marked unavailable.

### Read-only presentation projections

The current `GET /executions` response is paginated and has no Finding count. `GET /executions/{id}` returns Finding counters but requires a request per row. The configuration list response does not contain a schedule; the schedule endpoint is per configuration. Home requires multi-execution counts, distinct processed repository totals, Finding totals, status and date buckets. Therefore make the following additive, read-only contract extensions over existing data:

- Add `findingCount` to each execution list item as a read-only count of existing persisted Finding rows associated through RepositoryExecution. Do not change filtering, pagination, ordering, Finding detection, or execution lifecycle.
- Add a nullable structured `scheduleSummary` projection to configuration-list items using one left join/read projection to existing schedule rows. Do not call the per-configuration schedule endpoint once per table row. The projection contains configured state, recurrence fields, local execution time, timezone, and schedule enabled state; no next-occurrence calculation or mutation is added.
- Add `GET /api/v1/dashboard/summary`, described below.

These are backward-compatible read projections, not new business rules. Existing API fields and actions are retained. No migrations, caching, provider calls, or persistence are introduced.

### Home summary boundary

The current execution-list response cannot provide complete counts or period buckets. Therefore add one bounded read-only `GET /api/v1/dashboard/summary` query over existing MiningExecution, RepositoryExecution, and Finding persistence. Use an application query/use case and repository-port method; put efficient aggregation in the SQLAlchemy repository adapter. No new table, cache, scheduler behavior, or mutation route is introduced.

The query covers the last seven UTC calendar days, from 00:00 UTC six days before the current UTC date through the current instant (start inclusive, end exclusive when represented as a boundary). It also returns the five most recent executions in that window. “Repositories processed” is the number of distinct GitLab project IDs represented by RepositoryExecution rows whose parent execution was created in the window. Finding count is based on persisted Finding rows. Status distribution counts all executions created in-window, including pending/running. Success rate is `completed / (completed + partially_completed + failed)`, rounded to a whole percent; pending/running are excluded from the denominator and partial completion is not counted as a fully successful execution. Return null when the denominator is zero. Daily trend groups execution creation timestamps by UTC date and includes all seven dates, including zeros. Rule breakdown includes only persisted Finding rules with actual records. No “previous period” comparison is calculated.

### Shared visual foundation

Reuse existing visual primitives first. Extend or add only when a concept genuinely repeats:

- `AppShell`/`Sidebar`/`MobileNavigation`: persistent desktop nav and the existing narrow-screen navigation affordance.
- `PageContainer`/`PageHeader`/`AppBreadcrumbs`: shared content width, title/subtitle/action placement, and breadcrumbs.
- `ContentCard`/dashboard grid and metric cards: consistent card padding and responsive grids.
- `StatusBadge`, feedback `LoadingState`/`EmptyState`/`ErrorState`, form group/actions, and `WizardShell`: existing building blocks standardized across affected pages.
- Shared table presentation is a style/composition convention using semantic MUI tables; avoid a generic table engine unless multiple pages need the same behavior.
- MUI `IconButton` requires an accessible name and supplementary tooltip when the action is not self-describing.

Use current palette/theme tokens, visible focus styles, existing semantic controls, and controlled local overflow. Do not introduce a second component framework or replace existing routing/state/query behavior.

## Page and Workflow Design

### Application shell and Home

The shell keeps exactly the four supported primary entries. Home has four persisted-data cards (execution count, distinct repositories processed, Findings count, success rate), a seven-day execution-created trend, status distribution, five recent executions, and Findings grouped by actual rule. Home uses one summary request with loading/error/retry/empty states. If the aggregate is empty, cards show zero where the response supports zero; success rate is unavailable/null with accessible explanatory text. There are no fake fixture metrics in production.

### Monitoring Configurations and details

Keep current list/search and CRUD/actions, redesigning the layout to the reference table. Use the additive `scheduleSummary` list projection to display recurrence/time/timezone and configured/disabled state without per-row fetches. Configuration details group existing fields, connection panel, schedule, execution history, and manual action into sections while retaining their exact current callbacks/API semantics.

### Five-step configuration flow

The stepper is a presentation structure, not a new domain aggregate:

1. **General**: name, description, and existing enabled field where editing behavior supports it.
2. **GitLab connection**: instance URL plus the existing credential save/replace/remove and validation UX. Token values remain transient and are never redisplayed.
3. **Scope**: existing hierarchical GitLab tree, search, multiple selection, summary, unavailable selections, and dynamic group intent.
4. **Authors**: existing global allowed-author editor remains active and maps to the existing configuration field. Show an explicitly unavailable, disabled preview for future repository/branch policy layout, if that presentation is included; do not show active per-scope editable chips or selectors that could imply supported behavior.
5. **Scheduling**: existing recurrence, local time, timezone, enablement, preview, and removal behavior.

Use current API mutation boundaries and ETag/version conflict behavior. No branch discovery, policy DTO, database schema, snapshot change, or rule change. The screen can use one wizard shell with step-specific existing feature components; it must not duplicate API/business logic in the wizard.

### Execution list and details

Keep `ExecutionHistory` filters, pagination, return links, and `ManualExecutionAction`. Add `findingCount` as the read-only count of persisted Finding rows associated with each execution through RepositoryExecution, so the reference Findings column is complete without per-row detail fetches. Provide the existing manual execution action from the Executions page by selecting a Monitoring Configuration from the existing list and invoking the existing action/API; do not create a new execution path or mutation contract.

Preserve the four `ExecutionDashboardPage` tabs and the existing components for Overview, Repositories, Findings, and Details. Align table/card hierarchy and status presentation without changing historical snapshot or refresh semantics. The Home summary endpoint does not replace detail/list endpoints.

### Findings and commit diff

Retain existing Finding query/state, supported Unauthorized Commit Author content, and `Difference` action. Preserve Feature 011 on-demand Finding-ID-only lookup, secure credential and historical GitLab instance validation, Feature 012 split row alignment, file sidebar, independent line numbers, binary/large/truncated/completeness states, safe errors/retry, and modal accessibility. Only shared spacing, palette/theme alignment, shell, and dialog proportions may change.

## API Contract and Persistence

The only approved backend contract additions are [`contracts/home-dashboard-summary.md`](contracts/home-dashboard-summary.md) and additive read-only `scheduleSummary` and `findingCount` fields in the existing configuration/execution list DTOs. They are backwards-compatible projections from existing persisted data, not authoritative new domain state. Preserve every existing field, meaning, route, filter, ordering, and write semantic. Reuse existing endpoint/DTO data when it cleanly satisfies the presentation need; do not add any further projection field or endpoint without a Feature 013 requirement and explicit justification. These additions contain no credentials, raw provider data, author email aggregation, or new Finding category, and require no migration/database entity.

## Testing Strategy

- Shared shell: route links, active route, desktop sidebar, narrow navigation, controlled content width/overflow.
- Home: contract/unit/API tests for aggregation math and UTC boundaries; frontend tests for real response, all-zero/no-terminal state, loading, safe error/retry, recent rows, and no fabricated metrics. Verify one bounded request and no per-execution detail fanout.
- Config list/details: table/search/actions/status/schedule presentation; verify the joined schedule summary avoids per-row requests and preserves create, update/ETag, enable/disable, delete, manual execution, and details behavior.
- Wizard: five-step navigation and existing create/edit flow; GitLab URL and credential behavior, scope selection/reconciliation, global allowed authors, disabled future policy shell, and schedule lifecycle/preview/dirty-navigation behavior. Assert disabled future controls send no requests and persist no new fields.
- Execution list/details: existing filters/pagination/manual trigger, persisted list Finding counts, and all four tabs, historical values, repository results, Findings and safe errors.
- Diff: run existing Feature 011/012 regression suite for on-demand fetch, large dialog, sidebar, split alignment, file states, safe errors, and focus/accessibility.
- Accessibility: update shell, navigation, forms/wizard, tables/status, Home charts/tables, modal/icon controls; run existing axe/accessibility tests and keyboard/focus assertions.
- Responsive: component-level assertions at supported breakpoints and manual viewport review against the supplied references. Do not rely solely on pixel screenshots.
- Backend: focused unit/application/API tests for dashboard aggregation; existing backend suites remain regression validation if backend code changes. PostgreSQL integration is not required for the new endpoint because it adds no persistence or database-specific constraint, but run applicable existing backend tests.
- Final: frontend full suite, backend applicable suite, production builds, and manual visual review; report reference review separately from automated tests.

## Delivery Phases

1. **Shared foundation**: audit existing design primitives, tune theme tokens and common page/table/status/feedback composition. Avoid broad rewrite.
2. **Application shell**: refine persistent sidebar, active route, content sizing, and responsive navigation.
3. **Home**: implement the bounded aggregation use case/contract/API and data-driven dashboard.
4. **Configuration list/details**: align table and grouped details while retaining actions and state.
5. **Wizard foundation and General/GitLab/Scope**: compose the stepper around existing components and APIs.
6. **Authors visual shell**: preserve global author editor and show future branch/repository controls only as disabled/explanatory UI.
7. **Scheduling**: integrate existing recurrence form/preview/lifecycle into the wizard without changing semantics.
8. **Executions**: align execution history and manual action using existing data contracts.
9. **Execution Details/Findings**: standardize four tabs and data presentation.
10. **Commit Diff polish**: align existing large split-diff dialog without touching retrieval or parser.
11. **Cross-cutting validation**: accessibility, responsive layout, full relevant suites/builds.
12. **Manual visual validation**: compare all ten references to their corresponding pages and record intentional functional differences, especially the disabled Authors future-policy shell.

## Source Structure

```text
src/
├── app/
│   ├── layout/                         # AppShell, Sidebar, MobileNavigation
│   ├── routes/                         # Existing route/navigation definitions
│   └── theme/                          # Existing theme and design tokens
├── shared/
│   ├── components/layout/              # PageContainer, PageHeader, ContentCard
│   ├── components/navigation/          # Breadcrumbs
│   ├── components/status/               # StatusBadge
│   ├── components/feedback/             # Loading/empty/error states
│   ├── components/form/                 # Form groups/actions
│   ├── components/wizard/               # WizardShell
│   └── components/dashboard/             # Dashboard cards/grid/chart container
├── features/
│   ├── home/                             # Home page and dashboard summary API/types
│   ├── monitoring-configurations/        # List, details, five-step flow, existing APIs
│   └── executions/                       # History, four detail tabs, Findings, diff modal
└── test/
    ├── app/                              # Shell/routes/responsive tests
    ├── shared/                           # Shared component tests
    ├── accessibility/                    # Application accessibility checks
    └── features/                          # Page and workflow regression tests

backend/app/
├── api/v1/dashboard.py                   # Additive read-only summary route/schema
├── application/use_cases/get_dashboard_summary.py
├── application/ports/dashboard_summary_repository.py
└── infrastructure/database/              # SQLAlchemy aggregate query; no schema change
backend/tests/
├── unit/                                  # Aggregation/use-case tests
└── api/                                   # Summary response/security/empty tests
```

The exact file split may follow existing local conventions, but route/query/business boundaries and scope above remain fixed. Avoid editing the same page/component from parallel tasks.

## Risks and Mitigations

- **Wizard changes can disrupt existing APIs or data timing**: reuse API modules/hooks and preserve ETags, resource boundaries, token-clearing, and scope/schedule lifecycle tests.
- **Authors reference can mislead users**: visibly mark future repository/branch controls unavailable; keep global list as the only active editable policy and test that unavailable controls do not issue mutations.
- **Home can imply unsupported analytics**: fixed seven-day bounded aggregation, explicit metric formulas, actual persisted records only, no previous-period comparisons, and no chart categories without real records.
- **Repeated screens can create over-abstraction**: prefer existing shared components and add new primitives only for genuinely reused visual behavior.
- **Image examples may contain sample values**: do not copy identities, URLs, tokens, counts, dates, branch policy examples, or other fixture content into application defaults.

## Complexity Tracking

| Addition | Justification | Simpler alternative rejected because |
|---|---|---|
| Read-only Home dashboard summary and additive list projections | The paginated execution list lacks Finding counts; configuration list lacks schedule summary; Home needs multi-execution aggregate counts. Read projections avoid N+1 calls and derive only existing persisted values. | Fetching schedule/detail for every row multiplies requests; using current-page totals would mislabel page-scoped values as complete dashboard totals. |
