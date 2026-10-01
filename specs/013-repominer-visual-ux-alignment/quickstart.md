# Feature 013 Validation Quickstart

## Prerequisites

- Use the Feature 013 directory selected by `.specify/feature.json`.
- The ten approved images are under `specs/013-repominer-visual-ux-alignment/references/`.
- Do not use real GitLab credentials in automated tests. Use mocked provider/test configuration.

## Inventory and reuse points

- Existing routes, desktop `AppShell`, `Sidebar`, and mobile navigation live in `src/app/`; Feature 013 retains their route and navigation behavior.
- Existing Material UI theme tokens, `PageContainer`, `PageHeader`, `ContentCard`, `StatusBadge`, feedback states, dashboard cards, and wizard/form primitives are reused under `src/app/theme/` and `src/shared/components/`.
- Configuration CRUD/API clients, GitLab credential panels, hierarchical scope, global allowed-author editing, schedule forms/previews, and execution actions remain in their feature components and hooks under `src/features/monitoring-configurations/` and `src/features/executions/`.
- Execution history/details, repository results, Findings, and the on-demand Feature 011/012 split diff remain under `src/features/executions/`; no second API/client/pipeline was added.
- Backend projections are application queries/read models over existing SQLAlchemy execution, repository execution, schedule, and Finding rows. No entity or migration was added.

## Automated validation record — 2026-09-30

The standard Vitest config loader hit a Windows `spawn EPERM`. The complete existing frontend suite passed using Vitest's runner config loader:

```powershell
npx vitest run --configLoader runner
npm run build
```

Result: frontend **45 test files / 187 tests passed**. The suite includes the existing axe-based accessibility checks. Production build passed; Vite emitted a large-chunk advisory (approximately 800 kB before gzip).

The full backend suite passed with the scheduler disabled for the test process. Legacy `TestClient` fixtures otherwise start the Feature 009 runner, which can wait on its configured scheduler loop. This test-only setting does not change application runtime behavior:

```powershell
$env:SCHEDULER_ENABLED='false'; .\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests -q
```

Result: **316 passed, 32 skipped**. PostgreSQL integration tests were skipped because `TEST_DATABASE_URL` is unavailable. PostgreSQL-specific validation remains pending. Backend `compileall` also passed. The focused Feature 013 dashboard, configuration, schedule, and Finding API tests passed, including UTC window calculation, seven zero-filled dates, status and success-rate/null behavior, SQL projection checks for distinct repositories and bounded recent execution ordering, additive `scheduleSummary`, and persisted Finding count projection through repository ownership.

## Manual visual review

All ten supplied images were inspected as layout guidance. Live manual comparison remains **open**: the Windows computer-use runtime failed to initialize twice with `failed to write kernel assets (os error 3)`, so the running UI could not be inspected at representative desktop/narrow viewports.

| Reference | Review target |
|---|---|
| `01-home-dashboard.png` | Real seven-day summary, status/trend, recent rows, honest empty/loading/error states, no fabricated metrics |
| `02-monitoring-configurations.png` | Configuration list, search, schedule summary, enabled status, existing actions |
| `03-new-configuration-general.png` | General step, five-step indicator, breadcrumbs and save boundary |
| `04-gitlab-connection.png` | Existing URL and credential flow, validation feedback, secret redaction |
| `05-scope-selection.png` | Hierarchical scope, search, selection summary and unavailable historical values |
| `06-author-policies.png` | Existing global author editor remains active; future branch/repository policy area is explicitly disabled and cannot mutate state |
| `07-scheduling.png` | Existing recurrence, local time/timezone, enablement, preview and save/remove behavior |
| `08-executions-list.png` | Filters, trigger/status/timestamps, Finding count, manual execution using an existing configuration |
| `09-execution-findings.png` | Four existing execution tabs and persisted Finding details/actions |
| `10-commit-diff-modal.png` | Feature 011/012 large dialog, sidebar, split alignment, loading/error/file states and keyboard focus |

Do not consider the visual review complete until a reviewer compares the running application against all references and records viewport sizes and differences.

## Behavior-preservation walkthrough

1. Create and edit a Monitoring Configuration; verify CRUD validation, optimistic concurrency, enabled status, global allowed authors, scope, and schedule behavior.
2. Save or validate a GitLab credential and verify the secret clears from the input and is never shown again.
3. Select groups and repositories and verify dynamic group intent and unavailable historical selections retain their existing behavior.
4. Run the existing manual execution action; verify the execution pipeline and read-only list fields show real status and Finding counts.
5. Open an execution and visit Overview, Repositories, Findings, and Details; verify historical values and actions remain unchanged.
6. Open a commit diff from an applicable Finding and verify on-demand retrieval and the split viewer without changing Feature 011/012 limits or semantics.

## Expected scope check

- No database migration or new persisted entity.
- Only additive read projections described by `contracts/home-dashboard-summary.md`: Home summary, nullable `scheduleSummary`, and `findingCount`.
- No branch-author policy API/storage/snapshot/rule behavior.
- No unsupported analytics, Finding types, mining rules, AI, scheduler changes, or diff endpoint changes.

Implementation scope review: no Alembic migration or persisted entity was added. The Authors preview fields are disabled and excluded from form state and write payloads. PostgreSQL integration and manual visual validation remain open for the environment reasons above.
