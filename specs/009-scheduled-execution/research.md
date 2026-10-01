# Feature 009 Research Decisions

## Decision: Reuse the existing recurrence and schedule persistence

- **Decision**: Enumerate enabled schedules from Feature 005 persistence and call the existing domain `ScheduleCalculator` with a controlled UTC reference instant. Do not add a scheduler-specific recurrence calculator or modify recurrence semantics.
- **Rationale**: Feature 005 already defines daily/weekly/monthly rules, strict-future calculation, IANA timezone handling, monthly day clamping, and DST gap/overlap behavior.
- **Alternatives considered**: Reimplementing due-time math in a scheduler package was rejected because it would duplicate business rules and could diverge from previews.

## Decision: One lifespan-managed polling loop, no new scheduler dependency

- **Decision**: Start one serialized scheduler runner from FastAPI lifespan only when `SCHEDULER_ENABLED=true`. Default the flag to true for local/single-process development; exactly one designated process per deployment may be enabled and additional API workers must be disabled. Use a 10-second default scan interval configurable from 1 to 60 seconds and re-read persisted state on every periodic scan. Startup reconciliation loads persisted eligible schedules; no per-occurrence timer object or timer persistence is required. This is an operational single-process constraint, not distributed coordination.
- **Rationale**: The scope explicitly excludes distributed scheduling and multiple scheduler instances. A small bounded loop provides restart restoration without adding a package, broker, worker fleet, or database job framework.
- **Alternatives considered**: APScheduler, Celery/Redis, and PostgreSQL advisory-lock based multi-instance coordination were rejected as unnecessary scope/operational complexity.

## Decision: Bound scheduled pipeline workers without a backlog

- **Decision**: Keep the schedule scan responsive while mining is running by submitting due candidates to a nonblocking bounded process-local worker pool. `scheduled_execution_concurrency` defaults to 4 and is configurable from 1 to 8. If all slots are occupied at the scan, skip that occurrence without creating an execution or queueing it.
- **Rationale**: Running the full synchronous mining pipeline inside the poll loop would delay checks for other due schedules and could turn a conflict at the scheduled instant into an unintended late run. An unbounded task/thread per schedule is unsafe; a backlog would create delayed executions contrary to the no-catch-up/conflict rules.
- **Alternatives considered**: Inline synchronous processing, unbounded background tasks, and unbounded executor submission queues were rejected. The limit applies to whole scheduled MiningExecutions and remains distinct from Feature 008 repository-level concurrency.

## Decision: Skip offline occurrences; do not catch up

- **Decision**: Set a startup scan watermark to the current instant; only process schedule occurrences in subsequent live scan intervals. Occurrences at or before startup are skipped. A normal running loop catches an occurrence on its first scan after due time; a scan pause follows the same no-backfill policy for time already before the new baseline after restart.
- **Rationale**: This avoids unexpectedly starting a backlog of repository mining after downtime and yields deterministic restart behavior.
- **Alternatives considered**: Running every missed occurrence, running only the most recent miss, or introducing a configurable catch-up grace period were rejected as business policy not required by the user and harder to reason about.

## Decision: Share execution creation, lifecycle, and mining orchestration

- **Decision**: Generalize the Feature 006 manual creation use case into one trigger-aware application use case (or a shared core with a compatibility manual adapter). It captures the same configuration/scope snapshot, acquires the existing configuration execution lock, reconciles stale active work via Feature 006, persists pending/running lifecycle, and invokes the existing Feature 008 pipeline. Scheduled initiation adds trigger and `ScheduleTriggerContext` only.
- **Rationale**: This preserves identical validation, concurrency, snapshot security, and mining outcomes across entry points.
- **Alternatives considered**: A second scheduled creation/pipeline service or endpoint was rejected because it duplicates lifecycle behavior and violates the single-pipeline rule.

## Decision: Persist an occurrence identity with database uniqueness

- **Decision**: Add nullable UTC `scheduled_occurrence_at` to MiningExecution. New scheduled creations require this value and a positive schedule version in the snapshot context. Create a partial unique index over `(monitoring_configuration_id, scheduled_occurrence_at)` for scheduled non-null rows. Manual rows remain null. Catch the known unique conflict as a safe no-op.
- **Rationale**: In-memory deduplication is lost on restart and cannot guard concurrent duplicate dispatch. A unique occurrence identity prevents duplicate history even if an execution has already reached a terminal state.
- **Alternatives considered**: Unique `(configuration, schedule version, occurrence)` was rejected because it could admit two records for one instant after schedule edits. A separate schedule-run table was rejected because MiningExecution is the sole execution entity.

## Decision: Reuse the Feature 006 active-configuration guard

- **Decision**: Scheduled and manual creation acquire the same active Monitoring Configuration serialization/lock and check active rows under that lock. A non-stale active row wins and scheduled dispatch is skipped with no execution row. Stale rows are reconciled with existing lifecycle behavior before attempting scheduled creation. Database uniqueness remains the final guard.
- **Rationale**: This guarantees one active execution per configuration and only lets the winning creator invoke Feature 008.
- **Alternatives considered**: Scheduler-local mutexes or a second concurrency control were rejected because they cannot coordinate with manual API requests.

## Decision: Recheck current persisted schedule before snapshot/dispatch

- **Decision**: The scheduler loads only enabled configuration/schedule rows and passes expected schedule version into dispatch. It calculates the first candidate strictly after `max(previous scan watermark, schedule.updated_at)`. The shared creation use case locks/re-reads configuration and schedule and confirms enabled state/version before capturing snapshot. If disabled, removed, or changed, the stale candidate is a no-op. A dispatch that serialized before a later edit keeps its coherent old schedule snapshot.
- **Rationale**: Current schedule state controls future eligibility; immutable snapshots preserve historical execution truth.
- **Alternatives considered**: Trusting a timer built once at startup was rejected because edits/deletion would leave stale work scheduled.

## Decision: No automatic restart/retry of interrupted/failed runs

- **Decision**: Startup reconciliation restores future schedules only. It does not re-invoke an active scheduled MiningExecution or retry terminal failed/partially completed executions. Feature 006 stale reconciliation remains authoritative.
- **Rationale**: Replays can duplicate repository work. The request explicitly excludes adding a separate recovery model or retry policy.
- **Alternatives considered**: Automatic restart of active work, retry of failed occurrence, and queue redelivery were rejected as future recovery semantics.

## Decision: No new public endpoint or frontend model

- **Decision**: Keep the scheduler as an internal application entry point. Reuse current history, execution dashboard, and repository result APIs. Add a frontend regression test only if a current UI contract lacks coverage of the already-defined `scheduled` trigger.
- **Rationale**: Feature 006 already established the scheduled trigger and snapshot context; Feature 007/008 already present executions and repository outcomes.
- **Alternatives considered**: Scheduler administration endpoints and scheduled-run dashboard pages were rejected because the spec asks for normal execution history and no distinct run entity.

## Project inspection evidence

- Feature 005 owns `MonitoringSchedule`, schedule versioning, preview, and `ScheduleCalculator`; its plan explicitly deferred scheduler work to Feature 009.
- Feature 006 defines `TriggerType` values `manual`/`scheduled`, `ScheduleTriggerContext` (`scheduled_occurrence`, `schedule_version`), immutable `ExecutionSnapshotV1`, active unique index `uq_execution_active_configuration`, configuration-owner locking, request-time stale reconciliation, and manual creation use case.
- Feature 008 provides `ProcessMiningExecution` as the real application-owned repository pipeline; it handles safe credentials, repository execution, counters, and aggregate status.
- Current app composition is `backend/app/api/main.py`; modules follow `backend/app/{domain,application,infrastructure,api}`. PostgreSQL DDL resides in Alembic migrations.
- Existing execution API/history use trigger filtering and normal MiningExecution reads; the UI does not require a separate scheduled entity.
