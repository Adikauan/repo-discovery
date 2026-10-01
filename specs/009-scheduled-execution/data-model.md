# Feature 009 Data Model

## Existing entities reused without duplication

### MonitoringConfiguration

Existing Feature 002 entity. `enabled=true` is required for automatic eligibility. A disabled or retired configuration is not dispatched. Existing manual execution eligibility remains unchanged.

### MonitoringSchedule

Existing Feature 005 one-to-zero-or-one schedule state. A configured schedule with `enabled=true` is required for automatic eligibility. `version` is captured by scheduled execution and checked again atomically at dispatch. Daily/weekly/monthly recurrence, local wall time, timezone, and DST semantics remain owned by Feature 005.

### MiningExecution

Existing Feature 006 execution record and sole history entity for manual and scheduled runs.

| Field | Existing/new | Rules |
|---|---|---|
| `id` | Existing | UUID identity. |
| `monitoring_configuration_id` | Existing | Parent configuration and active uniqueness partition. |
| `trigger_type` | Existing | `manual` or `scheduled`. |
| `status` and lifecycle timestamps | Existing | Feature 006 lifecycle is authoritative. |
| `snapshot` | Existing | Immutable `ExecutionSnapshotV1`, including config/scope data and safe schedule context for scheduled trigger. |
| `scheduled_occurrence_at` | New nullable database field | UTC-aware scheduled occurrence identity. Required for every new scheduled execution; null for manual rows. Included as an indexed column rather than relying on JSON expression uniqueness. |

### ScheduleTriggerContext

Existing embedded snapshot value, used for scheduled executions:

| Field | Type | Rules |
|---|---|---|
| `scheduled_occurrence` | UTC-aware datetime | Exact occurrence instant captured at acceptance. Must equal normalized `scheduled_occurrence_at`. |
| `schedule_version` | positive integer | Version of the persisted schedule that was eligible at the atomic dispatch check. |

Scheduled snapshot `trigger_type` and MiningExecution `trigger_type` must both be `scheduled`. Manual snapshots retain null schedule context and null occurrence key.

`ScheduleTriggerContext` is internal persisted snapshot data. It is not added to `SnapshotResponse` or another public DTO solely for Feature 009. No timer entity/table or per-occurrence timer object is part of this model; the runner periodically evaluates persisted schedule state.

## Identity, uniqueness, and relationships

```text
MonitoringConfiguration 1 ─── 0..1 MonitoringSchedule
MonitoringConfiguration 1 ─── 0..* MiningExecution
MiningExecution         1 ─── 1    ExecutionSnapshotV1 (embedded immutable JSON)
```

- Existing PostgreSQL partial unique index allows only one `pending` or `running` MiningExecution per configuration, regardless of trigger.
- New PostgreSQL partial unique index allows at most one scheduled MiningExecution for `(monitoring_configuration_id, scheduled_occurrence_at)` when trigger is `scheduled` and timestamp is non-null.
- Occurrence identity deliberately excludes schedule version so a schedule edit cannot create two execution records for one configuration/instant.
- There is no scheduled-run entity/table, scheduler cursor/state table, or per-occurrence timer table. Startup watermark is process-local and reconstructed on every startup; persisted schedules are re-evaluated periodically.
- Existing foreign-key restrictions/retention remain; no new cascade deletes.

## Eligibility and dispatch invariants

- Only non-retired configuration with `enabled=true`, existing configured schedule with `enabled=true`, current schedule version, and due occurrence is eligible.
- Scheduler scan proposes; the atomic shared creation use case re-reads and verifies the current configuration/schedule/version before capture.
- If schedule is disabled, removed, updated since candidate calculation, or configuration disabled, no MiningExecution is created for that stale candidate.
- A changed configured schedule version can produce a run only for an occurrence strictly after its persisted `updated_at`; edits never cause a past occurrence to be caught up.
- If a non-stale active execution exists, a scheduled candidate is skipped; it is not queued. A stale active execution is reconciled only using Feature 006 lifecycle behavior.
- Duplicate occurrence insertion is a safe no-op enforced by the partial unique index. It does not call the mining pipeline.
- After pending creation commits, normal lifecycle goes pending → running → the final Feature 008 outcome. A failure is not retried by the scheduler.

## Migration

One Alembic migration adds nullable timezone-aware `scheduled_occurrence_at` and its partial unique index. Existing rows are left null; migration must not rewrite snapshots or statuses. Forward uniqueness is validated against PostgreSQL. Downgrade removes the new index/column according to repository migration policy and must not be used as a production data-retention operation.
