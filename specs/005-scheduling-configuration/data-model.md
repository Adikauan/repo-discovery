# Feature 005 Data Model

## MonitoringSchedule

Represents optional recurrence intent for one active or soft-retired Monitoring Configuration. There is at most one configured schedule per configuration. A schedule is configuration data only; it is not an execution or job record.

| Field | Type / representation | Required when configured | Rules |
|---|---|---:|---|
| `monitoring_configuration_id` | UUID, primary/foreign key | Yes | References `monitoring_configurations.id`; one-to-zero-or-one association. Physical FK cascade follows existing schema behavior; public retirement remains soft. |
| `configured` | Boolean state discriminator | Yes | False means no schedule is configured. A retained false row is an internal version tombstone, not a user-visible schedule. |
| `version` | Positive integer | Yes | Monotonic schedule resource version used for ETag/If-Match; independent of Monitoring Configuration revision. Initial absent state is virtual version 0. |
| `recurrence_type` | Enum/string: `daily`, `weekly`, `monthly` | Yes | Null only when `configured=false`. |
| `enabled` | Boolean | Yes | Null only when `configured=false`; independent of `MonitoringConfiguration.enabled`. |
| `execution_time` | SQL `TIME` without timezone | Yes | Local wall-clock value at minute precision (`HH:mm`); never converted to a permanent UTC time. |
| `timezone` | IANA timezone identifier string | Yes | Must be in the backend-supported timezone catalogue and constructible by `ZoneInfo`; persist the selected identifier, not a display label or UTC offset. |
| `day_of_week` | Nullable small integer | Weekly only | ISO numbering Monday=1 through Sunday=7. Null for daily and monthly schedules. |
| `day_of_month` | Nullable small integer | Monthly only | Integer 1–31. Null for daily and weekly schedules. |
| `created_at` | UTC-aware timestamp | Yes when configured | Original creation time of the current configured schedule; cleared when schedule is removed. |
| `updated_at` | UTC-aware timestamp | Yes | Updated on schedule changes and tombstone/version changes. |

### Recurrence invariants

- `configured=false` requires all schedule payload fields (`recurrence_type`, `enabled`, `execution_time`, `timezone`, `day_of_week`, `day_of_month`, and `created_at`) to be null.
- Daily: `recurrence_type=daily`, `day_of_week=null`, `day_of_month=null`.
- Weekly: `recurrence_type=weekly`, `day_of_week` in 1–7, `day_of_month=null`.
- Monthly: `recurrence_type=monthly`, `day_of_month` in 1–31, `day_of_week=null`.
- The selected timezone must resolve to a supported IANA identifier. Unknown identifiers are field validation errors; missing timezone data in the runtime is a safe service/configuration failure, not a persisted invalid schedule.
- A schedule write is a complete replacement. Irrelevant recurrence values are cleared before persistence and rejected if a non-null stale value is submitted.
- The database migration adds structural checks for recurrence enum, configured-state nullability, weekday/month-day ranges, positive version, and one row per configuration. The domain/application validator remains authoritative for cross-field and timezone rules.

## Schedule existence and version state

- No schedule ever created: no schedule-state row exists; GET represents `{ "schedule": null }` with ETag `"0"`.
- Configured schedule: row has `configured=true`; GET returns schedule data and its version ETag.
- Removed schedule: schedule data is cleared and the row remains with `configured=false` and an incremented version. GET still returns `{ "schedule": null }`, but the ETag preserves the latest version so stale clients cannot write against a resurrected version.
- First save uses If-Match version 0 and atomically inserts configured version 1. Later successful mutations compare-and-swap the expected version and increment it exactly once. An unchanged replacement does not increment the version.
- Removing an absent schedule with the current ETag is an idempotent no-op; stale ETags still fail.

## NextOccurrencePreview

Transient value returned by calculation, not persisted.

| Field | Type / representation | Rules |
|---|---|---|
| `instant` | UTC-aware ISO 8601 instant | Strictly greater than the supplied reference instant. |
| `timezone` | IANA identifier | Identifies how the instant was interpreted and should be rendered. |
| `local_datetime` | Derived local date/time | Computed for display from `instant` and schedule timezone; never authoritative persisted input. |

A disabled or absent schedule has no next *eligible* occurrence and returns null for the preview. A preview never creates a `MiningExecution` and is never a guarantee of execution.

## Relationships and lifecycle

```text
MonitoringConfiguration 1 ─── 0..1 MonitoringSchedule state
                                  ├─ configured schedule fields, or
                                  └─ unconfigured version tombstone
```

Feature 002 retires configurations by setting `retired_at`; retirement preserves the configuration row and associated schedule data. Schedule GET/PUT/DELETE/preview require an active configuration and return the existing safe 404 outcome for retired or missing configurations. The schedule endpoint's DELETE removes only schedule configuration; it does not retire the Monitoring Configuration or alter its credential, GitLab scope, or enabled state.

## Future eligibility boundary

Feature 009 may define an execution as eligible only if all of the following hold:

1. `MonitoringConfiguration.enabled = true`;
2. a configured schedule exists; and
3. `MonitoringSchedule.enabled = true`.

Feature 005 does not implement this query, trigger, or any execution behavior.
