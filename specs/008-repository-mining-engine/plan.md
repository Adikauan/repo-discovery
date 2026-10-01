# Implementation Plan: Repository Mining Engine

**Branch**: `008-repository-mining-engine` | **Date**: 2026-09-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature 008 specification and approved clarification decisions

## Summary

Feature 008 replaces Feature 006's orchestration-only completion with one application-owned mining pipeline. It reads the immutable execution snapshot, verifies the associated secure GitLab connection identifies the same instance, resolves the snapshot's selected groups and repositories, and processes unique resolved projects with a four-repository concurrency bound. A dedicated repository processor retrieves only project metadata and the recursively paginated tree for its provider-declared default branch, creates a normalized context, and runs a deterministic metadata-only Repository Summary Rule. Repository outcomes and bounded summary facts are persisted per execution; execution counters are reconciled from those records and a separate scope-resolution-failure count. The existing Feature 006 lifecycle and same-configuration active-execution protection remain authoritative. The existing Feature 007 dashboard route receives a read-only repository list contract and renders persisted rows.

Successfully resolved empty scope completes with zero counters. Invalid selected scope entries remain explicit failures: accessible projects continue, partial scope failure can make a successful execution `partially_completed`, and no fake `RepositoryExecution` rows are created. Repository Summary facts are not Findings; no Feature 010 Finding persistence or TODO/FIXME rule is added. Metadata eligibility and future text-content eligibility are separate policies: summary metadata can include oversized or binary files after path filtering, while future text rules must skip oversized files and must never receive binary content as text.

## Technical Context

**Language/Version**: Python 3.13–3.14 backend; TypeScript/React frontend (existing project settings)

**Primary Dependencies**: Existing FastAPI, Pydantic, SQLAlchemy, Alembic, HTTPX, React, Material UI, React Router, Vitest, Testing Library; no new library dependency planned

**Storage**: Existing PostgreSQL database; migration-managed `repository_executions` and a bounded JSONB extension summary on the row; additive MiningExecution scope-failure aggregate fields

**Testing**: pytest unit/API/integration suites, controlled GitLab HTTP transport mocks, Vitest/Testing Library/axe-core; PostgreSQL integration tests when `TEST_DATABASE_URL` is available

**Target Platform**: Existing backend service and browser application

**Project Type**: Full-stack web application with Clean Architecture backend and React frontend

**Performance Goals**: At most 4 repositories processed concurrently by default inside one Mining Execution; at most 50,000 tree entries per repository; bounded 100-item provider pages; no repository archives or file bodies for the summary rule

**Constraints**: Reuse snapshot and Feature 006 lifecycle; verify instance identity before any historical-ID request; decrypt credentials only for a request-scoped pipeline lifetime; never hold DB transactions across GitLab calls; no retry by default; tree overflow fails explicitly rather than silently truncating; no scheduler, Finding model, AI, progress stream, or cancellation

**Scale/Scope**: Manual executions and future reusable invocation only; Feature 006 permits at most one active execution per Monitoring Configuration; inside each valid execution, 4 concurrent repositories by default, configurable within a bounded range; maximum 50,000 provider tree entries per repository; configured maximum of 100 stored distinct extensions per repository (default 100)

## Constitution Check

*Gate before Phase 0: PASS.*

| Principle | Gate assessment |
|---|---|
| I. Clean Architecture and Responsibility Boundaries | Pass. Domain value objects/entities own invariants; application ports/use cases orchestrate; GitLab and SQLAlchemy stay in infrastructure; FastAPI and React remain interface adapters. |
| II. Domain-Centered Business Rules | Pass. Lifecycle transitions, repository transitions, result normalization, summary semantics, and aggregate status each have one authoritative owner. |
| III. Explicit, Versionable Contracts | Pass. Additive safe Pydantic DTOs and documented list/detail API behavior; no raw provider/persistence models cross the boundary. |
| IV. Abstracted External Integrations | Pass. Add a mining-specific GitLab port and HTTP adapter behind application-owned protocols; rules consume normalized context only. |
| V. Secure by Construction | Pass. Runtime decrypt is scoped to the pipeline; snapshot and records exclude credentials; errors and logs use allow-listed safe codes/summaries. |
| VI. Immutable and Reproducible Execution History | Pass. Snapshot remains authoritative; RepositoryExecution captures resolved safe repository names/paths and processing branch; current scope selections never replace snapshot intent. |
| VII. One Controlled Mining Pipeline | Pass. Manual requests invoke the shared application pipeline through the existing creation/lifecycle flow; no second scheduler pipeline or public mutation endpoint. |
| VIII. Observable Execution Lifecycle | Pass. Persist repository status/times, safe errors, summary counters, and scope-resolution failure count; no real-time transport is required. |
| IX. Migration-Managed Persistence | Pass. Add one Alembic migration with constraints, indexes and restrictive historical ownership; preserve execution history. |
| X. Risk-Based Automated Verification | Pass. Tests cover snapshot authority, failure isolation, safe boundaries, idempotency/uniqueness, concurrency, APIs, and UI states. PostgreSQL-specific claims are conditional on actual PostgreSQL execution. |
| XI. Deliberate, Reusable User Experience | Pass. Reuse the Feature 007 Repositories section and shared accessible table/feedback/status patterns; avoid dashboard redesign. |
| XII. Incremental Simplicity and Justified Dependencies | Pass. Use metadata APIs rather than clone/archive, add no dependency, and implement only factual summary results. |

**Gate result**: Pass. No constitutional exception or complexity justification is required.

## Project Structure

### Documentation (this feature)

```text
specs/008-repository-mining-engine/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── repository-execution-api.md
│   └── repository-dashboard.md
└── tasks.md                 # Phase 2 output; not created by this plan
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── domain/
│   │   ├── entities/mining_execution.py          # Existing lifecycle; safe scope aggregate extension
│   │   ├── entities/repository_execution.py      # Repository lifecycle and safe result fields
│   │   ├── value_objects/repository_context.py   # Transport-free rule input
│   │   ├── value_objects/repository_summary.py   # Bounded factual summary output
│   │   └── ports/                                 # Mining-specific GitLab repository port
│   ├── application/
│   │   ├── ports/                                 # Repository execution and mining provider protocols
│   │   └── use_cases/
│   │       ├── process_mining_execution.py        # Credential, identity, scope, bounded orchestration
│   │       ├── resolve_effective_scope.py         # Snapshot-to-unique-project resolution
│   │       ├── process_repository.py              # One repository lifecycle + rule execution
│   │       ├── list_repository_executions.py      # Safe, ordered read
│   │       └── get_repository_execution.py        # Safe detail read
│   ├── infrastructure/
│   │   ├── database/models.py                     # RepositoryExecution ORM mapping
│   │   ├── database/sqlalchemy_repositories.py   # Persistence and aggregate transaction methods
│   │   └── gitlab/                                # Project metadata and recursive tree adapter
│   └── api/v1/
│       ├── executions.py                         # Repository list/detail routes
│       └── execution_schemas.py                  # Safe response DTOs
├── alembic/versions/0006_repository_executions.py
└── tests/
    ├── unit/domain/                               # Entity/rule/aggregation invariants
    ├── unit/application/                          # Resolver, processor and orchestrator tests
    ├── unit/infrastructure/gitlab/                # Mocked HTTP and paging contract tests
    ├── api/                                       # Safe list/detail/error contracts
    └── integration/                               # PostgreSQL constraints/transactions when available

src/features/executions/
├── api/executionsApi.ts                           # Add repository list/detail reads
├── types/execution.ts                             # Repository DTOs only
├── components/ExecutionRepositoriesSection.tsx    # Replace unavailable state with persisted list
└── pages/ExecutionDashboardPage.tsx               # Pass route execution id to repository section
src/test/features/executions/                      # API, status, empty/loading/error, accessibility tests
```

**Structure Decision**: Extend the existing `backend/app` Clean Architecture and `src/features/executions` feature boundary. Mining services and protocols are feature-specific. The current GitLab scope client continues to serve configuration browsing; the mining adapter adds only the group/subgroup-owned project discovery, project metadata, and repository-tree reads required by the resolver and summary rule. The existing `/executions/:id` route, page shell, tabs, and dashboard layout remain in place.

## Design Decisions

### Pipeline boundaries

`ProcessMiningExecution` is an application use case, not a monolithic provider/persistence service. It coordinates credential resolution, snapshot instance validation, `EffectiveScopeResolver`, durable row creation, bounded `ProcessRepository` calls, persisted-result aggregation, and the existing execution transition use case. `ProcessRepository` owns one repository record's pending → running → completed/failed lifecycle. It calls the mining provider port, constructs `RepositoryContext`, executes registered deterministic rules (initially only `RepositorySummaryRule`), persists the typed summary, and returns a normalized outcome. Each boundary has its own protocol and unit tests.

Manual execution creation remains guarded by Feature 006's existing active-execution protection before `ProcessMiningExecution` is invoked. A non-stale pending/running execution for the same Monitoring Configuration produces the existing normalized conflict; the losing request does not enter the mining pipeline. Existing stale reconciliation and request idempotency remain unchanged. This guard is the execution-level concurrency control and is not replaced by the repository worker limit.

### Scope resolution and partial failures

The resolver consumes `ExecutionSnapshotV1` only. Direct repositories resolve by stable project ID; selected group hierarchies are traversed using Feature 004 ownership semantics (owned projects in group/subgroups, no shared-only projects). Results are deduplicated by `(snapshot instance fingerprint, project ID)` and sorted by normalized full path then numeric project ID. Each explicit selected entry that cannot be resolved is a normalized scope failure; failures are not converted into empty scope. Continue processing independently resolved repositories.

Persist `scope_resolution_failure_count` separately on `MiningExecution`. It counts explicit selected snapshot entries that failed resolution; if traversal of a selected group's hierarchy is incomplete, count that selected group once even if multiple nested provider requests failed. Do not create fake repository rows or overload `failed_repository_count`. The latter remains exactly the number of failed RepositoryExecution rows; `repository_count` remains exactly the number of rows created. A safe execution error object with code `scope_resolution_incomplete` accompanies `partially_completed`; for a failed execution it uses `scope_resolution_failed`. Aggregate state counts repository failures plus scope failures: valid empty scope with no scope failures is completed; all repository rows completed and no scope failures is completed; at least one repository success plus any repository/scope failure is partially completed; zero successes with one or more repository/scope failures is failed; credential/instance/pre-processing failure before work is failed with zero fabricated repository rows. If some scope entries fail but others resolve, resolved work proceeds.

The API exposes only the scope failure count and curated safe execution-level code/summary, not raw provider results or internal fingerprints. If the existing Feature 006 lifecycle/DTO currently restrict error metadata to `failed`, its domain validation, persistence constraint, and safe DTO are minimally extended to permit only the approved scope-resolution code on `partially_completed`. No other lifecycle transition is added.

### Credential and GitLab instance boundary

At invocation, the application loads the execution and its immutable snapshot, then loads the current configuration only to validate connection identity and retrieve the associated encrypted credential through existing repositories. It must not read the current configuration name or scope as historical context. Before any provider request, require the normalized fingerprint of the snapshot GitLab URL, the current configured GitLab URL, the credential's validated URL fingerprint, and every snapshot scope item's stored instance fingerprint to match. Missing credential, decryption failure, absent/invalid validation identity, or any mismatch is a safe pre-processing failure; do not query GitLab with historical IDs. Decrypt once after checks and keep the plaintext token only in the call-local pipeline scope; never assign it to domain entities or log context. Use the snapshot GitLab URL for requests once the identity match succeeds. An implementation may use the existing `normalized_url_fingerprint` helper rather than duplicating its canonicalization.

### GitLab retrieval strategy

For selected groups, use the GitLab Groups API to validate the selected group, enumerate subgroups recursively, and list only projects owned directly by each group (`include_subgroups=false`, `with_shared=false`). For direct selected repositories, use the Projects API to resolve stable IDs and safe metadata. For processing, retrieve project safe metadata including `default_branch`, then the Repository Tree API with `recursive=true` and the exact default branch. Do not clone, shallow-clone, download an archive, or retrieve blob bodies for Repository Summary Rule. The rule needs file paths and tree/blob classification only. Compare alternatives:

| Strategy | Decision | Reason |
|---|---|---|
| Project + recursive tree APIs | Selected | Minimal data transfer for branch and factual file/extension counts; no local clone or file-content handling. |
| Archive download | Rejected for this rule | Transfers all source bytes, uses more memory/storage and introduces decompression and binary concerns without adding summary value. |
| Shallow clone | Rejected for this rule | Requires local Git/process/temp-directory management and transfers blob data unnecessarily. |
| Individual file APIs | Deferred | Needed only when a future approved rule consumes bounded file content. |

The adapter maps provider objects to a narrow normalized project/tree value object and maps provider statuses/exceptions to a closed safe outcome taxonomy. Follow every page deterministically: request `per_page=100`, advance offset pages until a short/empty page even when GitLab omits pagination headers, deduplicate stable tree object IDs/paths, and reject repeated pages or malformed paging. Limit each repository to 50,000 returned tree entries; exceeding this bound fails that repository with safe `repository_tree_limit_exceeded` instead of reporting an incomplete successful count. Sort normalized tree paths before rule execution. Repository default branch missing/blank fails with `repository_default_branch_missing`; no branch name is guessed.

### File policy and Repository Summary Rule

File filtering defines two separate policies. **Metadata eligibility** for Repository Summary Rule excludes a tree entry when it is a directory or its path contains an exact case-insensitive segment `.git`, `node_modules`, `vendor`, `bin`, `obj`, `dist`, or `build`; this applies at any depth and is a documented broad exclusion policy. Unknown extensions remain eligible. Every other blob/file entry contributes to `file_count` and observed extensions, including oversized files and files that may be binary. The rule does not retrieve contents and does not perform binary detection or size-based exclusion; a provider binary indicator may be retained if reliably available without retrieval, but it is not required.

**Text-content eligibility** is a separate safety boundary for future rules that load file bodies. Content above `repository_mining_max_file_bytes` (1 MiB default) is excluded from text-rule input and is not fetched for those rules. Binary content must never be passed as text. A reliable provider binary indicator may reject a file before fetch; when status is unknown, a future bounded content reader must detect binary data before decoding or passing text to a rule. Feature 008 has no file-body reader, so it must not download blobs solely to classify summary files. Skipping an oversized or binary file for text rules does not fail repository processing by default.

Extension semantics: use the last suffix after a non-leading dot in the basename, lowercase invariantly, include the leading dot (for example `.ts`), and use the literal `(none)` for extensionless names and dotfiles without a later suffix. Build distinct extension names from metadata-eligible files and sort lexicographically by normalized Unicode code point. `repository_mining_max_extensions` is a validated integer from 1 through 100, default 100; the rule uses its configured value and retains no more distinct extensions than that value. When more exist, retain the first configured number in deterministic sorted order and persist `extensions_truncated=true`; otherwise it is false. `file_count` still counts all metadata-eligible files, including files whose extensions are not retained. Outputs are deterministic for the same normalized tree and configured limit. `finding_count` and the execution aggregate remain zero because these facts are not Findings.

`MiningRule` consumes `RepositoryContext` and returns a typed `MiningRuleResult`; it has an immutable identifier/version and no GitLab/HTTPX/SQLAlchemy/FastAPI dependency. The registry is an application composition concern. Only `RepositorySummaryRule` is registered for Feature 008. Results use typed fields rather than an unbounded arbitrary JSON blob.

### Repository persistence and transactions

One migration adds `repository_executions` with a restrictive FK to `mining_executions`, unique `(mining_execution_id, gitlab_project_id)`, stable repository safe identity fields, status/timestamps, processed branch, file_count, bounded JSONB `observed_extensions`, `extensions_truncated`, finding_count, and safe nullable error fields. Add indexes for execution/order, status and project ID. Retain history if a configuration is retired; no cascade from execution deletion is introduced. Application-level deduplication and the DB unique constraint both prevent duplicate project processing.

Add `scope_resolution_failure_count` to MiningExecution and widen its safe error constraint only for the exact supported `partially_completed` scope-resolution exception described above. Existing `repository_count`, successful/failed row counts, and finding_count retain their meanings. Persist summary fields and lifecycle changes through short transactions; never retain a transaction or row lock while waiting on GitLab. Commit execution `running` before scope/provider work; persist all resolved RepositoryExecution `pending` rows in one short transaction; each worker commits running, then success summary/completed or safe failure independently; after all workers settle, recompute counters from repository rows plus the scope failure count and finalize execution via the Feature 006 lifecycle service. Failure to persist a final state is left to existing stale reconciliation and must not be falsely represented as completed.

### Concurrency, failure isolation, retries, and crash behavior

Use a `ThreadPoolExecutor` with configurable `REPOSITORY_MINING_CONCURRENCY` default 4, validated from 1 through 8, and an in-flight submission window no larger than the worker count. This is only the per-execution repository-processing limit; it cannot authorize or start a second active execution for the same Monitoring Configuration. The Feature 006 active-execution guard runs before the pipeline, rejects a competing non-stale pending/running execution through the existing normalized conflict, and remains responsible for stale reconciliation. The existing application path and GitLab HTTPX client are synchronous; a bounded worker pool gives actual I/O concurrency without blocking an async event loop or converting the service to async. Do not create one future for every selected repository at once. Each repository has its own short-lived unit of work/session; workers do not share a SQLAlchemy session. One repository error is normalized and committed, then workers continue. Provider auth, authorization, not-found, malformed response, timeout, transport, and tree-bound failures have safe codes. Automatic retries are disabled, including transient failures; existing HTTP client behavior must be inspected for implicit retries and disabled for this adapter if present. Feature 006 stale execution reconciliation remains authoritative; a crashed repository remains pending/running and diagnosable, with no new recovery worker in this feature.

### API and dashboard integration

Add `GET /api/v1/executions/{execution_id}/repositories?page=&pageSize=` (default 25, max 100, deterministic `(repository_full_path ASC, gitlab_project_id ASC)` ordering) and `GET /api/v1/executions/{execution_id}/repositories/{repository_execution_id}`. List response includes page metadata and safe row fields; detail adds all persisted summary fields but no ORM/provider shape. Return normalized not-found errors for absent execution or repository row, and never permit status writes. Extend existing execution detail with `scopeResolutionFailureCount`; use the existing safe `error` projection for approved partial scope error. Update `completionMeaning` projection so completed Feature 008 executions no longer claim mining was skipped: successful empty scope states that no repositories were in the resolved scope; successful non-empty scope states that repository processing completed. Preserve existing execution DTO compatibility otherwise.

In `ExecutionDashboardPage`, pass the current route execution ID to `ExecutionRepositoriesSection`. The section fetches only the repository execution API when its tab is selected (or through existing dashboard data-fetch style if implementation conventions require), shows accessible loading/error/retry/empty/list states, and renders repository path, status text/icon, processed branch, file_count, findings count (`0`), timestamps, and safe error summary. Display the scope-resolution aggregate warning in the existing execution overview/header context when the execution detail carries the normalized partial-scope error. Keep Findings detail unavailable; no Finding API or UI model is added. No current configuration query or GitLab request occurs in the browser.

### Completion meaning for stored executions

Migration `0006` adds private `repository_mining_completed BOOLEAN NOT NULL DEFAULT FALSE`. Existing Feature 006 rows remain false and retain the API meaning that orchestration completed without repository mining. Feature 008 sets the marker true only for successful finalization, including valid empty scope. The API uses this persisted marker rather than inferring mining from counters, and does not expose the marker itself.

### Chart/dependency decision

No charting library or new runtime dependency is justified. The initial data are per-repository facts and statuses, best represented by a semantic table/list and existing metric cards; there is no time series or finding category dataset.

## Constitution Check (post-design)

*Gate after Phase 1: PASS.*

| Principle | Post-design evidence |
|---|---|
| I–II. Boundaries and rule ownership | `data-model.md` and contracts separate domain entities, application use cases/ports, infrastructure adapters, and API DTOs. Status/aggregation logic has one owner. |
| III. Explicit contracts | [`contracts/repository-execution-api.md`](contracts/repository-execution-api.md) defines pagination, DTO projections, safe errors and not-found behavior; [`contracts/repository-dashboard.md`](contracts/repository-dashboard.md) defines UI states. |
| IV–V. Provider/security | Credential and instance validation precede GitLab access; the mining GitLab port returns normalized values; only safe failures leave infrastructure; credentials are call-local. |
| VI–VIII. History/lifecycle/observability | Snapshot remains authoritative; RepositoryExecution has explicit lifecycle; scope failures have a distinct aggregate field; no fake completion/progress is generated. |
| IX–X. Migrations/tests | Versioned migration with uniqueness/check constraints; quickstart and test plan include PostgreSQL-specific verification only when PostgreSQL is actually available. |
| XI–XII. UX/simplicity | Dashboard reuses Feature 007, an accessible semantic list/table, existing states, and no chart or dependency addition. |

**Gate result**: Pass. The partial-scope aggregate fields and minimal RepositoryExecution summary persistence are required to meet the clarified status/counter and factual summary contract; neither duplicates the execution read model nor adds Finding persistence.

## Complexity Tracking

No constitution violations or complexity exceptions are proposed.
