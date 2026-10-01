# Feature 006 Execution API Contract (v1)

Base path: `/api/v1`. JSON timestamps are RFC 3339 UTC instants. UUIDs are lowercase hyphenated UUID strings. DTOs are explicit projections; raw JSONB snapshot and persistence metadata are never returned.

## Enums

- `triggerType`: `manual` | `scheduled`
- `status`: `pending` | `running` | `completed` | `partially_completed` | `failed`
- Final statuses: `completed`, `partially_completed`, `failed`.

Frontend transport types use these exact wire values. Any conversion to an existing visual badge token is presentation-only and must not change stored/request status vocabulary.

Feature 006's public creation endpoint creates manual executions only. Scheduled trigger is reserved for future scheduler integration and cannot be selected by this endpoint.

## Safe snapshot projection

The public snapshot projection contains only:

```json
{
  "configurationId": "fca9d0e1-0846-4f6b-80b0-cd16c6f724b7",
  "configurationName": "Example configuration",
  "configurationEnabled": false,
  "gitlabUrl": "https://gitlab.example.com",
  "configurationRevision": 4,
  "scope": {
    "groups": [{ "gitlabGroupId": 91, "name": "Platform", "fullPath": "platform" }],
    "repositories": [{ "gitlabProjectId": 712, "name": "Service", "fullPath": "platform/service" }]
  }
}
```

Revision may be null when unavailable. Scope arrays may be empty. This is persisted selection intent: group entries remain group rules and are not expanded. The projection may include only safe display metadata. It never contains credential values, encrypted credential, credential revision, scope instance fingerprint, raw provider payload, raw snapshot JSON, or snapshot schema version. Detail values are historical and do not change if current configuration/scope changes.

## Execution DTOs

List item:

```json
{
  "id": "031383cf-5975-4c8d-99a1-d28062a654d2",
  "monitoringConfigurationId": "fca9d0e1-0846-4f6b-80b0-cd16c6f724b7",
  "configurationName": "Example configuration",
  "triggerType": "manual",
  "status": "completed",
  "createdAt": "2026-09-29T13:00:00Z",
  "startedAt": "2026-09-29T13:00:00Z",
  "completedAt": "2026-09-29T13:00:01Z",
  "durationSeconds": 1
}
```

Detail extends the list item with `snapshot` (safe projection), `counters`, and nullable safe `error`:

```json
{
  "counters": {
    "repositoryCount": 0,
    "successfulRepositoryCount": 0,
    "failedRepositoryCount": 0,
    "findingCount": 0
  },
  "error": null,
  "completionMeaning": "Feature 006 orchestration completed; repository mining was not performed."
}
```

`durationSeconds` is null unless both lifecycle instants exist. Detail may contain a curated `error` object with a bounded normalized code and safe summary; it must not expose raw exception text or provider/database information. The detail DTO types `completionMeaning` as `string | null`; it applies only when `status=completed` and is `null` for `pending`, `running`, `partially_completed`, and `failed` (or omitted only if the project's serialization convention omits null fields consistently). For Feature 006 completed executions, use the controlled value/message shown above so completion cannot be interpreted as repository processing.

## Create manual execution

`POST /api/v1/monitoring-configurations/{configurationId}/executions`

No request body. Optional `Idempotency-Key` header follows the existing project convention. The endpoint assigns `triggerType=manual`; clients cannot specify trigger, status, timestamps, counters, or snapshot.

Eligibility: configuration exists and is not retired. Before returning the active-execution conflict, the application checks any `pending`/`running` execution against the configurable staleness threshold (default 300 seconds). Age is measured from `createdAt` for `pending` and `startedAt` for `running`; it is stale only when elapsed time is strictly greater than the threshold. A non-stale active execution produces the existing safe `409 conflict`; a stale one is reconciled to `failed` with `completedAt`, safe `execution_interrupted` metadata, unchanged snapshot/counters, and no fabricated data. For a distinct request, stale reconciliation and creation of the replacement execution are atomic. `MonitoringConfiguration.enabled`, schedule existence, and `Schedule.enabled` do not restrict explicit manual execution. This endpoint does not read credentials, contact GitLab, discover scope entities, clone repositories, or mine.

Processing sequence is pending + snapshot persisted and committed, then application lifecycle transition to running and the local orchestration, followed by a persisted final state. On success the response is `201 Created` with the current execution detail representation, status `completed`; domain/application tests verify the internal `pending → running → completed` sequence. On controlled orchestration failure after creation, the lifecycle persists `failed` with safe error data and the create endpoint still returns `201 Created` for the successfully created resource, now in its current `failed` state. A controlled failure before running uses `pending → failed` and leaves `startedAt` null. Feature 006 completion means orchestration-only work finished; all four counters are zero and no repository/mining/finding records exist. `Location: /api/v1/executions/{id}` identifies the created resource.

An idempotency replay with the same key/operation never creates another record. If the original is pending/running and non-stale, return safe `409 conflict` with an in-progress reason rather than returning an unfinished success response. If that same-key execution is stale, reconcile it and return that same failed resource; do not create a duplicate. A distinct new command/key may reconcile stale active work and create a replacement in the same transaction. Once an execution is final, replay returns its current resource representation. A key reused with another fingerprint is rejected using the existing safe idempotency conflict. Distinct overlapping requests are independently protected by row locks, expected-status transitions, and active-execution uniqueness. A later request after completed or failed is a new intentional execution.

Responses:

- `201`: execution created and orchestration finalized; normally `completed`, or `failed` when controlled orchestration failure was safely persisted.
- `404 not_found`: configuration absent or retired.
- `409 conflict`: an execution is pending/running and not stale, or an idempotency key conflicts. The safe domain reason may be `execution_already_active`; no database details are exposed.
- `500 unexpected_error`: generic safe response only.

## Global listing

`GET /api/v1/executions`

Query parameters:

- `page`: 1-based, default `1`.
- `pageSize`: default `25`, allowed `1..100`.
- `status`: optional supported status.
- `triggerType`: optional `manual` or `scheduled`.
- `monitoringConfigurationId`: optional UUID.

Response `200`:

```json
{
  "items": [],
  "page": 1,
  "pageSize": 25,
  "totalItems": 0,
  "totalPages": 0
}
```

Ordering is always `createdAt DESC`, then UUID `id DESC` as a stable tie-breaker. Filters are applied by the backend before pagination.

## Configuration history

`GET /api/v1/monitoring-configurations/{configurationId}/executions`

Accepts `page`, `pageSize`, `status`, and `triggerType` with the same rules. It returns only that configuration's history in the same deterministic order. Existing retired configurations remain readable; a missing configuration returns `404 not_found`. Creation remains disallowed for retired configurations.

## Execution detail

`GET /api/v1/executions/{executionId}`

Returns `200` with the detail DTO or `404 not_found`. It reads snapshot values, not mutable configuration/scope joins, for historical display.

## Lifecycle and error contracts

No public endpoint accepts status mutation. Internal/application lifecycle operations allow `pending → running`, `pending → failed` for a controlled pre-start failure or stale reconciliation, and `running → completed | partially_completed | failed`; lifecycle timestamps are assigned once by that service. Each persisted mutation uses a row lock/transaction and a conditional update requiring the expected current source status (for example, `pending → running` requires persisted `pending`; `running → completed/failed` requires persisted `running`). Request-time stale reconciliation locks and re-reads the active record, verifies it remains pending/running and stale, then conditionally transitions it to `failed`, setting `completedAt` once and preserving `startedAt` semantics. It uses safe `error_code=execution_interrupted` and a curated summary that the previous execution did not complete. Snapshot and mining counters are unchanged. No execution revision field is required. Invalid internal transition attempts are normalized safely and cannot alter stored history. Controlled orchestration failures return the created execution as a `201` resource in `failed` state with safe error fields and zero counters.

Errors use the project's RFC 9457 Problem Details format with deterministic safe top-level codes. Relevant mappings are `400 invalid_request`, `404 not_found`, `409 conflict`, `422 validation_error`, and `500 unexpected_error`. A safe domain reason such as `execution_already_active` may be included as a normalized extension while the top-level code remains `conflict` per the established global status mapping. No response exposes SQL errors/constraints, stack traces, exception text, tokens, encrypted credentials, fingerprints, or arbitrary snapshot fields. Pagination/filter validation uses 422. The exact error body follows existing global Problem Details compatibility conventions.

## Non-goals

No scheduled creation/dispatch, scheduler, mining pipeline, repository execution resource, clone, commit traversal, finding, WebSocket, fake progress/result, or dashboard analytics endpoint is introduced.
