# Feature 005 Schedule API Contract (v1)

Base path: `/api/v1`. All endpoints operate on an active, non-retired Monitoring Configuration. They never expose credentials and never create executions.

## Schedule representation

```json
{
  "recurrenceType": "weekly",
  "enabled": true,
  "executionTime": "09:30",
  "timezone": "America/Sao_Paulo",
  "dayOfWeek": 1,
  "dayOfMonth": null
}
```

- `recurrenceType` is exactly `daily`, `weekly`, or `monthly`.
- `executionTime` is local wall-clock time in 24-hour `HH:mm` format, minute precision.
- `timezone` is a supported IANA timezone identifier available through the backend's configured timezone database and returned by `GET /schedule-timezones`. The server preserves a valid submitted identifier exactly, including a runtime-recognized alias; it does not canonicalize or manually map aliases. An unsupported identifier is rejected with the standard validation error.
- `dayOfWeek` is ISO weekday numbering: Monday=1, Tuesday=2, Wednesday=3, Thursday=4, Friday=5, Saturday=6, Sunday=7. Required only for weekly.
- `dayOfMonth` is an integer 1–31, required only for monthly. For shorter months the configured day is clamped to the month's final day.
- Irrelevant recurrence fields MUST be null/omitted. A non-null irrelevant value is rejected with 422; it is not silently retained.
- `enabled` is the schedule's automatic-scheduling state, independent of Monitoring Configuration enabled state.

## Next occurrence representation

```json
{
  "instant": "2026-09-30T12:30:00Z",
  "timezone": "America/Sao_Paulo",
  "localDateTime": "2026-09-30T09:30:00"
}
```

The preview is calculated by the backend and is not persisted. It is strictly later than its reference instant. A disabled or absent schedule has `nextOccurrence: null`. DST gap times move forward by the size of the gap preserving their relative position; ambiguous times choose the earlier instant.

## GET schedule

`GET /api/v1/monitoring-configurations/{configurationId}/schedule`

Response `200 OK`, with `ETag` containing the quoted schedule version:

```json
{
  "schedule": null,
  "nextOccurrence": null
}
```

When configured, `schedule` is the representation above and `nextOccurrence` is calculated for the current UTC instant if enabled. An absent schedule has virtual ETag `"0"` until first mutation. A removed schedule returns `schedule: null` with its retained tombstone version ETag.

## Replace or create schedule

`PUT /api/v1/monitoring-configurations/{configurationId}/schedule`

Requires `If-Match: "{version}"`. PUT is a complete replacement; it does not partially merge fields. First creation uses `If-Match: "0"`. Example request is the Schedule representation above.

Success: `200 OK` with the persisted schedule, calculated `nextOccurrence` (null when disabled), and the new `ETag`, including on initial creation. PUT has one deterministic success status.

## Remove schedule

`DELETE /api/v1/monitoring-configurations/{configurationId}/schedule`

Requires current `If-Match`. Success: `204 No Content`. A state-changing removal increments the version and returns the new ETag; an already-absent schedule at its current version is an idempotent no-op and returns the current ETag unchanged. Removal deletes the configured recurrence only. It does not change the Monitoring Configuration, its enabled state, credential, or scope.

## Preview unsaved candidate

`POST /api/v1/monitoring-configurations/{configurationId}/schedule/preview`

Request:

```json
{
  "schedule": {
    "recurrenceType": "monthly",
    "enabled": true,
    "executionTime": "08:00",
    "timezone": "UTC",
    "dayOfWeek": null,
    "dayOfMonth": 31
  },
  "referenceInstant": "2026-04-01T00:00:00Z"
}
```

`referenceInstant` is optional; if absent, the application supplies its current UTC instant. Response `200 OK`:

```json
{ "nextOccurrence": { "instant": "2026-04-30T08:00:00Z", "timezone": "UTC", "localDateTime": "2026-04-30T08:00:00" } }
```

For a disabled candidate the response is `{ "nextOccurrence": null }`. Preview validates the complete candidate but creates/updates no schedule row and changes no configuration state.

## Timezone catalogue

`GET /api/v1/schedule-timezones`

Response `200 OK`:

```json
{ "timezones": ["America/Sao_Paulo", "Europe/London", "UTC"] }
```

The list is sorted identifiers available through the backend's configured supported IANA timezone database. It is not a guarantee that aliases are canonicalized. The frontend submits an identifier, not a browser-derived offset or display label; schedule reads return the accepted persisted identifier.

## Errors and concurrency

Errors use the project's RFC 9457 Problem Details contract with a deterministic, safe top-level `code` and safe `title`/`detail`; field errors may include safe field, code, and message values. The top-level code is determined by HTTP status:

| Status | Top-level code | Meaning |
|---|---|---:|
| 400 | `invalid_request` | Request is malformed or otherwise invalid. |
| 404 | `not_found` | Configuration is missing, retired, or inactive. |
| 409 | `conflict` | A state conflict applies where the project uses HTTP 409. |
| 412 | `stale_update` | `If-Match` does not match the current schedule version. |
| 422 | `validation_error` | Request fields fail validation. Safe field-level codes may distinguish `invalid_schedule` or `invalid_timezone`. |
| 500 | `unexpected_error` | Unexpected server failure; generic safe response only. |
| 428 | `invalid_precondition` | Required `If-Match` is absent (existing project convention). |
| 503 | `unexpected_error` | Required runtime timezone data/calculation service is unavailable (existing project convention). |

Scheduling-specific field-level validation codes such as `invalid_schedule` (recurrence/time fields) and `invalid_timezone` (unsupported identifier) are not top-level replacements for the HTTP 422 code `validation_error`. User-facing/API output MUST NOT expose raw exception text, stack traces, database details, timezone-library internals, provider/runtime response bodies, low-level parsing errors, or request-sensitive values. In particular, HTTP 500 responses MUST contain only generic safe title/detail and code `unexpected_error`. Diagnostics may retain only information permitted by project logging/redaction rules. Global status/code mapping belongs to the reusable application error handler, not scheduling-specific controller branches.

| Status | Meaning |
|---|---|
| 400 | Invalid request; code is `invalid_request`. |
| 404 | Monitoring Configuration does not exist or is retired/inactive; code is `not_found`. |
| 409 | Applicable state conflict; code is `conflict`. |
| 412 | `If-Match` version is stale; code is `stale_update`; no mutation occurred, the winning persisted schedule remains unchanged, and the client retains the rejected draft for review. |
| 422 | Invalid recurrence, time, timezone, weekday, month day, or irrelevant recurrence field; top-level code is `validation_error`, with safe field-level code such as `invalid_schedule` or `invalid_timezone`. Existing persisted schedule remains unchanged. |
| 428 | Required `If-Match` header is missing; code is `invalid_precondition`. |
| 500 | Unexpected application error; code is `unexpected_error` and title/detail are generic, without internal exception or request-sensitive information. |
| 503 | Required runtime timezone data/calculation service is unavailable; code is `unexpected_error`, with a safe generic message and no internal details. |

ETag versions are internal concurrency metadata and are not part of schedule DTOs or user-visible status. A current version is returned only as the HTTP ETag. Every successful state mutation increments the version once. Compare-and-swap is performed transactionally; no distributed locking is used.

## Non-goals

No endpoint in this contract evaluates execution eligibility, polls a schedule, creates a job or MiningExecution, or mines/clones repositories. A “next occurrence” is a calculation preview, not a promise that an execution will happen.
