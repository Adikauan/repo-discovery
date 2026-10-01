# Implementation Plan: Feature 009 — Scheduled Execution

**Branch**: `009-scheduled-execution` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification in `specs/009-scheduled-execution/spec.md`.

## Summary

Add a single-instance scheduler adapter that reads the current enabled Monitoring Configuration and Feature 005 schedule records, calculates due occurrences with the existing authoritative calculator, and dispatches eligible occurrences through a shared execution-creation/orchestration use case. Persist the scheduled occurrence identity on the existing Mining Execution so duplicate dispatch is prevented by PostgreSQL, while retaining Feature 006's active-execution guard across manual and scheduled triggers. Reuse the Feature 008 mining pipeline unchanged. No separate run entity, queue, scheduler library, or frontend execution surface is required.

## Technical Context

**Language/Version**: Python 3.13–3.14 (backend), TypeScript/React (existing frontend; no planned UI change)

**Primary Dependencies**: Existing FastAPI lifespan, SQLAlchemy, Alembic, PostgreSQL, Pydantic, Feature 005 schedule calculator, Feature 006 execution lifecycle/snapshot, Feature 008 ProcessMiningExecution; no new runtime dependency

**Storage**: Existing PostgreSQL MonitoringSchedule and MiningExecution tables; one additive scheduled-occurrence timestamp and partial unique index on MiningExecution; existing snapshot retains schedule version

**Testing**: pytest unit/application/API/PostgreSQL integration suites; deterministic clocks and scheduler tick harness; existing Vitest/Testing Library suites to assert scheduled history presentation remains compatible

**Target Platform**: Existing backend service; exactly one scheduler-enabled process per deployment, selected with `SCHEDULER_ENABLED`

**Project Type**: Full-stack web application; Feature 009 work is backend scheduling and execution integration, with no new frontend workflow

**Performance Goals**: Scheduler tick interval defaults to 10 seconds and is configurable within 1–60 seconds; a due occurrence is considered on the first tick after its due instant while the scheduler remains active. Whole scheduled MiningExecution processing is bounded to four workers by default (configurable 1–8) and has no overflow queue.

**Constraints**: Skip occurrences at or before process-start baseline; no catch-up after downtime; exactly one designated scheduler-enabled process per deployment; additional API workers set `SCHEDULER_ENABLED=false`; no distributed leader election/coordination/locking; poll current persisted state so edits/removals take effect; commit schedule eligibility and execution creation under the same configuration serialization used by manual execution; never hold a database transaction across mining/network processing; preserve safe errors, immutable snapshots, active concurrency and Feature 006 stale reconciliation; bound process-local scheduled worker slots and skip rather than queue when full.

**Scale/Scope**: One scheduler loop per deployment; one due occurrence per eligible schedule per scan interval; at most four active scheduled mining workers by default (configurable 1–8), no queued overflow; at most one active MiningExecution per Monitoring Configuration; idempotency across all lifecycle states by configuration and scheduled occurrence instant.

## Constitution Check

*Gate before Phase 0: PASS.*

| Principle | Assessment |
|---|---|
| I. Clean Architecture and Responsibility Boundaries | PASS — recurrence remains in the domain calculator; scheduler adapter invokes application use cases; persistence and FastAPI lifespan remain outer adapters. |
| II. Domain-Centered Business Rules | PASS — Feature 005 owns due-time calculation, Feature 006 owns creation/lifecycle/concurrency, Feature 008 owns mining. Scheduler does not reimplement these rules. |
| III. Explicit, Versionable Contracts | PASS — scheduled occurrence and schedule version are carried in the existing snapshot context; no new public endpoint or separate read contract. |
| IV. Abstracted External Integrations | PASS — repository mining keeps its existing GitLab adapter boundary. |
| V. Secure by Construction | PASS — scheduler carries no credential; the existing Feature 008 pipeline resolves/decrypts credentials within its current security boundary. |
| VI. Immutable and Reproducible Execution History | PASS — configuration/scope/schedule version and occurrence are captured in the MiningExecution; later edits do not rewrite history. |
| VII. One Controlled Mining Pipeline | PASS — manual and scheduled creation converge on one use case and one ProcessMiningExecution entry point; database guards protect active and duplicate occurrences. |
| VIII. Observable Execution Lifecycle | PASS — lifecycle/status/errors remain ordinary MiningExecution data; safe scheduler outcomes are logged with correlation identifiers only. |
| IX. Migration-Managed Persistence | PASS — occurrence-key column/index are delivered in Alembic migration and preserve existing records. |
| X. Risk-Based Automated Verification | PASS — deterministic recurrence, restart, deduplication, race, pipeline parity, PostgreSQL uniqueness and failure outcome tests are specified. |
| XI. Deliberate, Reusable User Experience | PASS — existing execution history/dashboard already render trigger and execution outcomes; no parallel scheduled UI is introduced. |
| XII. Incremental Simplicity and Justified Dependencies | PASS — use a small lifespan-managed polling loop and standard project infrastructure; add no scheduling package, queue, or distributed coordination. |

**Gate after design: PASS.** The only schema addition is the persisted idempotency key needed to make duplicate occurrence prevention durable. No other principle exception or complexity justification is needed.

## Phase 0 — Research Decisions

Decisions and inspected Feature 005–008 contracts are recorded in [research.md](research.md). Key decisions:

- Reuse `MonitoringScheduleRepository`, `ScheduleCalculator`, and current config/schedule enablement; do not build a second recurrence implementation.
- Refactor creation entry points behind one application use case accepting trigger context. Manual behavior and API conflict semantics remain unchanged.
- For scheduled creation, atomically lock/re-read the active configuration, schedule/version, scope, and active execution; capture snapshot and insert the MiningExecution in that transaction. Reuse stale reconciliation from Feature 006.
- Store nullable `scheduled_occurrence_at` on MiningExecution for new scheduled rows and enforce a partial unique constraint on `(monitoring_configuration_id, scheduled_occurrence_at)` for scheduled rows. The snapshot remains authoritative for schedule version and full historical context. A duplicate unique-key attempt returns a no-op; it never starts a second pipeline.
- A due occurrence that encounters a non-stale active execution is skipped without an execution row; only the existing winner enters the pipeline. If a manual request wins, the scheduled trigger is skipped. If a scheduled request wins, the manual request receives the current normalized conflict.
- On startup, reconciliation loads current persisted eligible schedules and establishes `scan_watermark = startup instant`. The runner periodically evaluates persisted schedule state; each serialized scan uses `max(previous watermark, schedule.updated_at)` as the strict-future reference and considers an occurrence eligible when its due instant is at or before the current scan instant. No per-occurrence in-memory timer object or persisted timer row is required. No occurrence timer table is introduced. Thus no occurrence before startup or before the active schedule version's update is replayed. Each scan re-reads persisted enabled flags/version, so stale candidates are invalidated by updates or deletions.
- A dispatch transaction that obtains the configuration serialization first captures a coherent current schedule version. A schedule mutation that commits first is seen by the next scan and invalidates any prior candidate. If dispatch wins first, the already-created snapshot remains historical truth.
- Use FastAPI lifespan to start and stop the polling task only when `SCHEDULER_ENABLED=true`. Default this flag to true for local/single-process development. Exactly one application process per deployment may have it enabled; every additional API worker must set it false. Repeated lifespan initialization in one process must not create duplicate runner instances. This is an operational deployment constraint; do not implement distributed coordination, leader election, or cross-process locking. Do not await the long mining pipeline inline with a scan. Track admitted workers and join them on graceful shutdown where possible. Do not create one task per schedule or overlap scans. Database uniqueness and the active-execution index remain defensive and do not provide distributed scheduling.
- Each admitted worker dispatches synchronously into the existing Feature 008 orchestration. It never retries a failed occurrence. If process interruption leaves a MiningExecution active, do not restart it; Feature 006 stale reconciliation governs later handling.
- No public scheduler endpoint, scheduler-specific execution read model, frontend feature, scheduler library, queue, or additional UI is required.

## Architecture and Data Flow

```text
FastAPI lifespan
  -> single SchedulerRunner (serialized scans; startup baseline)
     -> list enabled configurations + configured schedules
     -> Feature 005 ScheduleCalculator (candidate due in scan interval)
     -> nonblocking bounded scheduled-worker admission (default 4; no queue)
        -> ScheduledExecutionDispatcher
        -> shared CreateMiningExecution use case
           -> lock/recheck config + schedule/version + active execution
           -> capture Feature 006 scheduled snapshot/context
           -> persist MiningExecution with occurrence idempotency key
           -> pending -> running via Feature 006 lifecycle
           -> Feature 008 ProcessMiningExecution (same as manual)
           -> existing aggregate final status
```

Scheduler responsibilities are limited to startup reconciliation, polling and dispatch intent. It does not compute recurrence itself, resolve GitLab credentials, mine repositories, update counters, or own execution status transitions.

### Scheduled worker isolation and capacity

- The scan loop must not run the long MiningExecution pipeline inline. It submits each due candidate to a process-local bounded worker pool so other configurations remain scannable while repository mining runs.
- Sort due candidates by `(scheduled_occurrence_at ASC, monitoring_configuration_id ASC)` before worker admission so simultaneous schedules have deterministic slot priority.
- Worker admission is nonblocking and has no pending-work queue. If all `scheduled_execution_concurrency` slots are occupied at the due scan, log the safe skipped outcome and advance the scan watermark; do not create a MiningExecution for that occurrence.
- `scheduled_execution_concurrency` defaults to 4 and accepts integers 1–8. It limits whole scheduled execution pipelines, distinct from Feature 008's per-execution repository concurrency.
- Once admitted, the worker invokes the same shared `CreateMiningExecution` and Feature 008 pipeline. Same-configuration execution uniqueness still applies across scheduled workers and manual API requests.
- Track and join admitted worker futures on graceful lifespan shutdown. Hard termination leaves durable last lifecycle state; restart never restarts an active scheduled MiningExecution.

### Schedule and execution race handling

- Schedule edits use Feature 005's existing configuration/schedule version behavior. Scheduled creation serializes on the same Monitoring Configuration owner record used by manual execution, then reloads the enabled state and schedule version before snapshotting.
- The persisted occurrence identity is UTC and represents the calculated instant, independent of local timezone string. `schedule_version` remains in the immutable snapshot context.
- A duplicate occurrence is recognized by the unique key even after its prior execution is completed or failed. The duplicate returns a safe no-op and never calls the mining pipeline.
- Active-execution conflict and stale reconciliation are performed through the same lifecycle/service rules as a manual request. A non-stale winner remains unchanged; an occurrence that loses is skipped.
- Polling reads persisted schedules each tick rather than holding a separate mutable in-memory copy. Disabled/deleted/replaced rows therefore stop old candidates from dispatching.

### Startup, outage, and shutdown

- Start the scheduler only after application services/configuration are available; initialize the watermark from the injected clock at startup.
- Reconciliation loads enabled configurations with configured, enabled schedules. Periodic evaluation derives the next occurrence strictly after `max(startup watermark, schedule.updated_at)` and considers it due when reached. “Reconcile/load” does not mean persisting one timer per occurrence; no timer table or per-occurrence timer object is needed.
- The recurring scanner uses a 10-second default interval with a validated 1–60 second operational setting. It calculates only occurrences strictly after the later of the previous successful scan and current schedule `updated_at`, through the current scan time. This catches ordinary loop delay without replaying downtime or a pre-edit occurrence.
- Serialize scans but allow admitted processing workers to run independently within the configured bound. This keeps due-time conflict checks responsive during long mining. On restart, a due occurrence that passed while the process was unavailable is skipped by the new startup watermark. Persisted active executions are not invoked a second time.
- Shutdown stops new scans and waits for admitted workers to return when the application server allows graceful shutdown. Hard termination leaves last persisted lifecycle state intact and relies on Feature 006 stale reconciliation.

## Persistence and Migration

Extend existing `mining_executions`:

- `scheduled_occurrence_at TIMESTAMPTZ NULL`: UTC identity for the scheduled occurrence; null for manual execution.
- Partial unique index on `(monitoring_configuration_id, scheduled_occurrence_at)` with predicate `trigger_type = 'scheduled' AND scheduled_occurrence_at IS NOT NULL`.
- Check/consistency rule at the application/domain boundary: new scheduled executions require schedule context and matching occurrence identity; manual executions do not set the occurrence column or schedule context.
- Existing JSON snapshot internally stores `schedule_context.scheduled_occurrence` and `schedule_context.schedule_version`; persist enough context for historical identity/version and immutability, without duplicating full recurrence fields in a new table. This internal field is not a public DTO requirement.
- Migration backfills no occurrence identity. Existing rows remain queryable; uniqueness applies only to new scheduled records with a key.
- Preserve `uq_execution_active_configuration`, restrictive history retention, counters, and existing indexes. No delete cascade or scheduler state table is introduced.

## API and Frontend Contract

- No new public REST endpoint. The scheduler is an application entry point, not a client-triggered API.
- Do not extend `SnapshotResponse` or other public execution DTOs solely to expose internal `schedule_context`, occurrence identity, schedule version, idempotency keys, or runner metadata. Existing DTOs remain authoritative for trigger, lifecycle, counters/results, and safe historical execution data. API tests verify those fields and ordinary history/dashboard behavior, and separately verify that sensitive/internal scheduler metadata is absent.
- The existing manual execution endpoint retains its request idempotency key and conflict response. Scheduled occurrence idempotency is separate and persisted on MiningExecution.
- Existing execution list/dashboard/repository APIs remain authoritative. Confirm `trigger=scheduled` is displayed/serializable and scheduled executions appear without frontend route changes. Add only contract-compatible tests if no code change is needed.

## Testing Strategy

- Domain: rely on existing `ScheduleCalculator` test suite for daily/weekly/monthly, monthly day clamp, IANA timezone, DST gap and overlap; add a focused cross-feature test showing dispatcher uses returned UTC occurrence and does not duplicate recurrence logic.
- Application: shared create use case creates `trigger=scheduled` with immutable configuration/scope snapshot, occurrence/version context and real Feature 008 pipeline; disabled config/schedule checks; duplicate no-op; conflict winner semantics; schedule-version changes; normal failed and partially-completed engine outcomes.
- Scheduler adapter: deterministic fake clock/tick source; startup baseline excludes offline occurrences; startup reconciliation reloads persisted schedules for periodic evaluation; no per-occurrence timer table/object; scans are serialized; disabled/deleted/update rows are re-read; restart of already active scheduled run does not invoke pipeline again.
- Persistence/integration: verify occurrence identity is persisted internally in the execution snapshot, schedule revision/version is captured where required by the approved model, the snapshot context remains immutable after creation, and later schedule edits do not rewrite it.
- API/history: separately verify manual contract unchanged, `trigger=scheduled`, lifecycle/result fields and existing global/configuration history/dashboard behavior; assert no credential or internal scheduler/idempotency metadata is exposed. Do not expose `schedule_context` via `SnapshotResponse` solely for Feature 009.
- Lifespan/configuration: verify enabled app process starts exactly one runner, disabled API worker starts none, and repeated lifespan initialization in a process does not create duplicate runner instances. `SCHEDULER_ENABLED=true` is the single-process local default; deployment designates exactly one enabled process.
- PostgreSQL integration: migration upgrade/downgrade as supported by project policy, unique occurrence constraint under concurrent duplicate inserts, and race between manual/scheduled creation proving only one active row and only the winner starts processing. Tests require PostgreSQL; do not claim a pass without it.
- Frontend: existing rendering contract for scheduled trigger and standard dashboard/history/repository result display; no new scheduled UI or browser scheduler.
- No live GitLab access is required; existing Feature 008 tests mock provider interactions.

## Project Structure

### Documentation (this feature)

```text
specs/009-scheduled-execution/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── scheduler-dispatch.md
├── checklists/
│   ├── requirements.md
│   └── scheduled-execution.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/app/
├── api/
│   └── main.py                         # FastAPI lifespan start/stop wiring gated by SCHEDULER_ENABLED
├── application/
│   ├── ports/
│   │   └── monitoring_schedule_repository.py  # extend existing eligible schedule query
│   ├── scheduling/
│   │   └── scheduled_execution_dispatcher.py  # due occurrence to shared use case
│   └── use_cases/
│       ├── create_mining_execution.py  # shared manual/scheduled creation and pipeline entry
│       └── create_manual_execution.py  # compatibility adapter/delegation if retained
├── domain/
│   └── entities/
│       └── mining_execution.py         # scheduled occurrence invariants only if needed
├── infrastructure/
│   ├── scheduling/
│   │   └── scheduler_runner.py         # polling, watermark and bounded workers
│   └── database/
│       ├── models.py                   # occurrence identity column/index
│       └── sqlalchemy_repositories.py  # eligible schedule scan + insert/dedup
└── config.py                           # SCHEDULER_ENABLED (default true) and scheduler settings
backend/alembic/versions/
└── <revision>_scheduled_execution_idempotency.py
backend/tests/
├── unit/domain/                         # only additions needed beyond Feature 005 recurrence tests
├── unit/application/                    # shared creation and scheduled dispatch
├── unit/infrastructure/                 # repository mapping/unique conflict normalization
├── integration/                         # PostgreSQL idempotency and same-config race
└── api/                                 # existing history/detail contract compatibility
src/test/features/executions/
└── scheduled-execution-history.test.tsx # only if current trigger rendering lacks coverage
```

**Structure Decision**: Follow existing `backend/app/{domain,application,infrastructure,api}` Clean Architecture. The application owns the scheduled occurrence dispatcher; infrastructure owns polling, process-local worker management, and FastAPI lifespan wiring. `SCHEDULER_ENABLED` selects the one designated process operationally; it is not a distributed lock. Extend the current execution use case/repositories, add no queue or scheduler framework, and leave frontend routes unchanged.

## Dependency and Retry Decision

Do not introduce APScheduler, Celery, Redis, a database job queue, or a second scheduler framework. A small lifespan-managed serialized scanner is sufficient for the explicitly single-instance scope and avoids new operational dependencies. No automatic retry is added: transport/mining failures finalize through Feature 008; a later recurrence is independent. Duplicate insert races are handled through the database unique key, not a retry loop.

## Complexity Tracking

No constitution violations. The occurrence-key migration is required by FR-008 and Principle VII; an in-memory-only dedupe was rejected because it would fail after restart and concurrent duplicate delivery.

