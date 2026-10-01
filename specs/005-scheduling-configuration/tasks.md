---
description: "Task list for Feature 005 Scheduling Configuration"
---

# Tasks: Feature 005 — Scheduling Configuration

**Input**: Design documents from `specs/005-scheduling-configuration/` (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/api-v1.md`, `quickstart.md`).

**Prerequisites**: plan.md and spec.md; data-model.md, research.md, contracts/api-v1.md, quickstart.md.

**Tests**: Included because the specification explicitly requires automated tests across recurrence calculation, API, persistence, concurrency, and frontend flows.

**Organization**: Tasks are grouped by user story. Shared schedule foundations are completed first because each story relies on the same schedule model and authoritative calculation service.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Different files and no dependency on an incomplete task; safe to implement in parallel.
- **[Story]**: User-story traceability; omitted for setup, foundation, and polish tasks.
- Each task names its affected file path(s); tests and implementation remain separate tasks.

## Phase 1: Setup

**Purpose**: Make IANA timezone behavior reproducible in the supported backend environments.

- [X] T001 Add the first-party `tzdata` runtime dependency to `backend/pyproject.toml` and set `PYTHONTZPATH=""` in `backend/Dockerfile` so the deployed backend consistently uses the packaged timezone database.
- [X] T002 [P] Document the PowerShell environment setup (`$env:PYTHONTZPATH=""`) and timezone-data verification command in `specs/005-scheduling-configuration/quickstart.md` for local backend tests.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the schedule domain, authoritative calculation, persistence schema, and concurrency boundary required by all user stories.

- [X] T003 [P] Create `MonitoringSchedule` domain model and validation in `backend/app/domain/entities/monitoring_schedule.py`: `configured=false` requires all recurrence payload and `created_at` fields null; daily requires both recurrence fields null; weekly requires ISO `day_of_week` 1–7 and null `day_of_month`; monthly requires `day_of_month` 1–31 and null `day_of_week`; execution time is minute-precision local wall time with a supported IANA timezone.
- [X] T004 Add SQLAlchemy schedule-state mapping and Alembic migration `backend/alembic/versions/0004_monitoring_schedule.py` with one row per configuration, positive monotonic version, configured-state nullable payload, recurrence/range constraints, foreign key, and timestamps; preserve soft-retirement behavior and permit configurations with no schedule.
- [X] T005 [P] Define the schedule repository port and transactional compare-and-swap/tombstone persistence in `backend/app/application/ports/monitoring_schedule_repository.py` and `backend/app/infrastructure/database/sqlalchemy_repositories.py`: absent state has virtual version 0; successful state changes increment once; removal retains an unconfigured version tombstone; stale expected versions fail without mutation.
- [X] T006 [P] Add fixed-reference domain tests in `backend/tests/unit/domain/test_schedule_calculator.py` for strict-future semantics (`next_occurrence > reference`), daily/weekly/monthly recurrence, ISO weekdays 1–7, month-end clamping, leap/non-leap February, and year rollover.
- [X] T007 Implement the single pure recurrence service in `backend/app/domain/services/schedule_calculator.py`, accepting a complete schedule and aware reference instant and returning the first strictly later UTC instant; implement DST gap round-trip resolution by shifting forward by the gap while preserving relative position and overlap resolution by selecting the earlier instant.
- [X] T008 Extend `backend/tests/unit/domain/test_schedule_calculator.py` with UTC conversion and fixed cases for `America/Sao_Paulo`, New York spring gap (02:30→03:30), New York fall overlap (first occurrence), and the non-hour `Australia/Lord_Howe` gap; assert no test depends on machine clock.
- [X] T009 Add database-independent schedule repository tests in `backend/tests/unit/infrastructure/test_monitoring_schedule_repository.py` for configured/unconfigured state, version increments, compare-and-swap winner/loser, stale removal, tombstone behavior, and no-op removal preserving current version.

**Checkpoint**: Schedule invariants, the one recurrence calculator, and the persistence/CAS interface are ready; every story can now build on these shared rules.

---

## Phase 3: User Story 1 — Configure a recurrence (Priority: P1) 🎯 MVP

**Goal**: Create, retrieve, and replace a complete daily, weekly, or monthly schedule without changing unrelated Monitoring Configuration data.

**Independent Test**: For an active configuration, create and save each recurrence type, reload it, and confirm recurrence-only fields, time, timezone, enabled state, and unrelated configuration values are preserved. Invalid schedule input must leave a prior valid schedule unchanged.

### Tests for User Story 1

- [X] T010 [P] [US1] Add domain/application validation tests in `backend/tests/unit/application/test_monitoring_schedule_use_cases.py` for missing/invalid time, unsupported timezone, missing/invalid weekly weekday, missing/monthly day outside 1–31, irrelevant recurrence fields, exact preservation of a submitted runtime-supported timezone identifier (including a recognized alias), no custom alias mapping, and unchanged prior schedule on invalid replacement.
- [X] T011 [P] [US1] Add reusable global error-handler mapping tests in `backend/tests/api/test_errors.py` and schedule contract tests in `backend/tests/api/test_monitoring_schedule.py`: verify GET/PUT schedule DTOs, daily/weekly/monthly replacement, exact round-trip of an accepted timezone identifier, `If-Match` required (428), current ETag success, stale ETag (412, top-level `stale_update`, no winner mutation), missing/retired configuration (404), validation (422), and no internal version field in JSON. The reusable tests must assert deterministic top-level status/code mappings: 400/`invalid_request`, 404/`not_found`, 409/`conflict` where applicable, 412/`stale_update`, 422/`validation_error`, 500/`unexpected_error`, preserving 428/`invalid_precondition` and 503/`unexpected_error`; verify safe field-level `invalid_schedule`/`invalid_timezone` values and absence of raw exception/stack/database/timezone/provider/parser/request-sensitive details, especially for 500 responses.
- [X] T012 [P] [US1] Add timezone catalogue API tests in `backend/tests/api/test_schedule_timezones.py` for sorted supported IANA identifiers, UTC availability, exact round-trip preservation of a valid identifier/alias, and missing runtime timezone data returning safe `unexpected_error` without internal details.
- [X] T013 [P] [US1] Add PostgreSQL persistence and migration tests in `backend/tests/integration/test_monitoring_schedule_persistence.py` for zero-or-one schedule state, recurrence constraints, initial version 0 to 1, version increments, and migration upgrade/downgrade.

### Implementation for User Story 1

- [X] T014 [US1] Implement schedule read and full-replacement application use cases in `backend/app/application/use_cases/get_monitoring_schedule.py` and `backend/app/application/use_cases/replace_monitoring_schedule.py`; use the injected reference instant and shared calculator for enabled-schedule responses; do not mutate configuration enabled state, credential, or scope.
- [X] T015 [US1] Add Pydantic request/response schemas and schedule/timezone API routes in `backend/app/api/v1/monitoring_schedules.py` and `backend/app/api/v1/schemas.py`, and extend the reusable global handler in `backend/app/api/errors.py` to produce Problem Details compatible with the existing contract and deterministic safe top-level mappings: 400/`invalid_request`, 404/`not_found`, 409/`conflict` where applicable, 412/`stale_update`, 422/`validation_error`, 500/`unexpected_error`, preserving project conventions 428/`invalid_precondition` and 503/`unexpected_error`. Implement GET/PUT `/api/v1/monitoring-configurations/{id}/schedule`, `GET /api/v1/schedule-timezones`, and ETag/If-Match. Keep generic error mapping in the global handler rather than scheduling controllers; return generic safe 500 content without exception/stack/database/timezone/request-sensitive details, and preserve safe logging policy. Add/update reusable tests in `backend/tests/api/test_errors.py` and schedule contract tests in `backend/tests/api/test_monitoring_schedule.py` for every mapping and 500 redaction; preserve compatibility with `specs/005-scheduling-configuration/contracts/api-v1.md`.
- [X] T016 [US1] Implement `backend/app/application/use_cases/list_schedule_timezones.py` and register schedule routes/dependencies in `backend/app/api/main.py` and `backend/app/api/dependencies.py` only after the route module exists; ensure active-configuration checks follow Feature 002 retirement semantics.
- [X] T017 [US1] Add schedule API DTOs and typed request/response functions in `src/features/monitoring-configurations/types/schedule.ts` and `src/features/monitoring-configurations/api/scheduleApi.ts`, including preservation of ETag as conditional-write metadata and no schedule-version property in public JSON models.
- [X] T018 [US1] Add schedule fetching/saving state and error handling in `src/features/monitoring-configurations/hooks/useMonitoringSchedule.ts`; keep persisted data, editable draft, and request state separate, retain drafts after validation/network/412 failures, and never automatically retry a stale mutation.
- [X] T019 [US1] Implement recurrence-specific form controls and recurrence switching in `src/features/monitoring-configurations/components/ScheduleForm.tsx`; daily clears both recurrence fields, weekly requires ISO weekday and clears month day, and monthly requires day 1–31 and clears weekday.
- [X] T020 [US1] Add a backend-backed timezone selector and schedule section in `src/features/monitoring-configurations/components/TimezoneSelector.tsx` and `src/features/monitoring-configurations/components/ScheduleSection.tsx`; preserve selected supported identifier, label the control “Automatic scheduling,” distinguish it from Monitoring Configuration enabled state, and provide no-schedule/loading/error/saved states.
- [X] T021 [US1] Integrate the schedule section into the existing configuration details/edit route in `src/features/monitoring-configurations/pages/MonitoringConfigurationDetailsPage.tsx` and `src/app/routes/routeConfig.tsx` using existing shell and form patterns.
- [X] T022 [P] [US1] Add frontend US1 integration tests in `src/test/features/monitoring-configurations/schedule-form.test.tsx` for no-schedule, daily/weekly/monthly fields, recurrence field clearing, timezone choice, create/edit/reload, validation, independent configuration enabled state, and retained draft after failed save.

**Checkpoint**: Users can save and reload all schedule recurrence types; invalid or stale writes do not replace valid persisted state.

---

## Phase 4: User Story 2 — Understand the next scheduled occurrence (Priority: P1)

**Goal**: Show backend-calculated previews for persisted schedules and valid unsaved candidates without persisting preview state.

**Independent Test**: With explicit fixed reference instants, compare the API preview for each recurrence and DST edge to expected UTC instants; candidate preview leaves persisted schedule state unchanged and the frontend only formats the returned instant.

### Tests for User Story 2

- [X] T023 [P] [US2] Add candidate preview API tests in `backend/tests/api/test_monitoring_schedule_preview.py` for valid daily/weekly/monthly candidates, optional fixed `referenceInstant`, disabled candidate null result, invalid candidate 422 with top-level `validation_error`, unchanged database state before/after preview, normalized error codes, and assertions that response bodies never contain raw exception text, stack traces, database/timezone internals, provider/runtime response bodies, low-level parsing errors, or request-sensitive values; shared status/code mapping coverage is in T011.
- [X] T024 [P] [US2] Add application preview tests in `backend/tests/unit/application/test_schedule_preview.py` proving the same domain calculator is used for saved and unsaved schedules, the explicit reference is honored, and preview performs no repository mutation.
- [X] T025 [P] [US2] Add frontend preview tests in `src/test/features/monitoring-configurations/schedule-preview.test.tsx` for loading, success, disabled/no-preview, validation feedback, timezone-formatted occurrence, refresh after candidate changes, and copy that does not promise execution.

### Implementation for User Story 2

- [X] T026 [US2] Implement candidate preview use case in `backend/app/application/use_cases/preview_monitoring_schedule.py`; validate a complete candidate, accept/pass an optional explicit aware reference instant, return null for disabled candidate, and never persist the candidate.
- [X] T027 [US2] Add `POST /api/v1/monitoring-configurations/{id}/schedule/preview` request/response schemas and route in `backend/app/api/v1/monitoring_schedules.py`; return only the calculated occurrence and rely on the global handler from T015 for normalized safe Problem Details status/code mappings. Never expose raw exception text, stack traces, database/timezone internals, provider/runtime response bodies, low-level parser errors, or request-sensitive values.
- [X] T028 [US2] Implement preview API integration in `src/features/monitoring-configurations/api/scheduleApi.ts` and `src/features/monitoring-configurations/hooks/useMonitoringSchedule.ts`; do not implement recurrence arithmetic in TypeScript.
- [X] T029 [US2] Add `NextOccurrencePreview` presentation in `src/features/monitoring-configurations/components/NextOccurrencePreview.tsx` and integrate it into `ScheduleForm.tsx`; format the server instant in the selected schedule timezone and label it “Next scheduled occurrence”/preview.
- [X] T030 [P] [US2] Update API contract and user guidance in `specs/005-scheduling-configuration/contracts/api-v1.md` and `specs/005-scheduling-configuration/quickstart.md` to match preview payload, validation, normalized safe errors, and fixed-reference test usage.

**Checkpoint**: Saved and unsaved valid schedules use the same backend recurrence semantics; preview is transient and never an execution.

---

## Phase 5: User Story 3 — Manage schedule lifecycle independently (Priority: P2)

**Goal**: Disable/re-enable or remove schedule intent while preserving the Monitoring Configuration, credential, scope, and independent enabled state.

**Independent Test**: For Monitoring Configurations in both enabled states, disable and re-enable a schedule, remove it, reload, and confirm schedule absence is distinct from disabled state while all unrelated configuration data remains unchanged.

### Tests for User Story 3

- [X] T031 [P] [US3] Add lifecycle and isolation tests in `backend/tests/api/test_monitoring_schedule_lifecycle.py` for disable/re-enable retaining recurrence, DELETE clearing schedule only, absent schedule result, repeated current-version removal, and preservation of configuration enabled state, GitLab credential, and GitLab scope.
- [X] T032 [P] [US3] Add PostgreSQL concurrency tests in `backend/tests/integration/test_monitoring_schedule_concurrency.py` for two simultaneous If-Match mutations (one commits and one gets 412), a delayed stale writer, remove/recreate ABA protection via tombstone, and final state matching the highest committed version.
- [X] T033 [P] [US3] Add frontend lifecycle and deterministic stale-update tests in `src/test/features/monitoring-configurations/schedule-lifecycle.test.tsx`: load version N, let a competing update persist N+1, submit the stale draft, return HTTP 412, and assert the winning server schedule remains authoritative; the rejected draft stays visible and unchanged; conflict feedback is clear/programmatically available; no automatic retry or overwrite occurs; and the user can review before proceeding. Also cover disable/re-enable, distinct no-schedule/disabled state, removal confirmation, and unrelated configuration preservation.

### Implementation for User Story 3

- [X] T034 [US3] Implement conditional schedule removal use case in `backend/app/application/use_cases/remove_monitoring_schedule.py`; compare expected schedule version atomically, clear configured payload only, increment/tombstone on state change, and preserve unrelated Monitoring Configuration data.
- [X] T035 [US3] Add conditional DELETE route in `backend/app/api/v1/monitoring_schedules.py` requiring `If-Match`, returning 204 plus current/new ETag, mapping stale versions to 412, and keeping removal distinct from configuration retirement.
- [X] T036 [US3] Add confirmed remove and lifecycle status controls in `src/features/monitoring-configurations/components/ScheduleSection.tsx`; removal must not change Monitoring Configuration enabled state, credential, scope, or other configuration fields.

**Checkpoint**: Schedule can be disabled, re-enabled, or removed with optimistic concurrency and no mutation of unrelated configuration state.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate integration across all stories and enforce Feature 005's boundary.

- [X] T038 [P] Add end-to-end/integration-style frontend coverage in `src/test/features/monitoring-configurations/schedule-workflow.test.tsx` for three complete journeys: daily, weekly, and monthly. For each journey, start from an existing Monitoring Configuration fixture with representative unrelated data (name, description, GitLab URL, enabled status, safely exposed GitLab connection metadata, and existing GitLab scope selections where available); open schedule configuration; select that recurrence; fill its required recurrence-specific fields; choose time and a supported timezone; request/render the server preview; save; reload the Monitoring Configuration and schedule; assert the correct recurrence-specific values persisted; and verify every fixture value for unrelated configuration fields remains unchanged. Do not require, inspect, or expose sensitive credential values. Reuse shared fixtures/helpers, but keep explicit assertions for each of the three recurrence journeys.
- [X] T039 Run all backend tests from `backend/` with `pytest`; run `pytest tests/integration/test_monitoring_schedule_persistence.py tests/integration/test_monitoring_schedule_concurrency.py` against PostgreSQL and record explicitly if PostgreSQL is unavailable in `specs/005-scheduling-configuration/quickstart.md`.
- [X] T040 Run all frontend tests with `npm test -- --run` and production build with `npm run build` from repository root; record outcomes in `specs/005-scheduling-configuration/quickstart.md`.
- [X] T041 Review `backend/app`, `src/`, and `specs/005-scheduling-configuration/` to ensure Feature 005 adds no scheduler polling, queue, MiningExecution, eligibility evaluation, cloning, mining, findings, or execution-history behavior; document the scope review in `specs/005-scheduling-configuration/quickstart.md`.
- [X] T042 Reconcile requirement-to-task traceability in `specs/005-scheduling-configuration/tasks.md` against FR-001–FR-025 and SC-001–SC-010; ensure HTTP 412 and safe error codes, supported timezone/alias policy, DST gap/fold rules, accessibility criteria, and PostgreSQL-only integration constraints are explicit.
- [X] T043 Add scheduling accessibility verification in `src/test/features/monitoring-configurations/schedule-accessibility.test.tsx` using existing `axe-core` and Testing Library tooling; automate keyboard operation/focus order for recurrence/timezone/time/enabled/save/remove controls, associated labels and required/selected/enabled states, field-linked textual validation feedback (not color-only), preview/conflict feedback availability, axe checks, and confirmation-dialog focus movement. Document manual visual-focus-indicator inspection (and any remaining dialog-focus behavior automation cannot reliably assert) in `specs/005-scheduling-configuration/quickstart.md`; do not add an accessibility framework.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No feature-code dependencies. T001 must precede timezone-backed validation and tests; T002 can proceed in parallel.
- **Foundational (Phase 2)**: Depends on setup. Complete domain invariants, timezone calculator, persistence schema/repository CAS, and foundational tests before story work.
- **User Story 1 (Phase 3)**: Depends on Phase 2. Delivers persisted schedule configuration and the MVP workflow.
- **User Story 2 (Phase 4)**: Depends on Phase 2 and integrates with US1 schedule representation; calculation is already shared foundation. Candidate preview and preview UI are independently testable against mocked API.
- **User Story 3 (Phase 5)**: Depends on Phase 2 and the US1 schedule API/form. Adds removal and explicit lifecycle concurrency behavior.
- **Polish (Phase 6)**: Depends on all desired stories.

### User Story Dependencies

- **US1 (P1)**: Starts after Foundation; first user-visible increment and MVP.
- **US2 (P1)**: Starts after Foundation; schedule read/write uses the shared calculator. UI integration depends on the US1 form/API surface, but its preview endpoint can be implemented/tested independently.
- **US3 (P2)**: Starts after Foundation; disable state is part of full replacement, while deletion UI/API integrates with the US1 schedule surface.

### Parallel Opportunities

- T002 may run parallel with T001; T003 and T005 can proceed in parallel once their shared domain interfaces are agreed. T006's pure calculation cases can be authored in parallel with domain validation/model work; T007 follows the test contract.
- Within US1, T010–T013 tests can be authored in parallel. API, frontend types/hooks, and form work can be split after DTO/error contract agreement; route registration waits for its router module.
- Within US2, T023–T025 tests can be authored in parallel; backend preview use case and frontend preview presentation can proceed in parallel after the endpoint contract is stable.
- Within US3, T031–T033 tests can be authored in parallel; backend removal and frontend confirmation work can proceed in parallel against the defined conditional DELETE contract.
- PostgreSQL integration tests require a PostgreSQL instance and must not be substituted with SQLite. Database-independent suites can run regardless of PostgreSQL availability.

### Parallel Example: User Story 1

```text
T010 application validation tests
T011 schedule API contract tests
T012 timezone catalogue tests
T013 PostgreSQL persistence/migration tests
```

### Parallel Example: User Story 2

```text
T023 candidate preview API tests
T024 application no-mutation preview tests
T025 frontend preview tests
```

### Parallel Example: User Story 3

```text
T031 lifecycle/isolation API tests
T032 PostgreSQL concurrency tests
T033 frontend lifecycle tests
```

## Implementation Strategy

### MVP First (User Story 1)

1. Complete timezone setup and all foundational tasks.
2. Implement US1 to create, retrieve, replace, and reload schedules for all recurrence types.
3. Validate US1 independently, including PostgreSQL persistence where available.
4. Add US2 candidate preview and preview presentation.
5. Add US3 disable/re-enable/removal lifecycle and concurrency behavior.
6. Run complete backend/frontend verification and scope review; no scheduler or execution functionality is part of this increment.

## Notes

- `[P]` tasks touch independent files and have no dependency on unfinished work.
- `[US1]`, `[US2]`, and `[US3]` map to the corresponding `spec.md` user stories.
- Checkboxes indicate implementation task completion; they are separate from reviewer-owned checklist markers in `checklists/scheduling.md`.
- A stale `If-Match` returns HTTP 412 with normalized code `stale_update`; missing `If-Match` returns HTTP 428 with code `invalid_precondition`.
- PostgreSQL integration work is not complete unless it was actually run against PostgreSQL.

## Requirement-to-Task Traceability

| Requirement | Task coverage |
|---|---|
| FR-001 | T003–T005, T014, T020, T034–T035 |
| FR-002 | T003, T010, T014 |
| FR-003 | T006–T007, T010 |
| FR-004 | T006–T008, T010 |
| FR-005 | T006–T008 |
| FR-006 | T001–T003, T010–T012, T015, T020 |
| FR-007 | T007–T008 |
| FR-008 | T007–T008 |
| FR-009 | T006–T008 |
| FR-010 | T026–T029 |
| FR-011 | T014, T023–T029 |
| FR-012 | T014–T016, T034–T035 |
| FR-013 | T003, T019 |
| FR-014 | T019, T031, T033, T036 |
| FR-015 | T014, T031, T036 |
| FR-016 | T031, T034, T036 |
| FR-017 | T010–T011, T015, T027 |
| FR-018 | T018, T022, T033, T044 |
| FR-019 | T003–T005, T014, T026–T027 |
| FR-020 | T020, T029, T031, T033, T036 |
| FR-021 | T005, T009, T011, T015, T018, T032–T035 |
| FR-022 | T006–T008 |
| FR-023 | T041 |
| FR-024 | T020, T022, T033, T043 |
| FR-025 | T011–T012, T015, T023, T027, T030 |
| SC-001 | T038 (daily, weekly, and monthly journeys verify saved schedule and unchanged unrelated configuration); T022 (form-level supporting coverage) |
| SC-002 | T006–T008 |
| SC-003 | T006–T008 |
| SC-004 | T008 |
| SC-005 | T014, T031, T033, T036, T038 |
| SC-006 | T020, T025, T033, T036 |
| SC-007 | T041 |
| SC-008 | T032–T033 |
| SC-009 | T033, T043, T045 |
| SC-010 | T011–T012, T023, T027 |

## Phase 7: Convergence

- [X] T044 [US1] Expose when the schedule draft differs from the persisted schedule and guard route/browser navigation against discarding that draft, using the existing GitLabScopePage dirty-form pattern; add tests for clean navigation, dirty-state visibility, successful-save reset, explicit discard, route-confirmation stay/leave behavior, and browser `beforeunload` protection per FR-018 and the plan's frontend dirty-state decision.
- [ ] T045 [BLOCKED: browser/Computer Use unavailable] Manually inspect visible keyboard-focus indicators in a real browser for the recurrence selector, timezone selector, time input, Automatic scheduling switch, save/remove actions, and removal dialog; fix any focus-visibility defect and record the browser, controls checked, and outcome in specs/005-scheduling-configuration/quickstart.md per SC-009 and T043. Keep open until visual inspection is actually performed.
