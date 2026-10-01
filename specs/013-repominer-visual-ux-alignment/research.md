# Research: RepoMiner Visual & UX Alignment

## Decision 1: Incrementally refactor the existing application

**Decision**: Keep the current React routes, feature modules, API clients, hooks, state flow, Material UI stack, components, and test setup. Reorganize presentation in bounded page/workflow increments and reuse shared components where their behavior genuinely repeats.

**Rationale**: Existing `AppShell`, `Sidebar`, `PageContainer`, `PageHeader`, `ContentCard`, `StatusBadge`, form, feedback, dashboard, tree, and wizard components already establish working conventions. Rebuilding would create unnecessary regression risk and conflict with the specification's migration strategy.

**Alternatives considered**: Replace the frontend shell wholesale; introduce a new UI framework; make independent page-specific styling changes. The first two are out of scope; the last would preserve current inconsistency.

## Decision 2: Add bounded read-only projections where existing list contracts are insufficient

**Decision**: The only approved additive contract projections in Feature 013 are: (1) `GET /api/v1/dashboard/summary` over existing execution, repository execution, and Finding rows; (2) existing schedule data as nullable `scheduleSummary` on configuration list items; and (3) the existing persisted `findingCount` on execution list items. They are additive, read-only, backwards-compatible, derived from existing data, and are not authoritative new domain state. Do not remove, rename, reinterpret, or make existing contract fields/routes/write semantics incompatible. Reuse existing endpoint/DTO data when it cleanly meets the UI need; add no other projection field or endpoint without explicit Feature 013 justification. Implement these as application/read-model projections and SQLAlchemy queries over existing records; aggregate the Home window to the last seven UTC calendar days and return up to five recent executions.

**Rationale**: The current execution-list contract is paginated at 25 by default (maximum 100) and does not expose Finding counts; execution detail has counters but requires a separate request per execution. The configuration list also has no schedule summary and the schedule endpoint is per configuration. Fetching each list item's related endpoint multiplies requests, while a current-page-only aggregate would misrepresent page counts as dashboard totals. These three backward-compatible read-only projections are the narrowest changes for complete, bounded, data-backed presentation; they add no persistence, write behavior, new domain rule, or authoritative state.

**Alternatives considered**: Use current-page totals (inaccurate); issue N schedule/detail calls (request fanout); persist cached analytics (new persistence and stale-data behavior). These alternatives are rejected.

## Decision 3: Define Home metric scope and formulas

**Decision**: Use the seven UTC calendar days beginning at 00:00 UTC six days before the current UTC date and ending at the current instant. Include start and exclude end. Count executions created within this window. Count distinct GitLab project IDs with RepositoryExecution rows under those executions. Count persisted Findings for those executions. Status distribution includes every execution status in the window. Success rate is fully completed executions divided by terminal executions (`completed + partially_completed + failed`), rounded to an integer percent; exclude `pending` and `running` from the denominator, do not count partial completion as full success, and return null when the denominator is zero. Include seven UTC day buckets with zero-filled days and five most recent execution rows. Findings-by-rule includes only rule IDs that have persisted findings. Do not show previous-period comparisons or selectable periods.

**Rationale**: The response is deterministic and grounded in existing records, excludes active work from a terminal outcome ratio, handles empty/active-only windows honestly, and matches the reference's seven-day dashboard direction without copying mock comparisons or adding range-filter behavior.

**Alternatives considered**: All-time aggregation (unbounded visual context), page-scoped aggregation (incomplete), treating partial executions as successful (misleading), fetching comparison windows (extra unrequested presentation), user-selectable period range (not required by spec).

## Decision 4: Keep Authors step compatible and non-misleading

**Decision**: Preserve the current global allowed-author editor as the only active, persisted policy. The Authors wizard step may show a disabled future-policy preview with repository/group context and an explanation that branch/repository policies are unavailable. Do not present active per-row author chips or branch selectors as editable settings. Do not send new fields or alter scope, snapshot, checkpoint, or finding-rule behavior.

**Rationale**: The approved image illustrates a future capability explicitly deferred by Feature 013. The existing global field and Feature 010 rule remain the functional source of truth.

**Alternatives considered**: Bind scope rows to the global allowed-author list (would imply scope-specific policy); accept local edits without persistence (misleading); implement policy storage/discovery (out of scope). All are rejected.

## Decision 5: Compose a five-step UI using existing API boundaries

**Decision**: Use a frontend stepper shell and current feature components/API modules. Preserve current create/update, credential, scope, allowed-author, and schedule API boundaries, validation, ETag behavior, credential clearing, and save/remove semantics. Do not introduce a draft entity or draft API. Keep wizard-only unsaved inputs transient as current forms do; perform mutations only through the existing resource operations at their current form boundaries.

**Rationale**: A visual workflow can be reorganized without adding domain/persistence concepts. Resource APIs already model configuration, GitLab credential, scope, and schedule independently.

**Alternatives considered**: New aggregate wizard API, backend draft state, or a multi-resource transaction. Those would introduce new behavior and persistence or change established contracts.

## Decision 6: Treat reference images as visual guidance, not data or new product behavior

**Decision**: Use the ten supplied images to map layout and hierarchy to the existing pages. Do not copy example values, credentials, user identities, execution metrics, author policies, or other decorative details. Home uses actual persisted data; the Authors image's branch/repository policy controls remain disabled explanatory UI.

**Rationale**: Reference precedence explicitly places functional behavior and scope above decorative image content.

**Alternatives considered**: Treat all image elements as requirements or fixtures; this would introduce unsupported analytics and author-policy behavior and is rejected.

## Repository/API observations

- Frontend routes already include Home, Monitoring Configurations, Executions, and Settings in `src/app/routes/routeConfig.tsx` and `src/app/routes/navigation.tsx`.
- Home is currently placeholder content in `src/features/home/pages/HomePage.tsx`.
- `src/features/executions/api/executionsApi.ts` exposes paginated execution list/detail/repository requests; `ExecutionListItem` lacks Finding and repository counters while `ExecutionDetail` has aggregate counters.
- Backend execution list is paginated (`pageSize` maximum 100) and does not accept date bounds; execution details expose per-execution counters. Finding and repository rows are persisted separately.
- Existing frontend has Material UI, Material Icons, Vite, Vitest, React Testing Library, and axe-core. No dependency addition is needed.
- Backend uses FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Alembic and pytest. No schema change is needed for summary projection.

## Reference inventory reviewed

`01-home-dashboard.png`, `02-monitoring-configurations.png`, `03-new-configuration-general.png`, `04-gitlab-connection.png`, `05-scope-selection.png`, `06-author-policies.png`, `07-scheduling.png`, `08-executions-list.png`, `09-execution-findings.png`, and `10-commit-diff-modal.png` in `references/`.
