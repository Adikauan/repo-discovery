# Tasks: Feature 009 — Scheduled Execution

**Input**: Design documents from `specs/009-scheduled-execution/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/scheduler-dispatch.md`

**Organization**: Tasks follow the prioritized user stories in `spec.md`. Dependencies and physical order are aligned; tests explicitly requested by the specification are included.

## Format

Every task follows: `- [ ] Tnnn [P?] [USn?] Description with exact file path`.

## Phase 1: Setup

**Purpose**: Add validated scheduler settings and the process-role switch while preserving existing defaults and runtime conventions.

- [X] T001 [P] Add `SCHEDULER_ENABLED` (boolean, default true for local/single-process use), validated `schedule_poll_interval_seconds` (default 10, allowed 1–60), and `scheduled_execution_concurrency` (default 4, allowed 1–8) in `backend/app/config.py`; cover defaults, environment parsing, and bounds in `backend/tests/unit/test_config.py`.

---

## Phase 2: Foundational Execution Integration

**Purpose**: Persist occurrence identity and provide one shared execution-creation boundary before scheduler stories use it.

- [X] T002 [P] Add nullable UTC scheduled occurrence identity and scheduled/manual invariants to `backend/app/infrastructure/database/models.py` and `backend/app/domain/entities/mining_execution.py`; cover domain/mapping in `backend/tests/unit/domain/test_mining_execution.py`.
- [X] T003 Create the additive occurrence-key partial unique index migration in `backend/alembic/versions/<revision>_scheduled_execution_idempotency.py`; preserve all existing execution rows and indexes.
- [X] T004 Extend execution persistence for occurrence identity and add an eligible configuration/schedule scan query to the existing schedule/configuration repository ports and SQLAlchemy implementation in `backend/app/application/ports/mining_execution_repository.py`, `backend/app/application/ports/monitoring_schedule_repository.py`, and `backend/app/infrastructure/database/sqlalchemy_repositories.py`.
- [X] T005 Extract a trigger-aware shared creation use case in `backend/app/application/use_cases/create_mining_execution.py`; keep `CreateManualExecution` behavior/API-compatible and invoke the existing Feature 008 pipeline only after Feature 006 guard and lifecycle commit. Cover unchanged manual behavior and scheduled snapshot capture in `backend/tests/unit/application/test_create_mining_execution.py`.

**Checkpoint**: Shared creation persists coherent manual/scheduled snapshots and does not weaken the active execution guard.

---

## Phase 3: User Story 1 — Run Eligible Configurations on Schedule (Priority: P1)

**Goal**: Dispatch due occurrences through the shared MiningExecution lifecycle and the Feature 008 pipeline.

**Independent Test**: A controlled clock reaches one enabled schedule occurrence; exactly one scheduled MiningExecution is created with schedule context and the existing mining pipeline is invoked once.

### Tests for User Story 1

- [X] T006 [US1] Add deterministic daily, weekly, monthly, monthly-clamp, timezone, DST-gap, and DST-overlap dispatch cases proving due instants come from Feature 005 `ScheduleCalculator` in `backend/tests/unit/application/test_scheduled_execution_dispatch.py`.

### Implementation for User Story 1

- [X] T007 [US1] Implement `ScheduledExecutionDispatcher` in `backend/app/application/scheduling/scheduled_execution_dispatcher.py` to accept a calculated occurrence/version and dispatch through `CreateMiningExecution`; do not duplicate recurrence logic.
- [X] T008 [US1] Verify pipeline parity in `backend/tests/unit/application/test_scheduled_execution_dispatch.py`: scheduled runs invoke `ProcessMiningExecution` once and preserve normal completed, failed, and partially-completed outcomes, counters, repository rows, and safe errors.

---

## Phase 4: User Story 2 — Restore Schedules After Restart (Priority: P1)

**Goal**: Reconcile persisted schedules at startup and dispatch only future live occurrences without catch-up.

**Independent Test**: A new runner initialized after a downtime interval reloads eligible persisted schedules for periodic due-time evaluation, skips past occurrences, and does not resume an existing active MiningExecution. No per-occurrence timer object or persistence row is required.

### Tests for User Story 2

- [X] T009 [US2] Add fake-clock tests for startup baseline, offline missed-occurrence skip, next-future reconciliation, serialized scans, deterministic due ordering, full worker capacity skip without queueing, and an already-active scheduled execution in `backend/tests/unit/infrastructure/test_scheduler_runner.py`.

### Implementation for User Story 2

- [X] T010 [US2] Implement a serialized-scan infrastructure `SchedulerRunner` with a process-local startup watermark and nonblocking worker admission bounded by `scheduled_execution_concurrency` in `backend/app/infrastructure/scheduling/scheduler_runner.py`; reload persisted state per tick, skip occurrences at/before startup, and create no overflow queue.
- [X] T011 [US2] Wire scheduler start/stop to FastAPI lifespan in `backend/app/api/main.py` only when `SCHEDULER_ENABLED=true`; guarantee repeated lifespan initialization in one process reuses one runner, and test enabled process starts exactly one, disabled API worker starts none, and repeat initialization creates no duplicate in `backend/tests/api/test_scheduler_lifespan.py`. This flag designates the sole scheduler process operationally; do not add cross-process coordination. Wait for current dispatch when graceful shutdown permits and do not add recovery/retry.

---

## Phase 5: User Story 3 — Respect Schedule Changes and Eligibility (Priority: P1)

**Goal**: Ensure current persisted configuration/schedule state and version control dispatch.

**Independent Test**: Disable, update, or delete a schedule after a candidate is calculated but before dispatch; verify no stale candidate creates an execution.

### Tests for User Story 3

- [X] T012 [US3] Add deterministic disabled-configuration, disabled-schedule, schedule-version update, deletion, edit/dispatch serialization, and no-run-before-`updated_at` tests in `backend/tests/unit/application/test_scheduled_execution_dispatch.py`.

### Implementation for User Story 3

- [X] T013 [US3] Recheck configuration eligibility, configured/enabled schedule state, expected schedule version, and that the occurrence is strictly after schedule `updated_at` under shared configuration/schedule serialization before snapshot creation in `backend/app/application/use_cases/create_mining_execution.py`; stale candidates return an ineligible no-op and do not alter history.

---

## Phase 6: User Story 4 — Prevent Duplicate and Conflicting Execution (Priority: P1)

**Goal**: Preserve same-configuration concurrency and make occurrence dispatch idempotent across process restarts.

**Independent Test**: Race duplicate scheduled dispatches and a manual request against one due occurrence using PostgreSQL; verify one active execution and one pipeline entry maximum.

### Tests for User Story 4

- [X] T014 [US4] Add PostgreSQL integration tests for occurrence uniqueness, duplicate replay after terminal completion, manual/scheduled race, existing normalized manual conflict, only-winner pipeline entry, and stale reconciliation in `backend/tests/integration/test_scheduled_execution_concurrency.py`.

### Implementation for User Story 4

- [X] T015 [US4] Map scheduled occurrence unique conflicts to a safe duplicate/no-op result in `backend/app/application/use_cases/create_mining_execution.py` and `backend/app/infrastructure/database/sqlalchemy_repositories.py`; ensure duplicates and non-stale active conflicts never invoke mining.

---

## Phase 7: History Compatibility and Cross-Cutting Validation

**Purpose**: Verify scheduled MiningExecutions remain ordinary history/dashboard/repository results and preserve scope/security boundaries.

- [X] T016 [P] Add persistence/integration tests in `backend/tests/integration/test_scheduled_execution_snapshot.py` proving scheduled occurrence identity and required schedule revision/version are persisted internally in the immutable execution snapshot, remain unchanged after creation, and are not rewritten by later schedule edits; do not require public DTO exposure.
- [X] T017 [P] Add API tests in `backend/tests/api/test_scheduled_execution_history.py` verifying `trigger=scheduled`, lifecycle/result fields, failed/partial outcomes, and existing global/configuration history/dashboard behavior; assert credentials and internal occurrence keys, schedule context/version, idempotency keys, and runner metadata are not exposed through public DTOs.
- [X] T018 [P] Add frontend regression coverage that scheduled executions render through existing history/dashboard/repository result paths without a separate scheduled-run view in `src/test/features/executions/scheduled-execution-history.test.tsx`.
- [X] T019 Document `SCHEDULER_ENABLED` and the single-scheduler-process deployment mode in `README.md`, `.env.example`, and the backend environment mapping in `compose.yaml`: exactly one designated process true, all additional API workers false, local/single-process default true; state explicitly that this is operational configuration without distributed coordination. Verify safe scheduler logging/no credentials or provider details/no catch-up or retry/no extra pipeline, entity, or dependency against `specs/009-scheduled-execution/contracts/scheduler-dispatch.md` with focused tests in `backend/tests/unit/application/test_scheduled_execution_dispatch.py`.
- [ ] T020 Run migration upgrade and PostgreSQL idempotency/concurrency validation when `TEST_DATABASE_URL` is available; record unavailable PostgreSQL validation without marking it passed in `specs/009-scheduled-execution/quickstart.md`.

## Dependency Graph

```text
T001 ───────────────────────────────────────────────┐
T002 -> T003 -> T004 -> T005 -> T006 -> T007 -> T008
                                  └-> T009 -> T010 -> T011 -> T012 -> T013
T001 + T009 -> T010
T003 + T005 + T013 -> T014 -> T015 -> T016, T017, T018
T015 -> T019
T014 + T015 -> T020 (environment-dependent PostgreSQL validation)
```

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; T001 may run alongside T002 because they own separate settings and execution model files.
- **Foundational (Phase 2)**: T002–T005 establish persistence and shared execution creation before any scheduler story dispatches work.
- **US1 (Phase 3)**: Depends on setup/foundation, then implements scheduled dispatch and proves parity with the Feature 008 pipeline.
- **US2 (Phase 4)**: Depends on the US1 dispatcher (T007); T010 also requires the settings from T001, and T011 verifies the process-role lifespan gate.
- **US3 (Phase 5)**: Depends on the runner/lifespan from US2 because edits and eligibility are rechecked between periodic scans and dispatch.
- **US4 (Phase 6)**: Depends on shared creation and current-state serialization; PostgreSQL race tests gate conflict/idempotency mapping.
- **Cross-cutting (Phase 7)**: Starts after T015. Snapshot persistence, public API, and frontend compatibility tests use separate files; operational documentation is separate. T020 is conditional on PostgreSQL availability.

### User-Story Dependencies

- **US1** depends on foundational T001–T005, then establishes due dispatch and pipeline parity.
- **US2** depends on US1 dispatcher T007; startup restoration cannot dispatch until the occurrence adapter exists.
- **US3** depends on US1 dispatcher and US2 runner (T007/T010/T011) because it verifies invalidation of a candidate held between scans and dispatch.
- **US4** depends on the occurrence persistence and shared creation (T002–T005); PostgreSQL race validation precedes the duplicate-conflict mapping task.
- History compatibility checks depend on scheduled creation and outcome behavior (T005/T007/T013/T015).

Task-level prerequisites are: T003←T002; T004←T002/T003; T005←T004; T006←T005; T007←T005/T006; T008←T007; T009←T007; T010←T001/T009; T011←T010; T012←T010/T011; T013←T012; T014←T003/T005/T013; T015←T014; T016/T017/T018←T015; T019←T015; T020←T014/T015.

### Parallel Execution Examples

T001 and T002 may run in parallel: settings/config tests and execution model files are disjoint. Sequential task-ID execution remains valid.

US1, US2, US3, and US4 have no safe parallel implementation pair within their phase: each test/integration step gates a later change or shares a file with it. Their story order is T006–T008, T009–T011, T012–T013, and T014–T015 respectively.

After T015, T016, T017, and T018 may run in parallel because they touch separate persistence/integration, API, and frontend test files. T019 operational documentation may run independently after T015. T014 is PostgreSQL-dependent and may run only after T013 and the migration are ready; T020 performs the final environment-dependent validation.

Tasks T002–T005, T007, T010–T011, T013, and T015 have ordered shared-file ownership and must not be parallelized across their dependencies.

## Requirement-to-Task Traceability

| Requirements | Tasks |
|---|---|
| FR-001, FR-012, FR-013, FR-014 | T004, T012, T013 |
| FR-002 | T006, T007 (reuse Feature 005 calculator); existing Feature 005 recurrence tests remain authoritative |
| FR-003, FR-004 | T002–T008, T016, T017 |
| FR-005, FR-006 | T005, T008, T017, T018 |
| FR-007, FR-009, FR-015 | T005, T013–T015, T018 |
| FR-008 | T002–T004, T014–T015 |
| FR-010, FR-011 | T009–T011 |
| FR-016, FR-017, FR-018, FR-019, FR-020 | T001, T009–T011, T019–T020 |

## Implementation Strategy

1. **Persistence and shared boundary**: Add occurrence uniqueness and unify manual/scheduled MiningExecution creation while retaining Feature 006 behavior.
2. **MVP scheduled dispatch**: Implement due dispatch via the existing calculator and Feature 008 pipeline; prove standard final outcomes.
3. **Startup restoration and current-state checks**: Add one lifespan-managed loop with startup watermark and persisted version/eligibility rechecks.
4. **Race/idempotency validation**: Prove the existing active guard and occurrence uniqueness using PostgreSQL.
5. **History compatibility**: Verify existing history/dashboard/repository views require no separate scheduled execution concept.

All tests use deterministic clocks and mocked GitLab interactions. PostgreSQL-specific concurrency/migration tasks remain explicitly environment-dependent.
