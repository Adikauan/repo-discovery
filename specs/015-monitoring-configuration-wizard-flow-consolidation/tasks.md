# Tasks: Monitoring Configuration Wizard Flow Consolidation

**Input**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Automated tests are required by the specification and are included alongside the affected layers.

**Scope**: Frontend flow consolidation plus the single approved non-persisting candidate GitLab validation operation. No migrations, domain behavior changes, or Feature 014/005/009 semantic changes.

## Phase 1: Setup and baseline

**Purpose**: Confirm current implementation boundaries before refactoring.

- [x] T001 Characterize configuration routes, step forms, save hooks, dirty guards, and action placement across `MonitoringConfigurationWizardFlow.test.tsx`, `MonitoringConfigurationOwnership.test.tsx`, and existing Scope/Schedule regression suites.
- [x] T002 [P] Characterize create/update identity, idempotent retry, and ETag/If-Match handling in `MonitoringConfigurationWizardFlow.test.tsx` and `update-and-lifecycle.test.tsx`.
- [x] T003 [P] Add candidate validation contract test fixtures and secret-redaction cases in `backend/tests/api/test_gitlab_candidate_validation.py`.

## Phase 2: Foundational wizard and candidate-validation contracts

**Purpose**: Establish shared contracts and route-independent navigation primitives before migrating individual steps.

- [x] T004 Implement the candidate-validation request/response schemas, safe normalized result, and Problem Details contract in `backend/app/api/v1/schemas.py` and `specs/015-monitoring-configuration-wizard-flow-consolidation/contracts/gitlab-candidate-validation.md`.
- [x] T005 Implement candidate validation as an application use case over the existing GitLab connection client, with no configuration/credential/scope/schedule/execution persistence, in `backend/app/application/use_cases/validate_gitlab_candidate.py`.
- [x] T006 Add the candidate validation route and dependency wiring, reusing existing URL/token validation and redacting candidate secrets from logs/errors, in `backend/app/api/v1/gitlab_connections.py` and `backend/app/api/main.py`.
- [x] T007 Add unit/API tests proving provider success/failure normalization, no persistence calls, no token in response/log/error, and existing Problem Details behavior in `backend/tests/unit/application/test_validate_gitlab_candidate.py` and `backend/tests/api/test_gitlab_candidate_validation.py`.
- [x] T008 Create in-memory create-mode wizard draft state for General values, stable idempotency key, and post-create configuration ID; never put the candidate token in shared context or browser storage, in `src/features/monitoring-configurations/context/MonitoringConfigurationWizardContext.tsx`.
- [x] T009 Create shared route-to-step mapping and the non-clickable accessible five-step indicator in `src/features/monitoring-configurations/components/MonitoringConfigurationWizardLayout.tsx` and `src/features/monitoring-configurations/components/ConfigurationWizardProgress.tsx`.
- [x] T010 Implement the fixed main-content `WizardBottomBar` with left Previous/right Next-or-final slots, responsive sidebar offset, visible focus, and reserved scroll padding in `src/features/monitoring-configurations/components/WizardBottomBar.tsx` and `src/features/monitoring-configurations/components/MonitoringConfigurationWizardLayout.tsx`.
- [x] T011 Add route mapping for create General/Connection and existing-ID General/Connection/Scope/Authors/Scheduling in `src/app/routes/routeConfig.tsx`; preserve IDs, existing invalid-ID handling, and direct-link context.
- [x] T012 Add shared layout/bar tests for exactly five ordered active steps, first-step no-previous state, final-step no-next state, fixed placement/content spacing, and responsive operation in `src/test/features/monitoring-configurations/feature013-list-and-author-preview.test.tsx` and `src/test/features/monitoring-configurations/WizardBottomBar.test.tsx`.

## Phase 3: User Story 1 - Create or edit through one ordered flow (Priority: P1)

**Goal**: Create and edit use the same five-step user-facing flow and preserve configuration identity.

**Independent test criteria**: New configuration retains General values in memory through candidate validation, creates only on GitLab Connection Next, retries credential save without duplicate creation, then preserves the returned ID through Scope, Authors, and Scheduling. Existing configurations navigate across the same steps with the same ID.

**Dependencies**: Phase 2 route mapping, draft state, shared layout, and candidate-validation contract.

- [x] T013 [US1] Refactor `src/features/monitoring-configurations/pages/NewMonitoringConfigurationPage.tsx` and `src/features/monitoring-configurations/components/MonitoringConfigurationForm.tsx` so General validates Name/Description into the in-memory draft and Next does not create a configuration.
- [x] T014 [US1] Add the create-mode GitLab Connection page with URL/token candidate validation, create-on-Next, secure credential save, saved-credential validation, and retained-ID retry using the same idempotency key in `src/features/monitoring-configurations/pages/GitLabConnectionPage.tsx` and `src/features/monitoring-configurations/api/gitlabConnectionApi.ts`.
- [x] T015 [US1] Add edit-mode General and GitLab Connection step integration, keeping GitLab URL unchanged as the hidden field required by the existing full-resource update and preserving ETag/concurrency behavior in `src/features/monitoring-configurations/pages/EditMonitoringConfigurationPage.tsx` and `src/features/monitoring-configurations/pages/GitLabConnectionPage.tsx`.
- [x] T016 [US1] Integrate existing Scope and Authors save callbacks with shared Next/Previous navigation without changing dynamic group scope, policy semantics, or stale-write handling in `src/features/monitoring-configurations/pages/GitLabScopePage.tsx` and `src/features/monitoring-configurations/pages/AuthorPoliciesPage.tsx`.
- [x] T017 [US1] Move the existing schedule editor into the final Scheduling step, connect Previous to Authors and the right-side `Save schedule` action to existing save behavior, and preserve recurrence/DST/stale-write/remove semantics in `src/features/monitoring-configurations/pages/SchedulingPage.tsx` and `src/features/monitoring-configurations/components/ScheduleSection.tsx`.
- [x] T018 [US1] Add create/edit route integration tests for forward/back transitions, stable IDs, direct links, General draft retention, candidate validation failure, and credential-save retry without duplicate creation in `MonitoringConfigurationWizardFlow.test.tsx`; invalid-ID handling remains covered by the existing route/API error boundary.
- [x] T019 [US1] Preserve step save/validation regression coverage proving Next validates and saves before advancing, failed operations retain recoverable values, and Feature 004/014/005/009 behavior remains unchanged across Scope, Authors, Scheduling, and wizard-flow suites.

## Phase 4: User Story 2 - Find each setting and action in its owning step (Priority: P1)

**Goal**: Each setting/action appears only in its specified step or list surface.

**Independent test criteria**: General owns Name/Description/Enable; GitLab Connection owns URL/credential; Scope, Authors, and Scheduling retain only their responsibilities; Delete remains available only from the list; obsolete header shortcuts disappear.

**Dependencies**: Shared layout and the step migrations in US1.

- [x] T020 [US2] Remove GitLab URL from General controls and make GitLab Connection the sole editable URL/credential surface while preserving existing credential masking and save behavior in `src/features/monitoring-configurations/components/MonitoringConfigurationForm.tsx`, `src/features/monitoring-configurations/components/GitLabConnectionPanel.tsx`, and `src/features/monitoring-configurations/components/GitLabCredentialForm.tsx`.
- [x] T021 [US2] Remove Enable/Disable from list/detail surfaces and expose it only in existing-configuration General, preserving existing enable validation/API behavior in `src/features/monitoring-configurations/pages/MonitoringConfigurationsPage.tsx`, `src/features/monitoring-configurations/pages/MonitoringConfigurationDetailsPage.tsx`, and `src/features/monitoring-configurations/pages/EditMonitoringConfigurationPage.tsx`.
- [x] T022 [US2] Remove detail/header Edit General, Configure GitLab Scope, Configure Scheduling, Enable, and Delete shortcuts and remove editable GitLab/Schedule forms from the overview while retaining existing read-only overview, execution history, and manual execution capabilities in `src/features/monitoring-configurations/pages/MonitoringConfigurationDetailsPage.tsx`.
- [x] T023 [US2] Keep New/Open(Edit)/Delete as the list entry points, route New to General and Edit to the unified wizard, retain existing delete confirmation/API, and ensure Delete is absent from all wizard steps in `src/features/monitoring-configurations/pages/MonitoringConfigurationsPage.tsx`.
- [x] T024 [US2] Add field ownership/action-placement tests for every step, list Delete, New/Edit entry points, and absence of obsolete detail shortcuts/global Enable/Delete in `MonitoringConfigurationOwnership.test.tsx`, `create-and-list.test.tsx`, and `update-and-lifecycle.test.tsx`.
- [x] T025 [US2] Preserve and update regressions for General save/Enable, GitLab URL and credential validation/replacement/removal, Scope save, Authors save, Scheduling save/remove, and Delete confirmation across the existing `src/test/features/monitoring-configurations/` suites.

## Phase 5: User Story 3 - Navigate without losing work (Priority: P2)

**Goal**: Fixed navigation remains usable and honors existing validation and unsaved-change protections.

**Independent test criteria**: The bar stays visible without covering content/focus; keyboard users can operate it; dirty or invalid steps cannot silently lose work or bypass required validation.

**Dependencies**: All user-facing routes and page integrations in US1/US2.

- [x] T026 [US3] Coordinate existing step dirty guards with shared Previous/Next, informational stepper, exit-to-list, and browser navigation so Back never implicitly saves; implementation is in the step pages and shared wizard layout.
- [x] T027 [US3] Validate dirty and browser-unload protection, validation failures, retained values, and safe discard across General, GitLab Connection, Scope, Authors, and Scheduling using the wizard-flow, Scope, Authors, and schedule dirty-navigation suites.
- [x] T028 [US3] Run existing axe and keyboard/focus coverage plus fixed-bar/button accessibility tests for step semantics, Previous/Next labels, visible focus, and narrow viewport operation across `src/test/features/monitoring-configurations/`.

## Phase 6: Polish and cross-cutting validation

**Purpose**: Verify responsive layout, preserve approved behavior, and manually compare the screens with their references.

- [x] T029 [P] Run affected frontend tests, complete applicable frontend test suite, and production build; fix Feature 015 regressions in `src/test/` and validate with the existing frontend package scripts.
- [ ] T030 [P] Run candidate-validation unit/API tests and backend regressions; candidate/connection API tests (7 passed) and earlier backend unit suite (274 passed) are validated. Full `tests/api` execution stalled in the environment during `test_execution_details_api.py`; rerun full API suite when the test runner/database environment is responsive. Verify no persistence/migration was introduced in `backend/tests/`.
- [ ] T031 Perform and record manual visual validation against `specs/015-monitoring-configuration-wizard-flow-consolidation/references/03-new-configuration-general.png` for General ownership, stepper, first-step state, and fixed bar; keep open if not actually inspected.
- [ ] T032 Perform and record manual visual validation against `specs/015-monitoring-configuration-wizard-flow-consolidation/references/04-gitlab-connection.png` for URL/credential ownership, previous/next placement, and fixed bar; keep open if not actually inspected.
- [ ] T033 Perform and record manual visual validation against `specs/015-monitoring-configuration-wizard-flow-consolidation/references/05-scope-selection.png` for scope tree/summary, step order, and fixed bar; keep open if not actually inspected.
- [ ] T034 Perform and record manual visual validation against `specs/015-monitoring-configuration-wizard-flow-consolidation/references/06-author-policies.png` for Feature 014 policy UI, wizard consistency, and fixed bar; keep open if not actually inspected.
- [ ] T035 Perform and record manual visual validation against `specs/015-monitoring-configuration-wizard-flow-consolidation/references/07-scheduling.png` for Scheduling-only controls, final action, and fixed bar; keep open if not actually inspected.
- [ ] T036 Perform and record manual visual validation of the Monitoring Configurations list against the existing Feature 013/014 visual system for New/Edit/Delete placement, since Feature 015 supplies no list reference; keep open if not actually inspected.
- [x] T037 Review `src/features/monitoring-configurations/` and `backend/app/` changes against Feature 015 scope, confirming no migration, no credential exposure, no Feature 014 author-policy or Feature 005/009 scheduling semantic change, and no unrelated navigation/action remains.

## Dependencies and execution order

- Phase 1 baseline work precedes code changes.
- Phase 2 candidate-validation contract/use case/API and shared draft/routes/layout precede create/edit and step integrations.
- US1 step integration precedes US2 ownership/action removal tests where both touch the same pages.
- US1 and US2 precede US3 end-to-end unsaved-change/accessibility validation.
- Manual reference validation and final regression follow all screen migrations.
- No database migration or persistence task is required.

## Parallel opportunities

- T002 and T003 can proceed in parallel after baseline paths are verified.
- In Phase 2, T004/T009 may proceed independently; T005 depends on T004; T006 depends on T005; T007 depends on T006. T008 and T009 can be developed independently, while T010 depends on T009.
- Story implementation tasks are intentionally mostly sequential because they share wizard routes and page components; do not parallelize edits to `GitLabConnectionPage.tsx`, `MonitoringConfigurationDetailsPage.tsx`, or route configuration.
- T031–T036 are independent manual screen comparisons once implementation is available.
- T029 and T030 are independently runnable after code changes settle.

## Implementation strategy

Deliver the shared shell and candidate-validation contract first. Complete US1 as the MVP: users can create/edit through the five-step flow with a stable configuration identity. Complete US2 to remove duplicate fields/actions and enforce ownership. Complete US3 to validate fixed navigation, accessibility, responsive behavior, and unsaved-change safety. Finish with frontend/backend regression, build, and manual visual checks. Do not mark manual tasks complete without performing them.

## Phase 7: Convergence remediation

- [x] T038 Add edit/create wizard route regression coverage for forward/back transitions, stable configuration identity, safe invalid-ID handling, and post-create credential-save retry without duplicate creation per US1/FR-001 in `MonitoringConfigurationWizardFlow.test.tsx`.
- [x] T039 Add consolidated field-ownership and action-placement coverage for all steps, list Delete, and obsolete overview actions per US2/FR-002 to FR-008 in `MonitoringConfigurationOwnership.test.tsx` and list regressions.
- [x] T040 Add validation and unsaved-change regression coverage for retained values, Previous behavior, credential discard confirmation, step dirty guards, and browser-unload protection per US3/FR-009 to FR-014 in the wizard, Authors, Scope, and Scheduling tests.
