# Research: Repository Mining Engine

## Decision: Extend established Feature 001–007 boundaries rather than introduce parallel models

**Decision**: Keep the root `src/` Vite application, central route registry and shell from Feature 001; preserve Feature 002's soft-retired configuration history; use Feature 003's encrypted credential and normalized GitLab URL fingerprint; use Feature 004's persisted explicit scope and ownership semantics; keep Feature 005's scheduling configuration separate from actual scheduled execution; reuse Feature 006's immutable execution snapshot/lifecycle; and replace only the Feature 007 Repositories placeholder with the new repository history read.

**Rationale**: The new pipeline adds repository processing history without changing the established configuration, scope, scheduling-intent, execution, or dashboard ownership boundaries. Feature 009 may invoke the same application mining use case later; Feature 008 does not add a scheduler.

**Alternatives considered**: Move the UI, configuration or execution code into new packages; duplicate schedule or lifecycle state; or create another dashboard route; rejected because existing contracts already provide the necessary integration points.

**Evidence**: [Feature 001 plan](../001-application-shell/plan.md), [Feature 002 plan](../002-monitoring-configuration-crud/plan.md), [Feature 003 research](../003-gitlab-connection/research.md), [Feature 004 specification](../004-gitlab-scope-selection/spec.md), [Feature 005 plan](../005-scheduling-configuration/plan.md), [Feature 006 plan](../006-execution-model-history/plan.md), and [Feature 007 plan](../007-execution-dashboard/plan.md).

## Decision: Use the existing execution snapshot and lifecycle service as the pipeline entry

**Decision**: `CreateManualExecution` continues to persist the execution and transition it through the existing Feature 006 lifecycle. Replace its orchestration-only callback with the application-owned `ProcessMiningExecution` use case. Keep expected-status transitions, active-configuration exclusion (at most one active Mining Execution per Monitoring Configuration), idempotency receipt behavior, and stale reconciliation in the existing lifecycle path. A non-stale pending/running execution yields the existing normalized conflict before the losing request enters repository processing. The repository worker bound applies only within the winning execution; do not add a second execution-concurrency mechanism.

**Rationale**: Feature 006 already supplies the immutable `ExecutionSnapshotV1`, lifecycle invariants, and request idempotency. The manual path should invoke the same pipeline future scheduled triggers can call, without inventing a second state machine or scheduler.

**Alternatives considered**: A new mining execution table/state machine or a scheduled-only worker pipeline; rejected because both duplicate authoritative lifecycle behavior.

**Evidence**: [Feature 006 plan](../006-execution-model-history/plan.md), [Feature 006 data model](../006-execution-model-history/data-model.md), existing `backend/app/application/use_cases/create_manual_execution.py` and `transition_execution.py`.

## Decision: Treat the execution snapshot as sole scope intent; record partial scope failures separately

**Decision**: Resolve selected snapshot group and repository entries against the snapshot GitLab instance. Deduplicate projects by stable instance identity and GitLab project ID. Continue processing resolved projects when another selected scope entry is inaccessible or invalid. Persist a separate `scope_resolution_failure_count` on MiningExecution and allow only the approved safe scope error projection for partial/failed outcomes. Keep `failed_repository_count` exactly equal to failed RepositoryExecution records; do not create fake repository rows for group failures.

**Rationale**: This simultaneously preserves useful partial processing, makes invalid selection distinct from valid empty scope, and keeps every repository counter reconcilable with real repository records.

**Alternatives considered**: Treat all scope errors as empty success; rejected as silent loss of selected intent. Convert group errors to fake RepositoryExecution rows or inflate `failed_repository_count`; rejected because neither represents an actual repository record. Fail the entire execution before processing all resolved repositories; rejected because it discards useful independent results.

**Evidence**: Feature 004 defines group selection and excludes projects only shared into the selected hierarchy; Feature 006 stores selected intent and GitLab instance fingerprint in `ExecutionSnapshotV1`; approved Feature 008 clarifications define empty and partial-resolution outcomes.

## Decision: Resolve credentials at runtime and validate instance identity before provider requests

**Decision**: Load only the encrypted credential associated with the execution's Monitoring Configuration; validate its configured/last-validated URL fingerprint against the execution snapshot and scope fingerprint before any historical ID request. Decrypt after successful checks, keep the token call-local for the execution pipeline, and never put it in execution/repository entities, worker state that is persisted, response DTOs, or logs.

**Rationale**: Feature 006 deliberately excludes secrets from snapshots. Matching identity first prevents numeric historical IDs from being interpreted on a replacement GitLab instance.

**Alternatives considered**: Store a token or decrypted credential in the snapshot; rejected by the security boundary. Query the current URL with historical IDs and rely on 404; rejected because IDs may collide across instances.

**Evidence**: Feature 003 secure credential storage and URL fingerprinting, Feature 006 scope/credential boundary, `GetGitLabScopeTree` decryption and normalized URL fingerprint conventions.

## Decision: Use GitLab project metadata and recursive tree APIs; do not clone or download archives

**Decision**: Retrieve the provider-declared `default_branch` from the GitLab Projects API, then request the recursive Repository Tree API at that exact reference. Page all entries and process only normalized paths/types. No blob or file content is fetched by the Repository Summary Rule.

**Rationale**: The summary needs branch, file paths, and blob/tree types; metadata is sufficient to count eligible files and extensions. This avoids repository transfer, temporary storage, decompression, and binary-content handling.

**Alternatives considered**: Archive download; rejected because it transfers bytes unused by this rule and adds decompression/storage risks. Shallow clone; rejected because local Git and disk management are unnecessary. Individual file/blob API; deferred until a future rule requires bounded text content.

**Provider contract evidence**: The official [GitLab Projects API](https://docs.gitlab.com/api/projects/) exposes project `default_branch`. The official [GitLab Repositories API](https://docs.gitlab.com/api/repositories/) supports `recursive=true`, explicit `ref`, and paging for repository tree reads. The [GitLab REST API pagination guide](https://docs.gitlab.com/api/rest/) documents page sizing and pagination headers, and notes that some headers may be absent on GitLab.com; therefore the adapter must not use a missing `X-Next-Page` alone to conclude that a full page was final.

## Decision: Bound and normalize repository tree processing

**Decision**: Use a 100-entry API page and continue while pages are full, even if pagination headers are absent. Fail safely if the repository exceeds 50,000 tree entries or pagination repeats/malforms; never report a partial tree as a successful complete summary. Normalize and sort paths before rule execution. Exclude paths containing exact case-insensitive segments `.git`, `node_modules`, `vendor`, `bin`, `obj`, `dist`, or `build`. Metadata-eligible file/blob entries count; directories do not. `repository_mining_max_extensions` is configurable from 1 through 100 (default 100); retain no more than the configured count of unique normalized extensions in sorted order, and set `extensions_truncated` when the bound is exceeded.

**Rationale**: The explicit bounds keep memory and persistence predictable while preserving an honest complete-result guarantee. Metadata-only summary does not need file-size or binary inspection; oversized or potentially binary files remain in metadata counts when path-eligible.

**Alternatives considered**: Silently stop at one page or at a configured tree cap; rejected because it would misstate file counts. Download contents for summary binary or size checks; rejected because the initial rule never reads content. Excluding oversized files from summary metadata was rejected because the configured size bound governs future text input, not metadata eligibility.

## Decision: Use a bounded worker pool aligned with the existing synchronous HTTPX client

**Decision**: Keep the current synchronous FastAPI/use-case and HTTPX client pattern. Use a `ThreadPoolExecutor` with a bounded in-flight submission window and `REPOSITORY_MINING_CONCURRENCY` default 4, maximum 8. Each worker creates its own unit of work/session for short persistence operations; no SQLAlchemy session is shared across threads.

**Rationale**: The existing GitLab client uses synchronous `httpx.Client`, and manual execution is synchronous today. A bounded worker pool provides repository concurrency without blocking an async event loop, rewriting existing clients, or allocating one task per repository.

**Alternatives considered**: `asyncio.Semaphore` around synchronous I/O; rejected because synchronous provider requests would block the event loop. Converting the entire request and GitLab adapter to async; rejected because it expands the change without benefit for this first metadata-only pipeline. Unbounded futures; rejected because memory/work queues would scale with scope size.

## Decision: Persist typed Repository Summary fields, not generic rule output or Findings

**Decision**: Store `processed_branch`, `file_count`, bounded JSONB `observed_extensions`, `extensions_truncated`, and `finding_count=0` directly on RepositoryExecution. Keep a typed, transport-independent MiningRule/RepositoryContext contract. Only RepositorySummaryRule is registered for Feature 008.

**Rationale**: These are stable small facts required by the dashboard and do not justify arbitrary output blobs, a child table, or the future Finding model.

**Alternatives considered**: Full Feature 010 Finding model, TODO/FIXME findings, or unconstrained JSON rule output; rejected as out of scope and inconsistent with the approved factual-only rule.

## Decision: Preserve independent repository outcomes with short PostgreSQL transactions

**Decision**: Commit execution `running` before provider calls, create pending repository rows in a short write, then for each repository commit `running` and its terminal status/result independently. Aggregate from persisted records in a final short transaction and transition the parent using the Feature 006 lifecycle service. Never retain locks/transactions across GitLab requests.

**Rationale**: A failure or process crash should not erase completed repositories, and concurrency requires separate database sessions per worker.

**Alternatives considered**: One transaction for the entire execution; rejected because it holds locks during network work and rolls back valid partial results. SQLite as a substitute for PostgreSQL-specific integration; rejected by the feature constraint and Feature 006 history.

## Decision: Add read-only repository APIs and integrate the existing dashboard section

**Decision**: Add bounded deterministic list and safe detail reads under the existing execution resource; replace the Feature 007 Repositories unavailable state with persisted rows and safe list states. Keep Findings detail unavailable and reuse all current dashboard layout/tabs.

**Rationale**: Repository outcome history is the minimal user-visible evidence required by Feature 008. The route and dashboard already exist.

**Alternatives considered**: New dashboard route, mutable repository status endpoints, full Finding UI; rejected because existing navigation and read-only history suffice.

## Deferred decisions and feature boundaries

- Feature 009 scheduling is deferred; its future trigger must invoke this same application use case.
- Feature 010 Finding persistence and findings UI are deferred. Repository Summary output is factual and the Feature 008 finding counter remains zero.
- Repository file body reads and text-content loading are deferred. Any future text reader must skip files above `repository_mining_max_file_bytes` and must never pass binary content as text; it may use a reliable provider binary indicator or perform bounded detection after retrieval. Feature 008 does not fetch content solely for summary classification. Commit traversal, clone/archive support, automatic retries, crash recovery beyond Feature 006 reconciliation, cancellation, live progress, AI/LLM/embedding analysis, and advanced charts are also deferred.
- PostgreSQL constraint/concurrency validation is required when `TEST_DATABASE_URL` is available; otherwise it remains explicitly unverified rather than replaced with SQLite.
