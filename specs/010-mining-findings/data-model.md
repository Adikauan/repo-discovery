# Feature 010 Data Model

## MonitoringConfiguration author policy

The existing MonitoringConfiguration is extended with:

| Field | Type | Required/default | Validation |
|---|---|---|---|
| `allowed_author_emails` | ordered JSON array of strings | Required in new writes; defaults to `[]` for existing rows | At most 500 values; each input is at most 254 characters and a valid email; trim and Unicode case-fold; deduplicate by normalized value; persist deterministic sorted normalized values |

The list is policy input, not credential material. Create/update continues to use existing revision and ETag behavior. Empty list is valid and means every valid commit author email is unauthorized after baseline. Invalid author data from GitLab does not invalidate configured policy.

## ExecutionSnapshot

Extend the existing immutable snapshot with:

| Field | Type | Required/default | Validation |
|---|---|---|---|
| `allowed_author_emails` | tuple of strings | `()` when omitted by a legacy serialized snapshot | Values are already normalized, unique, and sorted at snapshot capture |

New manual and scheduled executions capture the same field through shared execution creation. Credentials, encrypted tokens, raw provider payloads, and scheduler internals remain excluded. Public `SnapshotResponse` does not expose this policy list by default. Older snapshots load with an empty tuple; historical completed findings are never reevaluated.

## RepositoryCheckpoint

One row represents the last successful author-analysis baseline for a configuration, stable GitLab project identity, and branch.

| Field | Type | Required/constraints |
|---|---|---|
| `id` | UUID | Primary key |
| `monitoring_configuration_id` | UUID FK | Required; `ON DELETE RESTRICT` |
| `gitlab_project_id` | BIGINT | Required, greater than zero |
| `branch` | text | Required, non-empty; exact branch identity returned by Feature 008 |
| `last_successful_commit_hash` | string(64) | Required full hexadecimal SHA of 40 or 64 characters |
| `updated_at` | timestamptz | Required, UTC-aware |

Unique key: `(monitoring_configuration_id, gitlab_project_id, branch)`. Add an index supporting configuration/project lookup. Checkpoint is updated in the same transaction as a successful RepositoryExecution terminal result and its Finding inserts. No current display path is used as identity.

## Finding

Finding is an immutable detection event. The parent MiningExecution is derived through RepositoryExecution; no duplicate execution FK is stored.

| Field | Type | Required/constraints |
|---|---|---|
| `id` | UUID | Primary key |
| `repository_execution_id` | UUID FK | Required; `ON DELETE RESTRICT` |
| `rule_id` | string(100) | Required, stable identifier |
| `rule_version` | string(32) | Required |
| `severity` | enum/string | Required; initial rule only permits `warning` |
| `title` | string(160) | Required, non-empty safe text |
| `summary` | string(500) | Required, non-empty safe text |
| `commit_hash` | string(64) | Required full hexadecimal SHA of 40 or 64 characters for initial rule |
| `author_email` | string(254) nullable | Normalized valid email only; NULL for missing/malformed provider identity |
| `author_email_state` | enum | Required: `valid`, `missing`, `malformed` |
| `author_name` | string(200) nullable | Optional sanitized display metadata; never used to identify the author |
| `authored_at` | timestamptz nullable | Provider authored time if valid |
| `commit_message_summary` | string(500) nullable | Control characters removed and at most 500 Unicode code points |
| `file_path` | text nullable | Null for Unauthorized Commit Author; reserved for future rules |
| `line_start` / `line_end` | integer nullable | Null for initial rule; if future rule sets them, both positive and `line_end >= line_start` |
| `created_at` | timestamptz | Required detection/persistence time in UTC |

Checks ensure supported severity and email state, valid nullable email relationships, and valid line ranges. Unique key `(repository_execution_id, rule_id, rule_version, commit_hash)` prevents repeated persistence for a commit/rule within one repository execution. Indexes support repository, rule, severity, created-time, and deterministic execution-scoped reads through the RepositoryExecution relationship.

Repository display path is joined from its owning RepositoryExecution, which already preserves the execution-time path; it is not duplicated on Finding. Finding candidates returned by rules are in-memory normalized values, not persistence rows. Application code validates candidate constraints and inserts findings; rules do not depend on SQLAlchemy.

## Repository execution and aggregate counters

Existing RepositoryExecution gains no new ownership model. Its existing `finding_count` is reconciled to the count of persisted Finding rows in the successful transaction. MiningExecution `finding_count` remains the sum of persisted RepositoryExecution counts during existing Feature 008 aggregation. Both counts must equal actual row counts after committed work; failed result transactions do not increment them.

## Lifecycle and invariants

- RepositoryExecution state transitions remain `pending -> running -> completed|failed`.
- Finding is inserted only as part of a successful repository result transaction.
- A baseline is persisted only after repository rule processing succeeds.
- Commit range failure, rule failure, persistence failure, or history rewrite leaves the prior checkpoint unchanged and produces no partial findings for that range.
- First successful baseline produces no finding from commits before current HEAD.
- Findings are append-only and have no open/acknowledged/resolved/ignored status.
- MonitoringConfiguration edits cannot mutate an existing execution snapshot, checkpoint, or Finding.

## Normalized repository failures

The incremental engine adds two safe RepositoryExecution error codes:

| Code | Safe summary |
|---|---|
| `commit_range_limit_exceeded` | The repository commit range exceeds the configured processing limit. |
| `repository_checkpoint_unreachable` | The stored repository checkpoint is no longer reachable from the selected branch. |

Persist only these normalized values. Provider response text and raw exception details are never stored.

## Migration and retention

Use Alembic migrations for the configuration JSONB field, Finding, and RepositoryCheckpoint. Existing configuration rows receive `[]`; existing execution snapshots without `allowed_author_emails` remain readable as `()`. Foreign keys use `RESTRICT` so execution and finding history is not cascade-deleted. Existing configuration retirement semantics remain authoritative.
