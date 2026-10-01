---
description: "Implementation tasks for Feature 013 RepoMiner Visual & UX Alignment"
---

# Tasks: RepoMiner Visual & UX Alignment

**Input**: Design documents in `specs/013-repominer-visual-ux-alignment/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/home-dashboard-summary.md`

**Organization**: Tasks are grouped by the four user stories from `spec.md`. Feature 013 is an incremental presentation refactor; use existing routes, API clients, state/query behavior, and domain behavior.

## Phase 1: Setup

**Purpose**: Confirm the existing frontend/backend test and route conventions before shared changes.

- [x] T001 Inventory current shell, shared components, feature routes, and test setup in `src/app/`, `src/shared/`, `src/features/`, `src/test/`, and `backend/app/`; record reuse points in `specs/013-repominer-visual-ux-alignment/quickstart.md` without changing behavior

## Phase 2: Foundational Shared Presentation

**Purpose**: Establish shared visual primitives before page-specific alignment.

- [x] T002 [P] Add or refine theme tokens and global typography/spacing/responsive foundations in `src/app/theme/` and `src/app/`
- [x] T003 [P] Add or refine reusable PageContainer, PageHeader, ContentCard, and breadcrumb presentation in `src/shared/components/layout/` and `src/shared/components/navigation/`
- [x] T004 [P] Standardize StatusBadge and loading, empty, and safe error state components in `src/shared/components/status/` and `src/shared/components/feedback/`
- [x] T005 [P] Add or refine reusable WizardShell, form section/actions, and dashboard card/grid presentation in `src/shared/components/wizard/`, `src/shared/components/form/`, and `src/shared/components/dashboard/`
- [x] T006 Add shared component accessibility and responsive tests for focus, labels, status text, semantic structure, and contained overflow after T002-T005 in `src/test/shared/` and `src/test/accessibility/`

## Phase 3: User Story 1 - Navigate a coherent application (Priority: P1)

**Goal**: Standardize the application shell and replace Home placeholder content with truthful summaries derived from persisted data.

**Independent Test**: Navigate all four supported routes at desktop and narrow widths; load Home with populated, empty, active-only, and failed responses and verify every metric is data-backed.

### Tests for User Story 1

- [x] T007 [P] [US1] Add dashboard summary response contract tests for UTC boundaries, seven zero-filled days, status/success formulas, distinct repositories, Findings, and recent rows in `backend/tests/api/test_dashboard_summary.py` and `backend/tests/unit/test_dashboard_summary.py`
- [x] T008 [P] [US1] Add shell and navigation tests for route links, active route semantics, narrow navigation, and responsive content in `src/test/app/`
- [x] T009 [P] [US1] Add Home tests for real response rendering, no-terminal success rate, empty/loading/error/retry, recent executions, and no fabricated metrics in `src/test/features/home/`

### Implementation for User Story 1

- [x] T010 [US1] Implement the bounded read-only dashboard summary query/use case and repository port over existing execution, repository execution, and Finding rows in `backend/app/application/use_cases/get_dashboard_summary.py` and `backend/app/application/ports/dashboard_summary_repository.py`
- [x] T011 [US1] Implement SQLAlchemy aggregation for the seven-day UTC summary and five recent executions without new persistence in `backend/app/infrastructure/database/`
- [x] T012 [US1] Expose and document `GET /api/v1/dashboard/summary` using the contract in `specs/013-repominer-visual-ux-alignment/contracts/home-dashboard-summary.md` in `backend/app/api/v1/dashboard.py`
- [x] T013 [US1] Implement the typed dashboard summary API client and query state in `src/features/home/api/` and `src/features/home/`
- [x] T014 [US1] Replace placeholder Home content with supported metric cards, seven-day trend, status distribution, real-rule Finding breakdown, recent executions, and honest asynchronous states in `src/features/home/pages/HomePage.tsx`
- [x] T015 [US1] Refine persistent sidebar, product identity, active navigation, page width, responsive navigation, and supported primary items in `src/app/layout/`, `src/app/routes/navigation.tsx`, and `src/app/routes/routeConfig.tsx`
- [x] T016 [US1] Integrate shared page heading/container and status/feedback presentation across Home and shell in `src/features/home/` and `src/app/layout/`

## Phase 4: User Story 2 - Create and maintain a Monitoring Configuration (Priority: P1)

**Goal**: Present configuration list, details, and existing create/edit behavior through a five-step visual flow without changing resource/API semantics.

**Independent Test**: Create and edit configuration through General, GitLab connection, Scope, Authors, and Scheduling; confirm existing credential, scope, global-author, and schedule behavior remains unchanged.

### Tests for User Story 2

- [x] T017 [P] [US2] Add configuration-list tests for search, existing actions, status, schedule summary, empty/error states, and no per-row schedule requests in `src/test/features/monitoring-configurations/configuration-list.test.tsx`
- [x] T018 [P] [US2] Add wizard regression tests for ordered step navigation and existing General, GitLab credential, hierarchical Scope, global Authors, and Scheduling behavior in `src/test/features/monitoring-configurations/configuration-wizard-regression.test.tsx`
- [x] T019 [P] [US2] Add tests that future repository/branch author-policy preview is disabled, sends no mutation, and leaves global allowed-author semantics intact in `src/test/features/monitoring-configurations/author-policy-preview.test.tsx`

### Implementation for User Story 2

- [x] T020 [P] [US2] Add Monitoring Configuration list contract tests proving nullable `scheduleSummary` derives only from the existing schedule and preserves all existing fields, meanings, routes, and write behavior in `backend/tests/api/test_configuration_create_and_read.py`
- [x] T021 [US2] Add nullable additive `scheduleSummary` to the Monitoring Configuration list DTO/list projection using existing schedule rows, preserving response semantics and adding no schema migration in `backend/app/api/v1/schemas.py`, `backend/app/infrastructure/database/sqlalchemy_repositories.py`, and `backend/app/api/v1/monitoring_configurations.py`
- [x] T022 [US2] Extend configuration-list frontend DTO/client mapping for `scheduleSummary` in `src/features/monitoring-configurations/api/`
- [x] T023 [US2] Align configuration table hierarchy, search, schedule summary, status, New Configuration action, and existing row actions in `src/features/monitoring-configurations/`
- [x] T024 [US2] Implement the five-step General/GitLab connection/Scope/Authors/Scheduling presentation shell around existing feature components and API hooks in `src/features/monitoring-configurations/`
- [x] T025 [US2] Group existing configuration detail fields, connection, scope, authors, schedule, execution history, and actions into consistent sections in `src/features/monitoring-configurations/`
- [x] T026 [US2] Preserve the active global allowed-author editor and present only disabled/explanatory future branch/repository policy structure in `src/features/monitoring-configurations/`; do not add policy requests, persisted fields, snapshots, or mining behavior
- [x] T027 [US2] Verify and retain existing ETag/version conflict, token transient handling, credential secrecy, scope reconciliation, schedule preview/removal, and save boundaries in `src/features/monitoring-configurations/` and focused existing tests under `backend/tests/api/`

## Phase 5: User Story 3 - Review execution history and results (Priority: P1)

**Goal**: Align execution list and details while retaining existing history, repository, Finding, and commit-diff semantics.

**Independent Test**: Review manual and scheduled executions, filters, all four detail tabs, repository outcomes, Findings, and split commit diff; verify values and actions match persisted history.

### Tests for User Story 3

- [x] T028 [P] [US3] Add execution-list API tests proving `findingCount` counts persisted Finding rows through RepositoryExecution and is additive while all existing fields, pagination, ordering, filtering, and lifecycle semantics remain unchanged in `backend/tests/api/test_execution_history_api.py`
- [x] T029 [P] [US3] Add execution list/detail component tests for filters, pagination, trigger/status/timestamps/duration/counts, existing manual action, and the four detail tabs in `src/test/features/executions/execution-history.test.tsx`, `src/test/features/executions/execution-details.test.tsx`, and `src/test/features/executions/manual-execution.test.tsx`
- [x] T030 [P] [US3] Add regression tests for repository results, existing Finding content, Finding-ID-only diff action, split alignment, dialog states, and focus/accessibility in `src/test/features/executions/execution-repositories.test.tsx`, `src/test/features/executions/execution-findings.test.tsx`, and `src/test/features/executions/finding-commit-diff.test.tsx`

### Implementation for User Story 3

- [x] T031 [US3] Add additive read-only execution-list `findingCount` as a count of persisted Finding rows through RepositoryExecution, without changing stored data, Finding detection, execution semantics, or list behavior in `backend/app/api/v1/execution_schemas.py` and `backend/app/infrastructure/database/sqlalchemy_repositories.py`
- [x] T032 [US3] Extend execution list types and API mapping for `findingCount` in `src/features/executions/api/`
- [x] T033 [US3] Align execution history table, existing filters/pagination, trigger and status indicators, timestamps, duration, Finding count, and existing manual action in `src/features/executions/`
- [x] T034 [US3] Align Overview, Repositories, Findings, and Details tab hierarchy using existing data and safe errors in `src/features/executions/`
- [x] T035 [US3] Apply shared visual polish to the existing Commit Diff dialog while preserving its on-demand retrieval, file sidebar, split viewer, line numbering, file states, safe retry, and focus behavior in `src/features/executions/`

## Phase 6: User Story 4 - Use consistent presentation across product data (Priority: P2)

**Goal**: Finish a coherent visual language across forms, tables, cards, statuses, actions, loading/empty/error states, and responsive layouts.

**Independent Test**: Compare affected routes at desktop, tablet, and narrow viewports and verify repeated components share hierarchy and accessibility without changing business behavior.

### Tests for User Story 4

- [x] T036 [P] [US4] Add cross-feature tests for semantic table headers, readable status labels, accessible icon actions, loading/empty/error states, and controlled table overflow in `src/test/accessibility/feature013-pages.a11y.test.tsx` and `src/test/features/visual-alignment-accessibility.test.tsx`
- [x] T037 [P] [US4] Add responsive tests for card wrapping, wizard usability, dialog bounds, and retained side-by-side diff semantics in `src/test/app/feature013-responsive.test.tsx`

### Implementation for User Story 4

- [x] T038 [US4] Apply shared status, table, action, typography, spacing, card, and feedback conventions to configuration, execution, repository, and Finding surfaces in `src/features/monitoring-configurations/` and `src/features/executions/`
- [x] T039 [US4] Verify labels, visible focus, keyboard operation, non-color status meaning, semantic tables, dialog focus, and theme contrast across affected workflows in `src/shared/`, `src/app/`, and `src/features/`
- [x] T040 [US4] Add responsive contained scrolling and layout refinements without changing route, wizard, table, or split-diff behavior in `src/app/`, `src/shared/`, and `src/features/`

## Phase 7: Polish and Cross-Cutting Validation

**Purpose**: Complete automated regression and production validation. Keep reference review explicitly manual.

- [x] T041 Run focused backend dashboard/configuration/execution API and unit suites, then record actual results in `specs/013-repominer-visual-ux-alignment/quickstart.md`
- [x] T042 Run frontend feature, shell, responsive, and accessibility suites and production build; record actual results in `specs/013-repominer-visual-ux-alignment/quickstart.md`
- [ ] T043 Manually compare shell and Home against `references/01-home-dashboard.png`; record viewport and intentional differences in `specs/013-repominer-visual-ux-alignment/quickstart.md`
- [ ] T044 Manually compare configuration list and General, GitLab connection, Scope, Authors, and Scheduling steps against `references/02-monitoring-configurations.png`, `references/03-new-configuration-general.png`, `references/04-gitlab-connection.png`, `references/05-scope-selection.png`, `references/06-author-policies.png`, and `references/07-scheduling.png`; verify future policy controls remain disabled and record differences in `specs/013-repominer-visual-ux-alignment/quickstart.md`
- [ ] T045 Manually compare Executions list, Execution Findings/details, and Commit Diff modal against `references/08-executions-list.png`, `references/09-execution-findings.png`, and `references/10-commit-diff-modal.png`; record visual and functional differences in `specs/013-repominer-visual-ux-alignment/quickstart.md`
- [x] T046 Verify no Alembic migration, new persisted entity, branch-author policy behavior, new Finding type, or unsupported analytics/mining capability was introduced; record the scope check in `specs/013-repominer-visual-ux-alignment/quickstart.md`

## Dependencies and Execution Order

### Phase dependencies

- Setup T001 precedes shared foundation work.
- Foundational T002-T006 precede all story work; T003-T005 depend on the existing-component inventory in T001, while T006 validates the shared primitives after their implementation.
- User Stories 1, 2, and 3 depend on the shared foundation. User Story 4 follows the three primary workflows because it applies cross-cutting conventions to their final presentation.
- Polish T041-T046 follows the applicable implementation tasks. Manual visual tasks remain open until a human performs and records the review.

### User-story dependencies

- **US1 (P1)**: After shared foundation; shell and Home can be independently verified. Home backend query, route, and frontend work proceeds T007/T009 -> T010-T014; shell tests and shell work proceed T008 -> T015-T016.
- **US2 (P1)**: After shared foundation; tests T017-T020 precede list/wizard changes T021-T027. The global Authors editor remains the only active policy.
- **US3 (P1)**: After shared foundation; tests T028-T030 precede list projection and UI alignment T031-T035. Feature 011/012 behavior remains unchanged.
- **US4 (P2)**: Depends on US1-US3 visual foundations and regression surfaces; tasks T036-T040 consolidate shared presentation without changing business meaning.

### Parallel opportunities

- T002-T005 can proceed in parallel after T001 because they own separate shared concerns/files; T006 follows them.
- Within US1, backend summary contract/query work T007/T010-T012 and shell work T008/T015 can proceed independently; frontend Home tests precede its API/page implementation.
- US2 and US3 may proceed independently after the foundation if separate contributors own their feature directories. Do not parallelize tasks that edit the same configuration or execution view files.
- T043-T045 are independent manual comparison sessions after implementation; T041/T042 should complete before declaring automated validation done.

## MVP and Delivery Strategy

The first demonstrable increment is US1: the coherent navigable shell and data-backed Home dashboard. Complete shared foundation first, then validate shell and Home independently. Follow with US2 configuration UX, US3 execution/result UX, and US4 product-wide consistency. Finish automated checks and production build; keep T043-T045 open until visual comparison is actually performed.

## Scope Notes

- Do not create database entities or Alembic migrations for Feature 013.
- The only planned backend work is additive read-only Home aggregation and list projections over already persisted schedule and Finding counts.
- Keep current global allowed-author editing. Repository/branch policy controls are future-only, disabled/explanatory presentation and cannot submit or persist data.
- Use the ten reference images only for layout, spacing, hierarchy, proportions, and responsive direction; do not copy mock values or infer new behavior.
