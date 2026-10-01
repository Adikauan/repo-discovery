# Internal Scheduled Execution Dispatch Contract

## Purpose

Defines the application boundary between the scheduler adapter and MiningExecution creation. This is an internal contract, not a public HTTP API.

## Candidate occurrence

```text
ScheduledOccurrenceCandidate
- monitoring_configuration_id: UUID
- scheduled_occurrence: aware UTC datetime
- expected_schedule_version: positive integer
```

The candidate is calculated by the existing Feature 005 schedule calculator from persisted schedule data. The scheduler must not provide configuration scope, GitLab credentials, MiningExecution status, or repository results.

## Dispatch operation

```text
dispatch(candidate) -> DispatchOutcome
```

Possible outcomes:

- `started(execution_id)`: new scheduled MiningExecution committed, then its lifecycle and Feature 008 pipeline were invoked.
- `duplicate(execution_id?)`: the occurrence key already exists; do not create or start another execution.
- `ineligible`: configuration/schedule missing, disabled, retired, or schedule version no longer matches; do not create an execution.
- `conflict`: a non-stale MiningExecution already owns the configuration; scheduled occurrence is skipped and is not queued.
- `capacity_skipped`: all bounded scheduled worker slots are occupied; no MiningExecution is created and no work is queued.
- `failed(execution_id)`: occurrence was accepted and a normal MiningExecution was created, but shared lifecycle/pipeline ended in a safe failed status. The mining outcome remains readable through the ordinary execution APIs.

Application implementation may express these as typed result values or controlled domain errors, but scheduler must handle every outcome deterministically.

## Atomicity and side effects

1. Lock/re-read active Monitoring Configuration and persisted schedule.
2. Confirm eligible state, candidate schedule version, and occurrence due/identity.
3. Apply Feature 006 stale active reconciliation and active conflict semantics.
4. Capture one immutable `ExecutionSnapshotV1` with `trigger_type=scheduled` and `ScheduleTriggerContext(occurrence, schedule_version)`.
5. Insert MiningExecution and `scheduled_occurrence_at` atomically. Partial unique conflict maps to `duplicate`.
6. Commit before lifecycle/pipeline network work.
7. Use the same lifecycle service and `ProcessMiningExecution` used by manual initiation.

No external call or mining pipeline runs for `duplicate`, `ineligible`, or `conflict` outcomes. No scheduler retry occurs after a terminal MiningExecution outcome.

## Scan contract

- Startup reconciliation loads eligible persisted schedules; a serialized periodic scan recalculates due candidates from current persisted state. A calculated next occurrence becomes eligible when due. No per-occurrence timer object or persistence row/table is required.
- Scheduler process owns a monotonic process-local scan watermark.
- At startup set it to current UTC instant, excluding all prior occurrences.
- For each serialized tick, use `max(previous_watermark, current_schedule.updated_at)` as the strict-future reference and evaluate occurrences through `tick_instant` using Feature 005 calculation semantics. An edited schedule cannot catch up an occurrence earlier than its update time.
- Load current configuration/schedule state on each tick; do not dispatch a candidate based only on stale in-memory state.
- Sort due candidates by occurrence instant ascending, then Monitoring Configuration UUID ascending, before worker admission.
- Admit dispatch through a nonblocking process-local worker bound (`scheduled_execution_concurrency`, default 4, valid 1–8). If no slot is available, record a safe `capacity_skipped` outcome, create no MiningExecution, and do not enqueue the candidate.
- After a complete scan, advance watermark to the tick instant. A process restart creates a fresh startup watermark and never replays downtime.
- One runner is supported per deployment. FastAPI lifespan starts it only in the process configured with `SCHEDULER_ENABLED=true`; additional API worker processes use false. No distributed lease/leader-election contract is provided.
