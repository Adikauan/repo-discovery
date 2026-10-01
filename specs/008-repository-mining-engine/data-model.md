# Data Model: Repository Mining Engine

Feature 008 adds durable per-repository execution history and bounded factual Repository Summary output. It extends MiningExecution for scope-resolution aggregate failures and a private completion marker needed to preserve legacy completion meaning. It does not add Finding persistence.

## MiningExecution (Feature 006, additive Feature 008 fields)

| Field | Type / constraint | Meaning |
|---|---|---|
| `id` | UUID, existing PK | Parent Mining Execution. |
| `snapshot` | immutable `ExecutionSnapshotV1` JSONB, existing | Sole historical scope intent, GitLab URL and instance identity. Never contains credentials. |
| `status` | existing execution status | Existing lifecycle service controls all transitions. |
| `repository_count` | nonnegative integer | Number of persisted unique RepositoryExecution rows for this execution. |
| `successful_repository_count` | nonnegative integer | Count of persisted rows with `completed` status. |
| `failed_repository_count` | nonnegative integer | Count of persisted rows with `failed` status; excludes scope failures. |
| `finding_count` | nonnegative integer | Sum of persisted RepositoryExecution finding counts; remains zero in Feature 008. |
| `scope_resolution_failure_count` | nonnegative integer, new | Number of explicit selected snapshot scope entries that could not be resolved. Does not create repository rows and does not change repository counters. |
| `repository_mining_completed` | boolean, new, default false | Internal marker set true only when Feature 008 successfully finalizes processing, including valid empty scope. Existing Feature 006 rows remain false so the detail API can preserve their orchestration-only completion meaning without inferring from zero counters. Not exposed in read DTOs. |
| `error_code`, `error_summary` | existing safe nullable pair; allowed on failed, and on `partially_completed` only for `scope_resolution_incomplete` | Curated execution-level pre-processing or scope-resolution result. Raw provider errors are never stored. |

**Execution aggregation**: valid resolved empty scope with zero resolution failures -> `completed`, all counters zero. All repository rows completed and no scope failures -> `completed`. At least one completed repository plus one or more failed repository rows or scope failures -> `partially_completed`. No successful repository and at least one repository/scope failure -> `failed`. Credential, instance-validation, or other pre-processing failure before any repository work -> `failed` with zero fabricated repository rows and normalized execution error. `scope_resolution_failure_count` contributes to aggregate state, not `failed_repository_count`.

## RepositoryExecution

One record exists for each unique resolved GitLab project in one MiningExecution. Unique identity is `(mining_execution_id, gitlab_project_id)` because the parent snapshot binds the execution to one GitLab instance.

| Field | Type / constraint | Meaning |
|---|---|---|
| `id` | UUID PK | Repository processing record identity. |
| `mining_execution_id` | UUID FK, non-null, `ON DELETE RESTRICT` | Historical parent execution. |
| `gitlab_project_id` | positive BIGINT, non-null | Stable provider project ID resolved against the validated snapshot instance. |
| `repository_name` | non-empty text | Safe resolved repository name snapshot. |
| `repository_full_path` | non-empty text | Safe resolved full path snapshot used for history/order. |
| `status` | `pending`, `running`, `completed`, or `failed` | Repository lifecycle; no public status mutation. |
| `started_at` | aware timestamp, nullable for pending | Time the processor began. |
| `completed_at` | aware timestamp, nullable until terminal | Completion/failure time. |
| `processed_branch` | nullable text | Provider-declared default branch used; populated on successful context creation. Never guessed. |
| `file_count` | nonnegative integer, default 0 | Eligible blob entries after centralized path exclusion. |
| `observed_extensions` | JSONB array of strings, database maximum 100 | Distinct normalized extensions, deterministically sorted; `(none)` represents no suffix. The runtime count is further bounded by `repository_mining_max_extensions` (1–100, default 100). |
| `extensions_truncated` | boolean, default false | True when eligible extensions exceeded the configured `repository_mining_max_extensions` retained limit. |
| `finding_count` | nonnegative integer, default 0 | Always zero for Repository Summary Rule. |
| `error_code`, `error_summary` | nullable safe pair | Curated repository failure code and summary; allowed only for failed status. |
| `created_at`, `updated_at` | aware timestamps | Persistence audit timestamps if required by repository conventions; not exposed unless contract requires. |

**Constraints and indexes**:

- Unique `(mining_execution_id, gitlab_project_id)` prevents duplicate work under overlapping groups/direct selections.
- Check positive project ID; allowed status; nonnegative file/finding counts; extension JSON is an array capped to 100 entries by domain validation; error pair consistency; timestamp ordering.
- Index `(mining_execution_id, repository_full_path, gitlab_project_id)` supports deterministic paginated history; additional status and project indexes support filtering/lookup.
- Restrict parent deletion; do not cascade-delete historical processing records.

**Lifecycle**:

```text
pending -> running -> completed
                   -> failed
```

`completed` and `failed` are terminal. A crash can leave a record pending/running and diagnosable; Feature 008 does not introduce another recovery worker. The existing Feature 006 stale execution reconciler remains the parent execution authority.

## Effective Repository and ScopeResolutionFailure (application value objects)

These are not new ORM models. `EffectiveRepository` contains project ID, resolved safe name/full path and instance identity used internally for deduplication. `ScopeResolutionFailure` contains a stable safe category and selected entry kind; it is counted on MiningExecution. Raw provider payloads/exceptions and credentials are excluded. The API exposes the aggregate failure count and curated execution-level code/summary, not provider internals or internal instance fingerprints.

## RepositoryContext (immutable domain value object)

Contains project ID, safe repository name/full path, selected default branch, and a bounded ordered sequence of metadata-eligible `RepositoryFileMetadata` values (path, file/blob type and optional stable size/binary indicators when reliably available). Metadata eligibility excludes directories and configured excluded paths; oversized or potentially binary entries remain eligible for metadata counts. It contains no HTTP client, raw GitLab DTO, SQLAlchemy record, credential, arbitrary binary body, or unbounded provider response.

Metadata eligibility and text-content eligibility are separate. `repository_mining_max_file_bytes` defaults to 1 MiB and applies to future text consumers: files above the limit are not fetched/passed as text. Binary content must not be passed as text; a reliable provider indicator may be used without retrieval, and unknown binary status must be made safe by a future bounded content reader before text is passed to rules. The current rule performs metadata-only tree analysis and makes no blob request, so it does not classify files by body or exclude oversized/binary metadata entries.

## RepositorySummaryResult and MiningRule contract

`RepositorySummaryResult` is an immutable typed result with `processed_branch`, `file_count`, `observed_extensions` (maximum 100 at persistence, further limited at runtime by configured `repository_mining_max_extensions`), `extensions_truncated`, and `finding_count=0`. Extensions use the final non-leading filename suffix, lowercase invariantly, include the dot, and sort lexically; retain the first configured number in sorted order and set truncation when further distinct values exist. Extensionless files and dotfiles without a later suffix map to `(none)`. Files inside excluded exact path segments do not count; directories never count; oversized or potentially binary files and unknown extensions remain eligible for metadata counts.

`MiningRule` has a stable identifier/version and consumes only RepositoryContext. Feature 008 registers RepositorySummaryRule. Summary facts are not Findings, and no Feature 010 entity or persistence contract exists here. Future finding-producing rule contracts and persistence require Feature 010 design.

## Data not persisted or returned

No token, encrypted token, authorization header, raw provider payload, exception/stack text, internal GitLab instance fingerprint, HTTP response, database concurrency metadata, file body, TODO/FIXME match, or unbounded rule JSON is stored in RepositoryExecution or returned from repository read APIs.
