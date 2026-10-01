---

description: "Dependency-ordered implementation tasks for Feature 001 Application Shell"
---

# Tasks: Application Shell

**Input**: Design documents from `/specs/001-application-shell/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required by the feature specification and constitution. Write each story's test tasks
before its implementation tasks and confirm they fail for the missing behavior.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated as
an incremental slice. The author-owned `checklists/ux-architecture.md` must be reviewed separately
before implementation; implementation does not modify reviewer-owned checklist markers.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it uses different files and has no incomplete dependency
- **[Story]**: User story traceability label
- Every task includes exact file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize the single frontend project and its development/test toolchain.

- [X] T001 Initialize the Vite React TypeScript project and pin runtime dependencies in package.json and package-lock.json
- [X] T002 Configure strict TypeScript compilation and browser types in tsconfig.json and tsconfig.app.json
- [X] T003 [P] Configure Vite and Vitest with jsdom and test setup discovery in vite.config.ts
- [X] T004 [P] Create the HTML entry document and application mount point in index.html
- [X] T005 [P] Configure global test matchers, cleanup, media-query support, and axe integration in src/test/setup.ts
- [X] T006 Create the frontend entry point and top-level application provider boundary in src/main.tsx and src/app/App.tsx

**Checkpoint**: The empty frontend builds and the test runner starts without backend configuration.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish design tokens, theme policy, presentation contracts, and base composition
primitives required by every user story.

**CRITICAL**: No user story implementation begins until this phase is complete.

- [X] T007 [P] Define semantic palette, typography, spacing, radii, borders, elevations, breakpoints, and shell dimensions in src/app/theme/tokens.ts
- [X] T008 Build the centralized accessible Material UI theme and global component overrides from T007 in src/app/theme/theme.ts
- [X] T009 [P] Define NavigationItem, RouteDescriptor, BreadcrumbItem, PageStateDescriptor, PresentationStatus, and WizardStepDescriptor exactly as constrained by data-model.md in src/shared/types/presentation.ts
- [X] T010 [P] Implement safe display formatting for absent, malformed, and long route identifiers in src/shared/utils/displayText.ts
- [X] T011 [P] Implement reusable PageContainer with theme-based responsive gutters and width constraints in src/shared/components/layout/PageContainer.tsx
- [X] T012 [P] Implement reusable ContentCard and SectionHeader primitives without feature behavior in src/shared/components/layout/ContentCard.tsx and src/shared/components/layout/SectionHeader.tsx
- [X] T013 Integrate the centralized theme and baseline styles at the application provider boundary in src/app/App.tsx

**Checkpoint**: Shared styling and presentation contracts are ready; user-story phases may begin.

---

## Phase 3: User Story 1 - Navigate the Monitoring Workspace (Priority: P1) MVP

**Goal**: Provide the shared shell and four primary destinations with direct entry, active navigation,
consistent titles, and centralized route declarations.

**Independent Test**: Start at each primary destination, move to every other primary destination,
and verify one shell, the correct title, and a visible and semantic active-navigation indication.

### Tests for User Story 1

- [X] T014 [P] [US1] Write failing shell landmark, identity, and four-item navigation tests in src/test/app/AppShell.test.tsx
- [X] T015 [P] [US1] Write failing SC-001/SC-003 direct-entry, primary-navigation, synchronous route-feedback, active-state, and title tests for `/`, `/monitoring-configurations`, `/executions`, and `/settings` in src/test/app/routes.test.tsx
- [X] T016 [P] [US1] Write failing keyboard navigation and active-item semantics tests in src/test/app/Sidebar.test.tsx

### Implementation for User Story 1

- [X] T017 [P] [US1] Define the four canonical primary navigation items and nested-path ownership metadata in src/app/routes/navigation.ts
- [X] T018 [P] [US1] Create the Home structural landing placeholder in src/features/home/pages/HomePage.tsx
- [X] T019 [P] [US1] Create the Monitoring Configurations listing shell with isolated search, action, table, status, and row-action presentation in src/features/monitoring-configurations/pages/MonitoringConfigurationsPage.tsx
- [X] T020 [P] [US1] Create the global Executions structural listing placeholder in src/features/executions/pages/ExecutionsPage.tsx
- [X] T021 [P] [US1] Create the Settings structural placeholder in src/features/settings/pages/SettingsPage.tsx
- [X] T022 [P] [US1] Add clearly labeled non-production listing fixtures owned only by the monitoring feature in src/features/monitoring-configurations/fixtures/listingFixtures.ts
- [X] T023 [US1] Implement the desktop Sidebar with identity, icons, canonical labels, semantic active state, and no authentication behavior in src/app/layout/Sidebar.tsx
- [X] T024 [US1] Implement AppShell with a single navigation region and main-content landmark in src/app/layout/AppShell.tsx
- [X] T025 [US1] Define centralized primary route objects and metadata outside feature pages in src/app/routes/routeConfig.tsx
- [X] T026 [US1] Instantiate the browser router and connect the AppShell layout route in src/app/routes/router.tsx and src/app/App.tsx
- [X] T027 [US1] Complete US1 tests and remove any temporary implementation shortcuts in src/test/app/AppShell.test.tsx, src/test/app/routes.test.tsx, and src/test/app/Sidebar.test.tsx

**Checkpoint**: User Story 1 is a demonstrable MVP with a stable shell and primary navigation.

---

## Phase 4: User Story 2 - Understand Context on Nested Pages (Priority: P2)

**Goal**: Add nested destinations, titles, breadcrumbs, and structural listing, form/wizard, tree,
and dashboard compositions without future business behavior.

**Independent Test**: Open each nested route directly, verify its page title and linked parent
breadcrumbs, then verify every unfinished capability is presented truthfully as a structural shell.

### Tests for User Story 2

- [X] T028 [P] [US2] Write failing SC-001/SC-002/SC-003 nested-route tests for all four nested canonical destinations, including safe parameters, titles, active sections, and direct reachability, in src/test/app/nestedRoutes.test.tsx
- [X] T029 [P] [US2] Write failing SC-003 breadcrumb semantics, required hierarchy, and parent-link tests in src/test/shared/Breadcrumbs.test.tsx
- [X] T030 [P] [US2] Write failing controlled current/completed step and Back/Next/Cancel semantics tests in src/test/features/WizardShell.test.tsx
- [X] T031 [P] [US2] Write failing structural boundary tests proving tree and dashboard shells expose no GitLab calls, real analytics, or enabled deferred actions in src/test/features/structuralShells.test.tsx

### Implementation for User Story 2

- [X] T032 [P] [US2] Implement reusable breadcrumb presentation with linked parents and a semantic unlinked current item in src/shared/components/navigation/AppBreadcrumbs.tsx
- [X] T033 [P] [US2] Implement reusable PageHeader with title, description, back/breadcrumb, status, and action slots in src/shared/components/layout/PageHeader.tsx
- [X] T034 [P] [US2] Implement shared form field grouping and responsive form actions without business validation in src/shared/components/form/FormFieldGroup.tsx and src/shared/components/form/FormActions.tsx
- [X] T035 [P] [US2] Implement the controlled four-step WizardShell using WizardStepDescriptor states `upcoming`, `current`, and `completed` in src/shared/components/wizard/WizardShell.tsx
- [X] T036 [P] [US2] Implement lightweight TreePanel, TreeNodeRow, and SelectedItemsPanel presentation primitives with no recursive selection rules in src/shared/components/tree/TreePanel.tsx, src/shared/components/tree/TreeNodeRow.tsx, and src/shared/components/tree/SelectedItemsPanel.tsx
- [X] T037 [P] [US2] Implement DashboardHeader, MetricCard, DashboardSection, ChartContainer, and DashboardGrid without calculations or chart dependencies in src/shared/components/dashboard/DashboardHeader.tsx, src/shared/components/dashboard/MetricCard.tsx, src/shared/components/dashboard/DashboardSection.tsx, src/shared/components/dashboard/ChartContainer.tsx, and src/shared/components/dashboard/DashboardGrid.tsx
- [X] T038 [P] [US2] Add non-production wizard and hierarchy fixtures isolated to the monitoring feature in src/features/monitoring-configurations/fixtures/wizardFixtures.ts
- [X] T039 [P] [US2] Add non-production metric, tab, chart-placeholder, and table fixtures isolated to the executions feature in src/features/executions/fixtures/dashboardFixtures.ts
- [X] T040 [P] [US2] Compose the New Monitoring Configuration form, wizard, and hierarchy visual shell with no validation, submission, GitLab, selection, or scheduling behavior in src/features/monitoring-configurations/pages/NewMonitoringConfigurationPage.tsx
- [X] T041 [P] [US2] Create the display-only Monitoring Configuration Details placeholder using safe identifier formatting in src/features/monitoring-configurations/pages/MonitoringConfigurationDetailsPage.tsx
- [X] T042 [P] [US2] Create the display-only Configuration Executions history placeholder using safe identifier formatting in src/features/monitoring-configurations/pages/ConfigurationExecutionsPage.tsx
- [X] T043 [P] [US2] Compose the Execution Details dashboard shell with static layout fixtures, status presentation, tabs, and no enabled report or analytics behavior in src/features/executions/pages/ExecutionDetailsPage.tsx
- [X] T044 [US2] Register the four nested destinations so routeConfig contains the same eight canonical paths as FR-005, with title, primary-section, parameter, and breadcrumb metadata in src/app/routes/routeConfig.tsx
- [X] T045 [US2] Complete US2 tests and verify route-contract terminology in src/test/app/nestedRoutes.test.tsx, src/test/shared/Breadcrumbs.test.tsx, src/test/features/WizardShell.test.tsx, and src/test/features/structuralShells.test.tsx

**Checkpoint**: All eight route patterns and reference-guided structural shells are independently
demonstrable without implementing future business capabilities.

---

## Phase 5: User Story 3 - Recognize and Recover from Page States (Priority: P3)

**Goal**: Establish reusable loading, empty, error, disabled, success, placeholder, status, helper,
validation, and alert presentation contracts.

**Independent Test**: Present every standard state independently and verify each has distinguishable
text/semantics, uses color only as reinforcement, and exposes a relevant action only when supplied.

### Tests for User Story 3

- [X] T046 [P] [US3] Write failing accessible semantics and optional-action tests for LoadingState, EmptyState, and ErrorState in src/test/shared/FeedbackStates.test.tsx
- [X] T047 [P] [US3] Write failing label, semantic-tone, icon, and non-color-cue tests for all eight PresentationStatus values in src/test/shared/StatusBadge.test.tsx
- [X] T048 [P] [US3] Write failing alert, helper, validation, disabled, success, and placeholder distinction tests in src/test/shared/FeedbackMessage.test.tsx

### Implementation for User Story 3

- [X] T049 [P] [US3] Implement LoadingState with accessible progress communication and no stale-content implication in src/shared/components/feedback/LoadingState.tsx
- [X] T050 [P] [US3] Implement EmptyState with optional meaningful next action in src/shared/components/feedback/EmptyState.tsx
- [X] T051 [P] [US3] Implement ErrorState with user-oriented explanation and optional recovery action in src/shared/components/feedback/ErrorState.tsx
- [X] T052 [P] [US3] Implement PlaceholderState distinct from empty and error conditions in src/shared/components/feedback/PlaceholderState.tsx
- [X] T053 [P] [US3] Implement shared alert, helper, validation, disabled, and success feedback conventions in src/shared/components/feedback/FeedbackMessage.tsx
- [X] T054 [US3] Implement canonical text/tone/icon mappings for `active`, `disabled`, `paused`, `pending`, `running`, `completed`, `partially-completed`, and `failed` without transition rules in src/shared/components/status/StatusBadge.tsx
- [X] T055 [US3] Replace ad hoc state/status presentation in existing feature shells with shared components in src/features/monitoring-configurations/pages/MonitoringConfigurationsPage.tsx and src/features/executions/pages/ExecutionDetailsPage.tsx
- [X] T056 [US3] Complete US3 tests and verify shared-state contract terminology in src/test/shared/FeedbackStates.test.tsx, src/test/shared/StatusBadge.test.tsx, and src/test/shared/FeedbackMessage.test.tsx

**Checkpoint**: Future feature pages can reuse all required user-facing states without duplicating
state presentation or business behavior.

---

## Phase 6: User Story 4 - Use the Application Across Viewport Sizes (Priority: P4)

**Goal**: Make navigation, layouts, forms, tables, tree panels, and dashboard grids usable at narrow,
medium, and wide viewports while preserving WCAG 2.2 AA behavior.

**Independent Test**: At 375px, 768px, and 1440px, verify access to every primary destination,
correct drawer focus behavior, readable reflow, stacked layouts, and no unintended page-level
horizontal scrolling; these acceptance widths do not redefine implementation breakpoints.

### Tests for User Story 4

- [X] T057 [P] [US4] Write failing persistent-sidebar versus compact-menu behavior tests at representative widths 375px, 768px, and 1440px with mocked media queries in src/test/app/responsiveNavigation.test.tsx
- [X] T058 [P] [US4] Write failing mobile drawer keyboard, focus containment/restoration, dismissal, and route-selection closure tests in src/test/app/MobileNavigation.test.tsx
- [X] T059 [P] [US4] Write failing responsive composition tests at 375px, 768px, and 1440px for forms, tables, tree panels, and dashboard grids in src/test/features/responsiveLayouts.test.tsx

### Implementation for User Story 4

- [X] T060 [P] [US4] Implement centralized responsive navigation state and viewport-change reconciliation in src/shared/hooks/useResponsiveNavigation.ts
- [X] T061 [US4] Implement the labeled, focus-managed temporary mobile navigation drawer in src/app/layout/MobileNavigation.tsx
- [X] T062 [US4] Integrate persistent desktop and compact mobile navigation without duplicate landmarks in src/app/layout/AppShell.tsx
- [X] T063 [P] [US4] Add wrapping actions and localized labeled table overflow to the listing shell in src/features/monitoring-configurations/pages/MonitoringConfigurationsPage.tsx
- [X] T064 [P] [US4] Add single-column form/actions and stacked hierarchy panels on constrained viewports in src/features/monitoring-configurations/pages/NewMonitoringConfigurationPage.tsx
- [X] T065 [P] [US4] Add adaptive metric/section grids and stacked dashboard composition in src/features/executions/pages/ExecutionDetailsPage.tsx
- [X] T066 [US4] Complete US4 tests and verify viewport-change edge cases plus SC-006 acceptance at 375px, 768px, and 1440px in src/test/app/responsiveNavigation.test.tsx, src/test/app/MobileNavigation.test.tsx, and src/test/features/responsiveLayouts.test.tsx

**Checkpoint**: The shell and every structural composition remain usable across the required
viewport classes.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validate accessibility, visual consistency, scope boundaries, and production build
quality across all completed stories.

- [X] T067 [P] Add automated axe coverage for shell, feedback states, listing, wizard, hierarchy, and dashboard compositions in src/test/accessibility/applicationShell.a11y.test.tsx
- [X] T068 [P] Add long-title, breadcrumb, message, identifier, and representative table-content edge-case coverage in src/test/app/contentOverflow.test.tsx
- [X] T069 Audit fixture imports, deferred controls, timers, and browser-specific APIs so no sample data escapes feature fixtures; no artificial route/placeholder delay exists; fallbacks are present where required; and no backend, storage, GitLab, authentication, report, chart, or business action is introduced across src/features/ and src/shared/
- [X] T070 Review all four visual references against the implemented theme and compositions, recording justified deviations in specs/001-application-shell/quickstart.md
- [X] T071 Run and document manual WCAG 2.2 AA keyboard, focus, zoom/reflow, contrast, and screen-reader smoke results in specs/001-application-shell/quickstart.md
- [X] T072 Run the full test suite and production build commands from quickstart.md, validate all eight canonical destinations, and resolve failures in package.json, src/, and src/test/
- [X] T073 Perform the final terminology, route-contract, component-boundary, and no-secret/no-storage review against specs/001-application-shell/contracts/ and specs/001-application-shell/plan.md
- [X] T074 Document compatibility smoke results for the Chrome, Edge, Firefox, and Safari support baseline and any required fallbacks in specs/001-application-shell/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1 and blocks all user stories.
- **Phase 3 US1**: Depends on Phase 2 and delivers the MVP shell.
- **Phase 4 US2**: Depends on Phase 2 and the AppShell/router integration from US1 (T024â€“T026).
- **Phase 5 US3**: Depends only on Phase 2; it may run in parallel with US1/US2 until T055.
- **Phase 6 US4**: Depends on the shell from US1 and visual compositions from US2/US3.
- **Phase 7 Polish**: Depends on all selected user stories.

### User Story Dependency Graph

```text
Setup -> Foundation -> US1 (MVP) -> US2 -> US4
                      |           \-> US4
                      `-> US3 --------> US4

US1 + US2 + US3 + US4 -> Polish
```

### User Story Independence

- **US1**: Independently delivers primary shell navigation and top-level routes.
- **US2**: Can be tested with AppShell and a memory router; depends on US1 infrastructure but not
  on US1 page content.
- **US3**: Shared states are independently testable after Foundation; T055 is the integration step.
- **US4**: Responsiveness is cross-cutting by nature and begins after the target compositions exist.

### Within Each User Story

- Write the story's tests first and confirm failure for the missing behavior.
- Implement independent primitives and pages in parallel where file ownership does not overlap.
- Complete route/page integration after primitives exist.
- Pass the story tests before advancing to the next dependent phase.

---

## Parallel Opportunities

### User Story 1

```text
Parallel tests: T014, T015, T016
Parallel pages/config: T017, T018, T019, T020, T021, T022
Then: T023 -> T024 -> T025 -> T026 -> T027
```

### User Story 2

```text
Parallel tests: T028, T029, T030, T031
Parallel shared primitives: T032, T033, T034, T035, T036, T037
Parallel fixtures/pages after primitives: T038, T039, T040, T041, T042, T043
Then: T044 -> T045
```

### User Story 3

```text
Parallel tests: T046, T047, T048
Parallel feedback primitives: T049, T050, T051, T052, T053
Then: T054 -> T055 -> T056
```

### User Story 4

```text
Parallel tests: T057, T058, T059
Then: T060 -> T061 -> T062
Parallel page adaptation: T063, T064, T065
Then: T066
```

---

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational phases.
2. Complete US1 tests and implementation.
3. Stop and validate the four primary destinations and shell independently.
4. Demonstrate the stable primary navigation foundation before nested compositions.

### Incremental Delivery

1. **US1**: Primary application shell and navigation.
2. **US2**: Nested hierarchy plus reference-guided structural pages.
3. **US3**: Shared state and status language.
4. **US4**: Responsive and compact-navigation behavior.
5. **Polish**: WCAG, visual, scope, build, and contract validation.

### Scope Discipline

- No task may add backend code, persistence, APIs, GitLab calls, credential handling,
  authentication, authorization, mining, scheduling, CRUD, execution processing, or analytics.
- Presentation fixtures stay in their owning feature and are never treated as domain entities.
- Shared components remain composable and contain no monitoring or execution business rules.
- New dependencies require the justification documented in research.md; no chart, tree, form-state,
  or global-state library is planned.

---

## Notes

- `[P]` means different files and no dependency on an incomplete task.
- `[US1]` through `[US4]` map directly to the prioritized specification stories.
- Reviewer-owned checklist markers are never changed by implementation.
- Commit after each task or coherent task group.
- Run `$speckit-analyze` before implementation and `$speckit-converge` after implementation.

---

## Phase 8: Convergence

- [ ] T075 Complete WCAG 2.2 AA acceptance evidence by extending automated accessibility coverage to all eight canonical destinations, adding deterministic contrast checks for themed text, controls, focus indicators, statuses, and errors, and recording the required keyboard, zoom/reflow, contrast, and screen-reader smoke results in src/test/accessibility/ and specs/001-application-shell/quickstart.md per FR-011, SC-005, and plan: Testing Strategy (partial)
- [X] T076 Harden formatDisplayIdentifier so malformed percent-encoded route identifiers return the safe fallback without throwing, and add regression coverage for absent, malformed, sanitized, and excessive identifiers in src/shared/utils/displayText.ts and src/test/app/contentOverflow.test.tsx per Spec Edge Cases and T010 (partial)
- [ ] T077 Execute and document compatibility smoke results for latest and previous-major Chrome and Microsoft Edge, latest Firefox, and latest Safari, including any required browser-specific fallbacks, in specs/001-application-shell/quickstart.md per FR-018 and plan: Testing Strategy (partial)

