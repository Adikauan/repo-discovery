---
description: "Dependency-ordered implementation tasks for Feature 006"
---

# Tasks: Execution Model and History

**Input**: Design documents from `specs/006-execution-model-history/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [API contract](contracts/api-v1.md)

**Organization**: Tasks are grouped by the three P1 user stories. Automated tests are included because the specification explicitly requires backend, PostgreSQL, API, and frontend coverage.

**Task format**: Every task uses `- [ ] T### [P?] [US#?] Description with exact file path`. `[P]` marks tasks that can proceed independently; story-phase tasks carry `[US1]`, `[US2]`, or `[US3]`.

## Phase 1: Setup

**Purpose**: Add feature-level client types and API adapter structure without changing shared project setup or adding dependencies.

- [X] T001 [P] Define frontend execution wire enums and DTO types (`manual|scheduled`, `pending|running|completed|partially_completed|failed`, list/detail/snapshot/pagination, nullable `completionMeaning` on details) in `src/features/executions/types/execution.ts`.
- [X] T002 Add typed execution API functions for manual creation, global/configuration lists, and details using `apiRequest` in `src/features/executions/api/executionsApi.ts` (depends on T001).

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define the shared domain and PostgreSQL foundation required by all three user stories.

- [X] T003 [P] Add fixed-reference-time unit tests for valid/invalid lifecycle transitions guarded by the expected source status, one-time timestamps, final-state immutability, zero counters, and trigger/status enum values in `backend/tests/unit/test_mining_execution.py`.
- [X] T004 [P] Add snapshot schema tests for required configuration/scope fields, empty scope, group intent retention, schema version, and rejection/absence of credential fields in `backend/tests/unit/test_execution_snapshot.py`.
- [X] T005 [P] Implement `TriggerType` (`manual`, `scheduled`), `ExecutionStatus` (`pending`, `running`, `completed`, `partially_completed`, `failed`), lifecycle/timestamp/counter invariants, and nullable safe error bounds (`error_code` ≤64 characters, `error_summary` ≤500 characters) in `backend/app/domain/entities/mining_execution.py`; expose no arbitrary public status/counter mutation.
- [X] T006 [P] Implement typed `ExecutionSnapshotV1` (`schema_version=1`) in `backend/app/domain/entities/execution_snapshot.py`, capturing configuration ID/name/enabled state/normalized GitLab URL/revision, scope version, selected group/project stable IDs and safe metadata, internal instance fingerprints, trigger and optional scheduled context; exclude credential values/revision and transient UI state.
- [X] T007 [P] Add `MiningExecutionRecord` to `backend/app/infrastructure/database/models.py` with UUID identity; non-null restrictive configuration FK; trigger values `manual|scheduled`; status values `pending|running|completed|partially_completed|failed`; UTC `created_at`, nullable `started_at`/`completed_at`; nonnegative counters defaulting to zero; nullable `error_code` max 64 characters; nullable `error_summary` max 500 characters; typed JSONB snapshot; and newest/history/filter indexes.
- [X] T008 [P] Create Alembic revision `backend/alembic/versions/0005_mining_executions.py` after `0004_monitoring_schedule`, including the active partial unique index for `pending`/`running` and applicable timestamp/counter/status constraints (independent file from T007).
- [X] T009 [P] Define execution repository/UoW operations for active lookup, owner-row lock, active-execution row lock/re-read, expected-current-status conditional transition, add, get, filtered page, and count in `backend/app/application/ports/mining_execution_repository.py` and `backend/app/application/ports/monitoring_configuration_repository.py`; do not add an execution revision field.
- [X] T010 Implement SQLAlchemy execution persistence and `SqlAlchemyUnitOfWork` support in `backend/app/infrastructure/database/sqlalchemy_repositories.py`, plus transaction isolation setup in `backend/app/infrastructure/database/session.py` and validated `EXECUTION_STALENESS_THRESHOLD_SECONDS` configuration in `backend/app/config.py` (default 300 seconds; reject non-finite/non-positive values): use PostgreSQL repeatable-read, owner-row `SELECT ... FOR UPDATE NOWAIT`, lock/re-read candidate active execution, conditional lifecycle updates, and safely normalize lock/serialization/partial-index conflicts (depends on T007–T009).
- [X] T011 Extend the PostgreSQL migration integration test in `backend/tests/integration/test_migrations.py` to assert the execution table/partial index after upgrade and absence of Feature 006 objects after downgrade; do not substitute SQLite (after T008).

**Checkpoint**: Domain lifecycle, typed snapshots, migration, repository port, and PostgreSQL concurrency primitives are ready for independently scoped story work.

## Phase 3: User Story 1 - Request a manual execution (Priority: P1) 🎯 MVP

**Goal**: Allow manual execution for an eligible non-retired configuration, snapshot it immutably, enforce concurrency/idempotency, and finish the Feature 006 orchestration path without mining.

**Independent Test**: A disabled but non-retired configuration with no active execution accepts a request. The created record starts pending, captures configuration/scope intent without credential data, transitions through running to completed, preserves zero counters, and creates no repository/mining/finding records. Retired/missing and non-stale active cases are rejected safely; stale active cases are reconciled before replacement creation; overlapping PostgreSQL requests produce no duplicate active execution.

### Tests for User Story 1

- [X] T012 [P] [US1] Add fixed-reference-time application tests for the internal `pending → running → completed` sequence and controlled failure finalization; assert that only a non-stale pending/running execution conflicts, while stale pending/running executions follow FR-027 and reconcile to `failed`; cover `completed_at`, preserved `started_at` semantics, `execution_interrupted` plus safe summary with no raw runtime detail, unchanged snapshot/counters, no fabricated data, replacement creation after reconciliation, invalid threshold configuration, disabled eligibility, retired/missing rejection, immutable snapshots, and same-key replay in `backend/tests/unit/test_create_manual_execution.py`.
- [X] T013 [P] [US1] Add PostgreSQL integration tests for execution persistence, same-key replay, non-stale active conflict, two synchronized requests racing on one stale active row, and a completion-versus-reconciliation race; assert row locking and expected-persisted-status conditional updates, exactly one reconciliation/replacement wins, terminal state cannot be overwritten, only one active row remains, and the loser receives a safe conflict in `backend/tests/integration/test_manual_execution_concurrency.py`.
- [X] T014 [P] [US1] Add API contract tests for manual-only bodyless creation, `Location`, HTTP 201 completed success and controlled-failure `failed` response, stale reconciliation followed by replacement creation, disabled acceptance, missing/retired 404, fresh active conflict 409, idempotency validation/replay including stale same-key behavior, safe DTO/error projection, and rejection of arbitrary status fields in `backend/tests/api/test_manual_execution_api.py`.

### Implementation for User Story 1

- [X] T015 [US1] Implement `CreateManualExecution` in `backend/app/application/use_cases/create_manual_execution.py`: under the owner configuration lock, compare active age against the configured threshold using a reference UTC instant; conflict only for non-stale active work, or lock/re-read and verify a stale `pending`/`running` execution still has the expected status and remains stale before lifecycle-transitioning it to `failed` with `completed_at`, `execution_interrupted`, and safe summary, preserving snapshot/counters. Atomically reconcile and create a new pending execution for a distinct request, then use expected-status-guarded transitions for `pending → running → completed`; on controlled orchestration failure persist safe `failed`. Preserve idempotent replay semantics and ensure no mining records/data are created (after T012–T014).
- [X] T016 [US1] Create shared execution API foundations: manual execution request/response schemas in `backend/app/api/v1/execution_schemas.py`, router module and `POST /monitoring-configurations/{configurationId}/executions` in `backend/app/api/v1/executions.py`; return the current finalized safe representation with HTTP `201` and `Location` (completed on success, failed for a controlled persisted orchestration failure), set nullable `completionMeaning` only for completed, normalize conflicts, and register the router in `backend/app/api/main.py` only after the module exists (after T015).
- [X] T017 [US1] Add a clearly named manual execution action, loading state, accessible success/conflict feedback, and access to the returned execution in `src/features/monitoring-configurations/pages/MonitoringConfigurationDetailsPage.tsx` using `src/features/executions/api/executionsApi.ts`.
- [X] T018 [P] [US1] Add frontend journey tests for manual success, disabled configuration eligibility, loading, accessible feedback for a non-stale active-execution conflict, and no mining-implied wording in `src/test/features/executions/manual-execution.test.tsx`.

**Checkpoint**: The manual request journey is independently usable and leaves no active execution after the orchestration-only flow.

## Phase 4: User Story 2 - Review execution history (Priority: P1)

**Goal**: Provide global and configuration-specific newest-first history with backend filtering and bounded pagination.

**Independent Test**: Seed executions with varied timestamps/status/trigger/configuration and tied creation timestamps; verify global and per-configuration filters, page bounds, stable `createdAt DESC, id DESC` ordering, and empty/error states.

### Tests for User Story 2

- [X] T019 [P] [US2] Add repository/application tests for global and configuration-scoped list filtering, page/pageSize bounds, total counts, retired-configuration history access, and stable createdAt/id ordering in `backend/tests/unit/test_list_executions.py` (after shared persistence foundations T009–T010).
- [X] T020 [P] [US2] Add API tests for global/configuration history routes, filters, pagination validation, retired versus missing configuration, newest-first ordering, and safe list DTOs in `backend/tests/api/test_execution_history_api.py` (after shared router/schema foundations T016).

### Implementation for User Story 2

- [X] T021 [US2] Implement SQL-filtered, bounded execution list and count queries (`page` default 1, `pageSize` default 25/max 100; order `created_at DESC, id DESC`) in `backend/app/infrastructure/database/sqlalchemy_repositories.py` (after T019).
- [X] T022 [US2] Implement `ListExecutions` and `ListConfigurationExecutions` application use cases with status/trigger/configuration filters and retired-history semantics in `backend/app/application/use_cases/list_executions.py` (after T021).
- [X] T023 [US2] Extend the shared router and schema modules with `GET /executions` and `GET /monitoring-configurations/{configurationId}/executions`, using dedicated paginated response schemas in `backend/app/api/v1/executions.py` and `backend/app/api/v1/execution_schemas.py` (after T016 shared foundations and T021–T022).
- [X] T024 [US2] Replace the global executions placeholder with an accessible paginated/filterable history table and loading/empty/error states in `src/features/executions/pages/ExecutionsPage.tsx` (after T023).
- [X] T025 [US2] Replace the configuration execution-history placeholder with a configuration-scoped history table and loading/empty/error states in `src/features/monitoring-configurations/pages/ConfigurationExecutionsPage.tsx` (after T023).
- [X] T026 [P] [US2] Add frontend tests for global and scoped history, filters, page navigation, deterministic ordering display, empty/loading/error states, and keyboard-accessible row navigation in `src/test/features/executions/execution-history.test.tsx`.

**Checkpoint**: Users can find execution history globally and for a configuration without loading an unbounded result.

## Phase 5: User Story 3 - Inspect an execution and its lifecycle (Priority: P1)

**Goal**: Show immutable historical snapshot context, lifecycle timestamps, derived duration, truthful counters, and safe errors without exposing storage internals.

**Independent Test**: Open pending/running/final records through controlled fixtures and verify valid state/timestamp display, safe snapshot projection, zero counters for Feature 006, no secret/fingerprint/snapshot-version fields, final-state immutability, and not-found behavior.

### Tests for User Story 3

- [X] T027 [P] [US3] Add application/API tests for execution detail projection, derived duration, safe normalized error summary, missing execution, absence of raw snapshot JSON/fingerprint/credential fields, and `completionMeaning` equal to the controlled no-mining statement only for `completed` and null/absent for all other statuses in `backend/tests/unit/test_get_execution.py` and `backend/tests/api/test_execution_details_api.py` (API tests use the shared foundations from T016).
- [X] T028 [P] [US3] Add PostgreSQL integration tests proving execution snapshot values remain unchanged and readable after configuration edits, scope replacement, credential replacement, and soft retirement in `backend/tests/integration/test_execution_snapshot_retention.py`.

### Implementation for User Story 3

- [X] T029 [US3] Implement `GetExecution` and dedicated public snapshot projection in `backend/app/application/use_cases/get_execution.py`; derive duration from UTC lifecycle timestamps, never return raw JSONB, and set completionMeaning only for completed executions (after T027 application tests).
- [X] T030 [US3] Extend the shared router/schema modules with `GET /executions/{executionId}` and detail DTO mapping in `backend/app/api/v1/executions.py` and `backend/app/api/v1/execution_schemas.py`, returning normalized 404 and safe failure metadata; `completionMeaning` is nullable and only populated for completed (after T023 and T029 to avoid competing edits to shared API modules).
- [X] T031 [US3] Replace the execution detail placeholder/fake dashboard content with semantic headings, status/trigger, safe snapshot, timestamps, derived duration, counters, safe error, and explicit “no repository mining occurred” wording in `src/features/executions/pages/ExecutionDetailsPage.tsx` (after T030).
- [X] T032 [P] [US3] Add execution detail tests for snapshot rendering, all status labels, timestamps/duration, truthful zero counters, safe failure output, no-mining language, and accessible semantic structure in `src/test/features/executions/execution-details.test.tsx`.

**Checkpoint**: Historical execution details remain understandable without querying mutable configuration children or implying mining outcomes.

## Phase 6: Polish and Cross-Cutting Validation

**Purpose**: Verify cross-story privacy, migration, accessibility, complete suite, and documented PostgreSQL limitations.

- [X] T033 [P] Add cross-layer API assertions that execution responses omit token/ciphertext, credential revision, internal scope fingerprint, raw snapshot, and schema version in `backend/tests/api/test_execution_security_contract.py`.
- [X] T034 [P] Add/extend axe and keyboard accessibility checks for manual action, accessible conflict/loading feedback, history tables, status text, and execution detail headings in `src/test/features/executions/execution-accessibility.test.tsx`.
- [X] T035 Run backend unit/API tests, PostgreSQL integration/concurrency tests when `TEST_DATABASE_URL` is available, and migration checks; record skipped PostgreSQL validation as not executed in `specs/006-execution-model-history/quickstart.md`.
- [X] T036 Run the complete frontend test suite and production build, then complete the Feature 006 end-to-end scenarios in `specs/006-execution-model-history/quickstart.md`.

## Requirement-to-Task Traceability

| Requirements | Tasks |
|---|---|
| FR-001–FR-006; SC-002; SC-010 (eligibility, active exclusion, concurrency) | T003, T005, T007–T015, T018 |
| FR-001, FR-016, FR-019, FR-021, FR-024; shared frontend adapter and normalized API error handling | T002 |
| FR-002–FR-003; FR-010–FR-014; FR-022–FR-023; SC-001, SC-005, SC-007 | T001, T003–T006, T012–T018, T027, T029–T032 |
| FR-007–FR-009; FR-020; FR-025; SC-003, SC-006 | T004, T006–T008, T012, T015, T027–T029, T033 |
| FR-026–FR-027; controlled failure, request-time stale reconciliation, and recovery to later manual eligibility | T010, T012–T016, T027, T030, T033 |
| FR-015; FR-021; FR-024; safe outcomes and no public status mutation | T014–T016, T027, T030, T033 |
| FR-016–FR-018; SC-004 | T019–T026, T030–T032 |
| FR-019; SC-008 | T014, T016–T018, T031–T034 |
| FR-004–FR-005; idempotent retry requirement; SC-002 | T008–T015, T018–T019 |
| SC-009 and all scope boundaries | T012–T018, T031, T033, T035–T036 |

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 precedes T002; frontend contracts can be developed alongside backend foundation once the type file exists.
- **Foundational (Phase 2)**: Depends on Setup. T003/T004 may run in parallel, then T005/T006; T007 and T008 can be prepared independently against the agreed schema; T009/T010 integrate these pieces. This phase blocks all story work.
- **User Stories (Phase 3+)**: All depend on the foundational aggregate, persistence, and concurrency boundary. US1 also creates the shared execution router/schema foundations in T016; US2 and US3 extend those modules and therefore depend on the US1 API foundation.
- **Polish (Phase 6)**: Depends on the desired stories being integrated; PostgreSQL-only assertions are reportable only if they actually ran against PostgreSQL.

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2. It establishes the manual creation path and MVP. It does not require history-list UI or the completed detail page to create and access the returned execution resource.
- **US2 (P1)**: Domain/repository list work and test preparation can start after Phase 2, but API implementation in T023 depends on T016 because it extends `executions.py` and `execution_schemas.py` created by US1. UI work may proceed against the documented contract, but the stories are not fully implementation-independent.
- **US3 (P1)**: Detail tests and projection design may be prepared after Phase 2, but API implementation in T030 depends on the shared modules from T016 and is ordered after T023 to avoid competing edits to `executions.py` and `execution_schemas.py`.

### Parallel Opportunities

- T003 and T004 are separate domain test files; T005 and T006 are separate domain modules.
- T007 and T008 target ORM and Alembic files; T012–T014 are separate US1 test layers.
- T019 and T020 are independent US2 test layers after shared foundations; T024 and T025 target separate pages.
- T027 and T028 target separate US3 test layers; T031 and T032 can be split across implementation and tests. Shared API module changes remain ordered T016 → T023 → T030.
- T033 and T034 are independent privacy and accessibility validation suites.

## Parallel Example: User Story 1

```text
After Phase 2:
Task T012: application-level manual creation/eligibility/lifecycle/idempotency tests
Task T013: PostgreSQL owner-lock and active-index concurrency tests
Task T014: API contract/security/error tests

Then implement in dependency order:
T015 CreateManualExecution use case → T016 API route/registration → T017 UI action
T018 frontend journey tests may be prepared in parallel with T017 after T001–T002.
```

## Implementation Strategy

### MVP First

Complete Setup and Foundational phases, then US1. The MVP demonstrates one safe manual request, immutable snapshot, concurrency protection, zero counters, and completion without mining. Validate disabled/retired eligibility, same-key replay, and PostgreSQL overlap behavior before expanding history UI.

### Incremental Delivery

1. US1 adds manual request, lifecycle, and shared router/schema foundations.
2. US2 extends those shared modules with discoverable global/configuration history.
3. US3 extends the shared modules with historical detail presentation after US2 API edits.
4. Polish closes cross-layer secret, accessibility, and complete-suite validation.

No phase implements scheduled dispatch, repository processing, findings, or analytics.

## Notes

- Every task is unchecked until implementation is actually completed.
- `[P]` tasks use distinct files and have no dependency on incomplete tasks in the same phase.
- Story tasks carry the required `[US1]`, `[US2]`, or `[US3]` label.
- PostgreSQL concurrency behavior must not be reported as validated if PostgreSQL integration tests are skipped.
- Reviewer-owned markers in `checklists/` are not changed by this task-generation workflow.

## Phase 7: Convergence

- [X] T037 CRITICAL: Repair backend/tests/integration/test_execution_snapshot_retention.py with valid 64-character GitLab instance fingerprints and seed an existing credential before replacing it after execution creation; then run the PostgreSQL test to verify snapshot immutability across configuration, scope, credential, schedule, and retirement changes per FR-020, SC-003, Constitution X, and T028 (partial).
