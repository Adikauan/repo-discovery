---
description: "Actionable task list for Feature 007 Execution Dashboard"
---

# Tasks: Execution Dashboard

**Input**: Design documents from `/specs/007-execution-dashboard/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/dashboard-ui.md`, and `quickstart.md`

**Tests**: Frontend automated tests are explicitly required by Feature 007 and are included by user story. No backend contract change is planned, so no backend test task is needed.

**Organization**: Tasks are grouped by user story. Feature 007 reuses the existing frontend project, API adapter, route, and Feature 006 execution-detail contract.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with another marked task because it changes a different file and has no dependency on incomplete tasks.
- **[Story]**: User story mapping from `spec.md`.
- Every task includes the specific file path it changes or validation guide it follows.

## Phase 1: Setup

**Purpose**: Shared project initialization.

No setup tasks are required. React, TypeScript, routing, shared dashboard components, API configuration, and the frontend test harness already exist.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared infrastructure required before story work.

No foundational changes are required. Feature 006's detail API and typed frontend adapter already expose all needed persisted fields. No backend, database, migration, dependency, or shell changes are in scope.

**Checkpoint**: Existing execution detail contract and shared UI foundation are ready for user-story work.

---

## Phase 3: User Story 1 - Understand an execution (Priority: P1) MVP

**Goal**: Turn the existing execution detail destination into a useful overview of persisted identity, lifecycle, snapshot context, completion meaning, and counters.

**Independent Test**: Open fixture-backed executions in all five statuses and compare header identity/status/trigger plus Overview timestamps, snapshot fields, duration, completion meaning, and all counters (including zeros) with the supplied detail response.

### Tests for User Story 1

- [X] T001 [US1] Create contrasting `historicalExecutionDetail` and `liveMonitoringConfiguration` fixtures with different names, GitLab URLs, and group/repository scopes; test all five statuses, header/Overview fields, API duration, completion meaning, counters including zero, historical-only rendering, absence of live values, and that rendering requests only execution detail with no live-configuration API lookup required [FR-002, FR-003, FR-005, FR-006, FR-007, FR-008; SC-004]; confirm new assertions fail before implementation in `src/test/features/executions/fixtures.ts` and `src/test/features/executions/execution-details.test.tsx`

### Implementation for User Story 1

- [X] T002 [P] [US1] Create the feature execution header owning execution ID, snapshot configuration name, status, and trigger with shared text-plus-icon status presentation [FR-003, FR-004] in `src/features/executions/components/ExecutionHeader.tsx`
- [X] T003 [P] [US1] Create exactly four labeled metric cards sourced from persisted execution counters, preserving zero values [FR-005, SC-003] in `src/features/executions/components/ExecutionMetrics.tsx`
- [X] T004 [P] [US1] Create Overview with created/started/completed timestamps, API duration, snapshot GitLab URL, completion meaning, counters, safe error information, and separate selected-group and selected-repository scope summaries using only safe snapshot metadata returned by the execution detail API; do not query current configuration, substitute live values, call GitLab, revalidate GitLab entities, or resolve groups into repositories [FR-003, FR-005, FR-006, FR-007, FR-008, FR-010] in `src/features/executions/components/ExecutionOverview.tsx`
- [X] T005 [US1] Compose the dashboard page from the existing detail adapter and shared loading/error states, place ExecutionMetrics inside Overview, use API-provided duration without a running timer, and mount it at the existing route without fetching live Monitoring Configuration data, calling GitLab, revalidating GitLab entities, expanding groups, or substituting live values [FR-002, FR-008, FR-013] in `src/features/executions/pages/ExecutionDashboardPage.tsx` and `src/app/routes/routeConfig.tsx`

**Checkpoint**: A user can open a persisted execution and understand its Feature 006 orchestration result from real detail data.

---

## Phase 4: User Story 2 - Navigate from execution history (Priority: P1)

**Goal**: Preserve whether the dashboard was opened from global history or one configuration's history, while providing a useful fallback for direct entry.

**Independent Test**: Open an execution from both history contexts and verify the dashboard return link targets the corresponding list; direct route entry returns to global history.

### Tests for User Story 2

- [X] T006 [US2] Write navigation-context tests for global history, configuration history, and direct dashboard entry fallback [FR-001, FR-012]; confirm new assertions fail before implementation in `src/test/features/executions/execution-history.test.tsx`

### Implementation for User Story 2

- [X] T007 [P] [US2] Pass the appropriate internal return path when execution links are opened from global or configuration-specific history [FR-001, FR-012] in `src/features/executions/components/ExecutionHistory.tsx`

**Checkpoint**: History links carry the appropriate internal return context; dashboard return navigation is integrated after the section components are ready.

---

## Phase 5: User Story 3 - Review unavailable details safely (Priority: P2)

**Goal**: Make repository and findings detail limitations explicit, show only safe execution error metadata, and make dashboard sections accessible.

**Independent Test**: With a detail response that has no repository/finding records and a safe error object, verify explicit unavailable copy, preserved zero counters, safe code/summary presentation, and no internal error details.

### Tests for User Story 3

- [X] T008 [P] [US3] Add tests for repository/findings unavailable states, zero-count distinction, safe error code/summary, prohibited internal error content, not-found feedback, and retry; parameterize manual refresh across Overview, Repositories, Findings, and Details and assert accessible loading, a detail refetch with changed values rendered in the active context, the same tab remains active with no reset to Overview, normalized refresh failure feedback, and no current-configuration or GitLab requests [FR-009, FR-010, FR-013; SC-006, SC-007]; confirm new assertions fail before implementation in `src/test/features/executions/execution-details.test.tsx`
- [X] T009 [P] [US3] Add accessibility tests for semantic headings, tab roles and keyboard operation, status text, metric names, loading, and error feedback, and confirm new assertions fail before implementation in `src/test/features/executions/execution-accessibility.test.tsx`

### Implementation for User Story 3

- [X] T010 [P] [US3] Create a safe error summary that renders only normalized code and user-safe summary when the API supplies an error object in `src/features/executions/components/ExecutionErrorSummary.tsx`
- [X] T011 [P] [US3] Create an honest repository-detail unavailable state with no sample rows or repository result type in `src/features/executions/components/ExecutionRepositoriesSection.tsx`
- [X] T012 [P] [US3] Create an honest findings-detail unavailable state with no sample findings or finding result type in `src/features/executions/components/ExecutionFindingsSection.tsx`
- [X] T013 [P] [US3] Create a details section limited to safe execution-level identifiers, lifecycle, status, and optional error fields in `src/features/executions/components/ExecutionDetailsSection.tsx`

**Checkpoint**: The unavailable states and safe execution details are ready to integrate into the dashboard.

---

## Phase 6: Dashboard Integration Dependency Join (US2 + US3)

**Purpose**: Integrate the section components only after their creation, then add refresh behavior.

- [X] T014 [US2] Integrate Overview, Repositories, Findings, and Details as keyboard-accessible dashboard tabs/sections, and render a safe return breadcrumb/action from valid internal route state with global execution history fallback for direct entry [FR-009, FR-012, FR-014] in `src/features/executions/pages/ExecutionDashboardPage.tsx` (depends on T005, T006, T007, T008, T009, T010, T011, T012, and T013)
- [X] T015 [US3] Extend the integrated page with manual detail refresh, accessible loading and normalized refresh-failure feedback; preserve whichever tab is selected, render refreshed data in that tab without resetting to Overview, and make no polling or live-configuration/GitLab requests [FR-013] in `src/features/executions/pages/ExecutionDashboardPage.tsx` (depends on T014 and T008-T013)

**Checkpoint**: All dashboard sections distinguish valid zero metrics from unavailable detail and disclose no prohibited data; refresh preserves the active tab.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Responsive and end-to-end validation across the complete dashboard.

- [X] T016 Review and extend representative-width layout coverage for 375px, 768px, and 1440px, including long execution IDs and scope paths without page-level overflow [FR-014, FR-015] in `src/test/features/responsiveLayouts.test.tsx`
- [X] T017 Run the frontend tests and build commands documented in `specs/007-execution-dashboard/quickstart.md`; validation used Vitest thread workers with a temporary config because child-process spawning returns EPERM in this Windows environment; all frontend tests and the standard production build passed. The initial test-first red baseline could not be confirmed because the original runner failed before test discovery.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No work required; project infrastructure already exists.
- **Foundational (Phase 2)**: No work required; Feature 006 detail contract and shared frontend primitives already exist.
- **User Stories (Phase 3+)**: US2 navigation preparation and US3 component work can progress in parallel after US1 where files differ. Dashboard integration T014 waits for T011-T013; refresh T015 follows T014.
- **Polish (Phase 7)**: Depends on dashboard integration and desired stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: No new story dependencies; delivers the useful persisted-data overview MVP.
- **User Story 2 (P1)**: Navigation test T006 precedes history-link work T007. Dashboard integration T014 follows T005-T013, including the US3 section components T011-T013.
- **User Story 3 (P2)**: Tests T008/T009 precede the safe error and section components T010-T013. The Repositories, Findings, and Details components T011-T013 may run in parallel. T014 integrates them; T015 adds refresh after integration.

### Within Each User Story

- Write the story's frontend tests before implementing the behaviors they describe.
- Story 1's separate presentation components can be implemented in parallel after T001; page composition T005 follows those components.
- Story 2 test T006 precedes T007. T014 is the later cross-story page integration and waits for T005-T013.
- Story 3 tests T008/T009 precede implementation. T010-T013 use separate files; T011, T012, and T013 may run in parallel. T014 waits for them, then T015 implements refresh.
- Do not add backend tests or schema work unless the existing safe detail response is proven incomplete; such a contract change requires a plan update first.

### Parallel Opportunities

- **User Story 1**: T002, T003, and T004 work in separate component files after T001.
- **User Story 3**: T008 and T009 can be authored in parallel. After both tests, T010-T013 can be implemented in separate files; T011, T012, and T013 can run in parallel. T014 follows T010-T013; T015 follows T014.
- **Polish**: T016 responsive coverage must finish before T017 runs the quickstart suite.
- No new database, backend API, or shell setup work is parallelized because none is in scope.

---

## Parallel Example: User Story 1

```text
After T001:
Task: T002 ExecutionHeader in src/features/executions/components/ExecutionHeader.tsx
Task: T003 ExecutionMetrics in src/features/executions/components/ExecutionMetrics.tsx
Task: T004 ExecutionOverview in src/features/executions/components/ExecutionOverview.tsx

After T002–T004:
Task: T005 Compose ExecutionDashboardPage in src/features/executions/pages/ExecutionDashboardPage.tsx
```

## Parallel Example: User Story 2

```text
After T005 and T006:
Task: T007 Pass history return context in src/features/executions/components/ExecutionHistory.tsx

T014 is not runnable yet; it must wait for T011, T012, and T013 in the User Story 3 example.
```

## Parallel Example: User Story 3

```text
After T008 and T009:
Task: T010 Safe execution error summary in src/features/executions/components/ExecutionErrorSummary.tsx
Task: T011 Repository unavailable state in src/features/executions/components/ExecutionRepositoriesSection.tsx
Task: T012 Findings unavailable state in src/features/executions/components/ExecutionFindingsSection.tsx
Task: T013 Safe execution details in src/features/executions/components/ExecutionDetailsSection.tsx

T011, T012, and T013 can run in parallel. After T005-T013:
Task: T014 Integrate the dashboard sections and history return navigation in src/features/executions/pages/ExecutionDashboardPage.tsx

After T014:
Task: T015 Add refresh and selected-tab preservation in src/features/executions/pages/ExecutionDashboardPage.tsx
```
## Implementation Strategy

### MVP First (User Story 1)

1. Use existing Feature 006 execution detail API and shared UI infrastructure; no setup, endpoint, or migration is needed.
2. Complete T001, then implement T002–T004 and integrate with T005.
3. Validate the overview independently using persisted execution detail fixtures and a real Feature 006 execution.
4. Complete T011, T012, and T013 in parallel after their tests; integrate them at T014, then implement refresh at T015.
5. Complete responsive and accessibility coverage and run the quickstart validations.

### Incremental Delivery

1. Deliver User Story 1 so users can understand a persisted execution and its true Feature 006 completion meaning.
2. Complete history preparation and section components in dependency order; T011-T013 precede T014, which precedes refresh T015.
3. Deliver User Story 3 so unavailable repository/finding records and safe error details are explicit and accessible.
4. Complete cross-cutting responsive review and the frontend validation commands.

### Scope Guard

Feature 007 does not implement repository mining, repository execution records, findings, current-configuration lookups, GitLab calls, charts, scheduler behavior, live progress, WebSockets/SSE, API changes, persistence changes, or migrations.
