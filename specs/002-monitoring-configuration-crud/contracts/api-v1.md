# API Contract: Monitoring Configurations v1

## General

- Base path: `/api/v1`
- Media type: `application/json`; errors use `application/problem+json` with the documented
  Problem Details shape below.
- The backend generates Monitoring Configuration UUIDs; clients do not provide them on create.
  Date values are ISO 8601 UTC instants (for example,
  `2026-09-28T15:20:00Z`).
- The API exposes active configurations only. Retired and unknown IDs return the same not-found
  outcome through normal user-facing routes.
- Every response representation includes `version`, an opaque concurrency token, and an `ETag`
  header for the item. The API does not expose database revision or retirement metadata.
- Create and update validation is enforced on the backend. Raw stack traces, database errors,
  connection strings, or internal exception messages are never returned.

## Create

`POST /monitoring-configurations`

Optional header: `Idempotency-Key: <opaque retry token>`.

If supplied, the idempotency key must contain 1–128 visible ASCII characters with no whitespace
or control characters. It is not a Monitoring Configuration identifier and is not required to be a
UUID. A missing key is valid and makes each accepted POST a separate create intent. An invalid key
returns `400 Bad Request` without creating a configuration.

Request body:

```json
{
  "name": "Engineering repositories",
  "description": "Optional note",
  "gitlab_url": "https://gitlab.example.com"
}
```

`enabled` is not accepted in the create body. A successful create always saves the configuration
with `enabled: false`; a separate post-creation enable action is required. A client-selected `id`
is not accepted in the create body; unknown create fields, including `id`, return `422`.

- `201 Created`: returns `MonitoringConfigurationResponse` including the backend-generated `id`,
  an `ETag`, and `Location` pointing at the new item.
- When a key is supplied, repeating it with the same normalized body returns the original status,
  response snapshot, generated `id`, `ETag`, and `Location`; it does not create another record.
- Reusing a supplied key with different normalized values returns `409 Conflict` and changes
  nothing.
- A different key, or a request without a key, is a different creation intent, even when all
  configuration values match.
- `422 Unprocessable Content`: field validation errors.

## List and search

`GET /monitoring-configurations?search=<text>`

- `search` is optional; leading and trailing whitespace is trimmed.
- Matching is a case-insensitive substring of the configuration name. `%`, `_`, `*`, and other
  wildcard-like or escape characters are treated literally and do not alter matching semantics.
- Empty, whitespace-only, or omitted search returns all active records without a filter.
- `200 OK` response:

```json
{
  "items": [
    {
      "id": "c7f6139b-17bc-48fb-9ea2-1e4a4a35ad5c",
      "name": "Engineering repositories",
      "description": "Optional note",
      "gitlab_url": "https://gitlab.example.com",
      "enabled": false,
      "created_at": "2026-09-28T15:20:00Z",
      "updated_at": "2026-09-28T15:20:00Z",
      "version": "1"
    }
  ]
}
```

No pagination fields are included in v1. The endpoint returns the full active collection for the
initial small-to-moderate expected volume. Pagination must be reconsidered when real usage or
measured response size demonstrates a need; v1 imposes no arbitrary collection-size hard limit.

## Retrieve

`GET /monitoring-configurations/{id}`

- `200 OK`: returns one active `MonitoringConfigurationResponse` and `ETag`.
- `404 Not Found`: unknown or retired configuration.

## Update and enable/disable

`PUT /monitoring-configurations/{id}`

Required header: `If-Match: "<version token from the latest response>"`.

Request body is a full representation of editable values:

```json
{
  "name": "Engineering repositories",
  "description": null,
  "gitlab_url": "https://gitlab.example.com",
  "enabled": true
}
```

- `200 OK`: returns the saved representation and its new/current `ETag`.
- An actual change preserves `id` and `created_at`, updates `updated_at`, and advances `version`.
- An unchanged normalized body returns `200` without advancing `updated_at` or `version`.
- `428 Precondition Required`: `If-Match` is missing.
- `412 Precondition Failed`: token is stale; body and user edits remain available to reload/reapply.
- `404 Not Found`: unknown or retired configuration.
- `422 Unprocessable Content`: one or more fields are invalid; no partial update is saved.
- Sending the existing enabled value is safe and has no additional side effect. Status changes never
  start mining.

## Delete

`DELETE /monitoring-configurations/{id}`

The frontend calls this endpoint only after explicit user confirmation. The backend performs
logical retirement and retains the row and its values.

- `204 No Content`: retired successfully.
- `404 Not Found`: unknown or already retired configuration.
- No related or future records are cascade-deleted.

## Validation and errors

`ProblemDetails` follows the RFC 9457 field names with an optional stable `errors` extension:

```json
{
  "type": "https://example.invalid/problems/validation",
  "title": "Request validation failed",
  "status": 422,
  "detail": "Review the fields and try again.",
  "instance": "/api/v1/monitoring-configurations",
  "errors": [
    { "field": "name", "code": "required", "message": "Enter a configuration name." }
  ]
}
```

Known statuses: `201` create, `200` read/update, `204` delete, `400` malformed optional
idempotency key, `404` unavailable configuration, `409` idempotency-key payload conflict,
`412` stale update, `422` field validation or rejected unknown create fields (including a
client-provided configuration `id`),
`428` missing update precondition, and generic `500` unexpected service failure. Error `detail` and
field messages are user-safe; database/internal exception content is excluded.

## Compatibility

Changes within v1 remain backward compatible. Removing/renaming fields, changing normalization,
status semantics, idempotency behavior, concurrency semantics, or error meanings requires a new
contract version or a documented compatible migration. FastAPI's generated OpenAPI document is
validated against these operation and schema expectations in API contract tests.
