# Tasks: Monitoring Configuration Final UX Adjustments

**Input**: Design documents from `specs/016-monitoring-configuration-final-ux-adjustments/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`

**Scope**: Three frontend refinements. No backend, persistence, migration, or API contract changes.

## Phase 1: User Story 1 - Run a configuration from the list (Priority: P1)

**Goal**: Each configuration row exposes the existing manual execution action without changing its execution behavior.

**Independent Test**: A selected row calls the existing manual execution request with its own configuration ID; pending, success, and safe error states remain accessible and no duplicate request is made while pending.

- [x] T001 [P] [US1] Add list-level manual execution tests for per-row identity, existing execution navigation, pending duplicate prevention, tooltip/accessibility, and safe failure behavior in `src/test/features/monitoring-configurations/manual-execution-list.test.tsx`.
- [x] T002 [US1] Extend `ManualExecutionAction` with an accessible compact IconButton/Tooltip presentation while preserving the existing details-page text presentation in `src/features/executions/components/ManualExecutionAction.tsx`.
- [x] T003 [US1] Render the existing manual execution action in each configuration row's Actions cell without removing Edit/Delete in `src/features/monitoring-configurations/pages/MonitoringConfigurationsPage.tsx`.

## Phase 2: User Story 2 - Keep Selected Scope visible (Priority: P1)

**Goal**: Selected Scope remains visible during desktop tree scrolling and remains usable in stacked narrow layouts.

**Independent Test**: Component tests verify the desktop sticky layout, tree/summary structure, responsive normal-flow presentation, and continued fixed wizard navigation; manual visual testing validates viewport behavior.

- [x] T004 [P] [US2] Add Scope layout tests for Selected Scope structure, desktop sticky styling, narrow stacked behavior, and presence of fixed wizard navigation in `src/test/features/monitoring-configurations/gitlab-scope-sticky-summary.test.tsx`.
- [x] T005 [US2] Apply desktop-only sticky positioning, top offset, viewport-bounded summary scrolling, and narrow-layout normal flow to the Selected Scope column while retaining the GitLab tree and scope behavior in `src/features/monitoring-configurations/pages/GitLabScopePage.tsx` and `src/features/monitoring-configurations/components/ScopeSelectionSummary.tsx`.

## Phase 3: User Story 3 - Return to the list after final save (Priority: P1)

**Goal**: Successful final saves in create and edit flows return to the configuration list; failures retain the current step and draft.

**Independent Test**: Successful schedule saves route to `/monitoring-configurations` for both create and edit; failed saves stay on Scheduling and retain error/draft state.

- [x] T006 [P] [US3] Add final-save tests for create/edit redirect after success, no redirect and retained draft after failure, existing list refresh/notice, and no hardcoded host in `src/test/features/monitoring-configurations/final-save-redirect.test.tsx`.
- [x] T007 [US3] Add a success callback to `ScheduleSection` that fires only after persisted save success, bypass the dirty-route blocker only for that completed save, and navigate from `SchedulingPage` to `/monitoring-configurations` with the existing success notice convention in `src/features/monitoring-configurations/components/ScheduleSection.tsx` and `src/features/monitoring-configurations/pages/SchedulingPage.tsx`.

## Phase 4: Cross-cutting validation

**Purpose**: Verify accessibility, responsive presentation, existing wizard behavior, and visual references.

- [x] T008 [P] Run targeted Feature 016 tests plus affected execution-action, Scope, Scheduling, and wizard regressions; fix failures in the affected `src/test/features/monitoring-configurations/` suites.
- [x] T009 [P] Run the complete frontend test suite and production build using the existing project scripts; record actual results in `specs/016-monitoring-configuration-final-ux-adjustments/quickstart.md` only if the outcomes materially refine the validation instructions.
- [ ] T010 Manually validate the configuration list action, desktop sticky Selected Scope with a long tree, narrow layout, bottom-bar clearance, and successful/failed final save against the running application; leave open if the visual environment is unavailable.

## Dependencies and Execution Order

- T001 precedes T002 and T003; the execution component behavior is reused before list integration is verified.
- T004 precedes T005; layout test and implementation touch separate test/source files.
- T006 precedes T007; final save routing behavior is implemented after its success/failure contract tests exist.
- T008 and T009 follow the three story implementations; T010 follows all screen changes and remains a manual task.
- User stories are independently testable, but the final integrated validation depends on all three.

## Parallel Opportunities

- T001/T004/T006 are independent test-first tasks in separate test files.
- T002/T005/T007 affect separate source files and can be worked independently after their respective tests; T003 depends on T002 because it integrates that component.
- T010 requires a running application and must not be marked complete without manual inspection.

## Implementation Strategy

Implement each small story independently: list action, sticky summary, and success-only final redirect. Preserve the existing API clients, UI feedback, scope state, scheduling semantics, and Feature 015 wizard structure. Finish with focused and full frontend validation plus manual visual review when available.
