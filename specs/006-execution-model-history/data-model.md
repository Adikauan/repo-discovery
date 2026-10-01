# Feature 006 Data Model: Execution Model and History

## MiningExecution

One durable execution owned by exactly one Monitoring Configuration. The aggregate controls identity, trigger/status invariants, counters, lifecycle timestamps, safe failure metadata, and immutable snapshot reference.

| Field | Type | Rules |
|---|---|---|
| `id` | UUID | Unique execution identifier. |
| `monitoring_configuration_id` | UUID | Required FK to the owner; physical deletion is restricted. Retirement does not remove the row. |
| `trigger_type` | enum | `manual` or `scheduled`; Feature 006 creation assigns `manual` server-side. |
| `status` | enum | `pending`, `running`, `completed`, `partially_completed`, `failed`. Final states are completed/partially_completed/failed. |
| `created_at` | UTC instant | Set once when created. |
| `started_at` | nullable UTC instant | Null until transition to running; then set exactly once. |
| `completed_at` | nullable UTC instant | Null until transition to a final state; then set exactly once. |
| `repository_count` | nonnegative integer | Defaults to zero; remains zero throughout Feature 006. |
| `successful_repository_count` | nonnegative integer | Defaults to zero; remains zero throughout Feature 006. |
| `failed_repository_count` | nonnegative integer | Defaults to zero; remains zero throughout Feature 006. |
| `finding_count` | nonnegative integer | Defaults to zero; remains zero throughout Feature 006. |
| `error_code` | nullable string, maximum 64 characters | Normalized application code only; set only for controlled failure. |
| `error_summary` | nullable text, maximum 500 characters | Safe user-facing summary only; no exception/provider output, stack trace, or secrets. |
| `snapshot` | validated JSONB `ExecutionSnapshotV1` | Immutable; schema version internal to persistence; not returned as raw storage JSON. |

PostgreSQL constraints enforce valid enum values, nonnegative counters, lifecycle timestamp shape where practical, a restrictive owner FK, and uniqueness of one `pending`/`running` execution per configuration. Indexes support global newest-first ordering, owner history, trigger/status filters, and active lookup. `duration` is derived from `started_at` and `completed_at`; it is not persisted.

## ExecutionSnapshotV1

Explicit immutable model serialized to JSONB. Version 1 captures:

- `schema_version = 1` (storage evolution marker; not required by the public DTO)
- configuration ID, display name, `enabled` state, normalized GitLab URL, and configuration revision when available
- scope version when available
- selected groups: stable GitLab group ID, safe name/full path, parent group ID when available, internal GitLab instance fingerprint
- selected repositories: stable project ID, safe name/full path, parent group ID when available, internal GitLab instance fingerprint
- trigger type and optional typed scheduled-occurrence/schedule-version context reserved for later use

The snapshot stores the selected intent, not expanded/effective repositories. Empty groups and repository arrays are valid. Manual requests do not read schedule data and carry no required schedule context. Snapshot construction does not access credential persistence; the schema has no credential fields. On read, the JSONB is parsed and validated as a known snapshot version before projection. Unknown versions fail through a normalized safe internal error path and do not expose the stored document.

The internal instance fingerprint is retained only to prevent historical scope identities from being conflated across GitLab instances. It is omitted from public response contracts and frontend models.

## Execution lifecycle

```text
pending ──> running ──> completed
   └──────────────────> failed
                    ├─> partially_completed
                    └─> failed
```

| Event | Status | Timestamp effect |
|---|---|---|
| Manual request accepted | `pending` | Set `created_at`; `started_at` and `completed_at` are null. Snapshot and zero counters are persisted. |
| Orchestration starts | `running` | Set `started_at` once. |
| Feature 006 orchestration succeeds | `completed` | Set `completed_at` once. All counters remain zero. |
| Controlled failure before start | `failed` | Allowed `pending → failed`; leave `started_at` null, set `completed_at` once, and store normalized safe error fields. |
| Controlled orchestration failure after start | `failed` | Allowed `running → failed`; preserve `started_at`, set `completed_at` once, and store normalized safe error fields. |
| Request-time reconciliation of stale pending | `failed` | Allowed `pending → failed`; leave `started_at` null, set `completed_at` to the reconciliation reference instant, and store only safe `execution_interrupted` metadata. |
| Request-time reconciliation of stale running | `failed` | Allowed `running → failed`; preserve `started_at`, set `completed_at` to the reconciliation reference instant, and store only safe `execution_interrupted` metadata. |
| Future repository processing outcome | `partially_completed`/`completed`/`failed` | Same lifecycle API; processing belongs to a later feature. |

No other transition is valid. A final state cannot transition again. Every lifecycle operation obtains a reference UTC instant and validates order/immutability; API serializers do not set timestamps. A failed execution is final/inactive and does not prevent a later manual execution.

Feature 006 creates no repository execution, repository discovery, clone, mining result, or finding rows. `completed` means only that the orchestration implemented in Feature 006 completed, not that repository mining occurred.

## Monitoring Configuration relationship and retention

```text
MonitoringConfiguration 1 ─── 0..* MiningExecution
MiningExecution         1 ─── 1    ExecutionSnapshotV1 (embedded immutable JSONB)
```

Feature 002 uses soft retirement. Retirement makes new manual requests ineligible but does not alter execution rows; historical list/detail reads remain possible. The execution FK is non-null and restrictive so a physical deletion cannot cascade away history or orphan the execution. Snapshot content does not depend on credential, schedule, scope-state, or selected-entity rows, so deleting/mutating those child values cannot rewrite historical context.

## Creation eligibility and concurrency

Manual creation requires an active, non-retired configuration and no non-stale `pending`/`running` execution after request-time reconciliation. Configuration `enabled` and schedule presence/enabled state are irrelevant to manual requests. Feature 009 may later apply automatic eligibility based on both independent enabled states; it is not implemented here.

The initial creation transaction uses repeatable-read isolation to capture configuration and scope from one consistent database view, locks the active Monitoring Configuration row using `FOR UPDATE NOWAIT`, and re-reads active executions after acquiring the lock. The configurable staleness threshold defaults to five minutes. Age is measured from `created_at` for `pending` and `started_at` for `running`; strictly exceeding the threshold marks an active execution stale. A non-stale execution produces the existing conflict. A stale execution is transitioned through lifecycle logic to `failed`, with `completed_at` set to the reference instant and safe `execution_interrupted` metadata; snapshot and counters remain unchanged. Lock and re-read the execution row and condition transitions on the expected current status: if normal completion wins first, reconciliation does not rewrite it; if reconciliation wins, the original completion attempt cannot overwrite the failed record. For a distinct new command, reconciliation and insertion of a replacement pending record commit atomically. The partial unique index plus owner-row lock ensures concurrent requests cannot create two active rows. Lifecycle mutations use row locks, expected-status conditional updates, transaction boundaries, and database-backed active uniqueness; no execution revision field is introduced. A same-key replay never creates another row; if its execution is stale, it is finalized and the replay returns that same failed record.

After that creation/reconciliation transaction commits, a second lifecycle operation transitions pending to running, then to completed or—on controlled failure—to failed. A controlled failure before start may transition pending directly to failed. Failed and completed executions are final, so a later request is allowed. No background reconciliation job or scheduler polling is introduced; reconciliation runs only when a manual request encounters stale active work.

## Error and counter invariants

All four counters are integer values with zero defaults and nonnegative checks. Feature 006 never changes them from zero. `error_code` is at most 64 characters and `error_summary` is at most 500 characters; only normalized safe codes and curated summaries may be persisted/displayed. Raw exception details are not stored in execution records or returned. Internal diagnostic logging follows existing safe logging policy.
