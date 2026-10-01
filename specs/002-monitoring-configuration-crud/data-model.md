# Phase 1 Data Model: Monitoring Configuration CRUD

## MonitoringConfiguration (domain entity)

Represents one persisted configuration for future repository mining intent. The domain entity is a
plain Python type and has no FastAPI, Pydantic, SQLAlchemy, PostgreSQL, or HTTP dependencies.

| Attribute | Type | Nullability | Rule |
|---|---|---:|---|
| `id` | UUID | Required | Generated once; stable and unique; immutable. |
| `name` | string | Required | Trim surrounding whitespace; reject when empty afterward; not unique. |
| `description` | string | Optional | Trim surrounding whitespace; normalize missing/blank to absent. |
| `gitlab_url` | string | Required | Trim surrounding whitespace; require an absolute HTTP or HTTPS URL with a host. |
| `enabled` | boolean | Required | New entity is always created `false`; may change only after creation through an explicit update/lifecycle action. |
| `created_at` | timezone-aware datetime | Required | Set by application in UTC at creation; immutable. |
| `updated_at` | timezone-aware datetime | Required | Set with creation; change only after a successful change to saved values. |
| `revision` | positive integer | Required | Internal concurrency token; increments for each actual update; not a user-editable field. |
| `retired_at` | timezone-aware datetime or null | Optional | Set at logical deletion; not part of normal API response and not user-editable. |

### Invariants and operations

- Factory generates `id` in the backend and accepts name, description, and GitLab URL only; it sets
  `enabled=false`, regardless of client input. Create requests do not accept a client-selected ID
  or status override. A `CreateRequestReceipt` is created only when an optional idempotency key is
  supplied.
- `update` validates all editable values atomically. It preserves `id` and `created_at`. If all
  normalized values are unchanged, it preserves `updated_at` and `revision`; otherwise it sets
  `updated_at` using an injected UTC clock and increments `revision`.
- `set_enabled` is a post-creation explicit action. A request for the current status is a safe
  no-op and does not change `updated_at` or `revision`.
- `retire` marks the entity with `retired_at` and updated lifecycle time. It does not remove the
  record, clear its values, or cascade to unrelated/future records.
- Normal list/get/update operations exclude retired entities. A later history capability may
  resolve a retired configuration reference through an internal history-specific boundary.

## CreateRequestReceipt (infrastructure support record)

Durable record used only to implement the accepted idempotent create-request contract.

| Attribute | Type | Nullability | Rule |
|---|---|---:|---|
| `request_key` | string | Required | Unique opaque token supplied in the optional `Idempotency-Key` header for one create intent; it is not the configuration ID. |
| `request_fingerprint` | string | Required | Hash of canonical normalized create values; same key with a different fingerprint conflicts. |
| `configuration_id` | UUID | Required | References the created configuration; no physical delete is performed. |
| `response_snapshot` | JSON value | Required | Original create response fields and status/headers needed to replay the initial result. |
| `created_at` | timezone-aware datetime | Required | UTC time the receipt is created. |

When a key is supplied, receipt and configuration are committed atomically. Same key/same fingerprint
replays the stored result, including the backend-generated configuration ID, even if the configuration
has since been edited or retired. Same key/different fingerprint returns conflict and makes no write.
A new key is a new create intent and may create identical configuration values. A create request
without a key is accepted as a separate intent and does not receive keyed replay guarantees. Receipt
expiry/cleanup is not part of this feature because it could make a late retry create a duplicate.

## Persistence mapping

The first Alembic revision creates `monitoring_configurations` and `create_request_receipts`.
UUID primary keys and the request-key unique constraint enforce identity/race safety. Timestamps
use timezone-aware columns. Configuration rows use `enabled NOT NULL DEFAULT FALSE`,
`revision NOT NULL`, and nullable `retired_at`. Name and URL have no uniqueness constraints.
There are no foreign-key cascades; receipt references remain valid because configurations are
logically retired rather than physically deleted.

## API presentation models

- **MonitoringConfigurationResponse**: `id`, `name`, `description`, `gitlab_url`, `enabled`,
  `created_at`, `updated_at`, and opaque `version` (derived from `revision`). It excludes
  `retired_at`, request keys, fingerprints, and persistence metadata.
- **CreateMonitoringConfigurationRequest**: `name`, optional `description`, `gitlab_url`. Does
  not accept `id` or `enabled`; the backend generates the ID and always disables creation. An
  optional `Idempotency-Key` is a separate retry token, not a resource identifier.
- **UpdateMonitoringConfigurationRequest**: full replacement of `name`, optional `description`,
  `gitlab_url`, and `enabled`; requires the version token obtained from the current response.
- **MonitoringConfigurationListResponse**: `items` array of active configuration responses. Search
  is optional, trimmed, case-insensitive literal substring matching; empty/whitespace-only values
  apply no filter. Pagination is not defined for the initial small-to-moderate expected volume.
- **ProblemDetails**: `type`, `title`, `status`, `detail`, `instance`, and optional `errors` entries
  with `field`, stable `code`, and user-safe `message`.
