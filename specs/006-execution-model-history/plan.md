# Implementation Plan: Execution Model and History

**Branch**: `006-execution-model-history` | **Date**: 2026-09-29 | **Spec**: [spec.md](spec.md)

## Summary

Introduce a PostgreSQL-backed `MiningExecution` aggregate, versioned immutable configuration/scope snapshots, an application-owned lifecycle service, and manual execution orchestration. A manual request is eligible for any existing non-retired configuration with no non-stale active execution after request-time reconciliation, regardless of configuration or schedule enabled state. Its successful synchronous API flow persists `pending`, advances through `running`, and persists `completed` before returning HTTP 201. A controlled orchestration failure is finalized as `failed` with bounded safe error metadata. All mining counters stay zero; no repository processing or findings are created. History is exposed through global and configuration-specific lists and safe detail DTOs, with React replacing the existing execution placeholders.

## Technical Context

**Language/Version**: Python (repository-supported version) and TypeScript (repository-supported version).

**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL; React, Vite, Material UI, React Router. No new runtime dependency is required.

**Storage**: PostgreSQL. Execution rows and a typed JSONB snapshot are migration-managed; snapshot data is independent of mutable scope/schedule child rows.

**Testing**: Backend pytest unit/API tests and PostgreSQL integration tests using the existing `TEST_DATABASE_URL`/`pg_uow_factory`; frontend existing Vitest and Testing Library suites. PostgreSQL concurrency claims require execution of the PostgreSQL integration suite.

**Target Platform**: Existing Python API and browser frontend deployment.

**Project Type**: Full-stack web application with Clean Architecture backend and React frontend.

**Performance Goals**: No repository/provider work on the manual execution path. History reads use indexed filters and bounded pagination; no new numerical latency target is introduced.

**Constraints**: Keep one active execution per configuration under concurrent requests; history must survive configuration retirement and remain readable without mutable child rows; snapshots and API responses must exclude credential material; lifecycle transitions are application-controlled; PostgreSQL remains authoritative for concurrency. The Feature 006 orchestration path must finish without leaving an active record and must not imply mining occurred.

**Scale/Scope**: One execution per user-requested manual orchestration, with global and per-configuration history. The API uses bounded pagination rather than an unbounded global result. Stale Feature 006 executions are reconciled only when a manual request arrives; no background reconciliation job, scheduler polling/dispatch, repository processing, findings, dashboard analytics, or execution worker is introduced.

## Constitution Check

| Principle | Gate and design response |
|---|---|
| I. Clean Architecture | Pass. Domain owns execution state/snapshot value rules; application owns creation, lifecycle, listing orchestration; infrastructure owns SQLAlchemy/PostgreSQL; API maps explicit DTOs; frontend consumes the API. |
| II. Domain-Centered Business Rules | Pass. Eligibility, transitions, timestamp invariants, counters, and snapshot validation are not implemented in controllers or UI. |
| III. Explicit, Versionable Contracts | Pass. Versioned API contract defines request, filters, safe DTOs, ordering, pagination, errors, and manual-only creation. |
| IV. Abstracted External Integrations | Pass. Execution creation does not call GitLab. Existing GitLab ports are not extended for this feature. |
| V. Secure by Construction | Pass. Snapshot schema excludes all token/ciphertext fields; public response uses a projection, not raw JSONB. Error fields are bounded and safe. |
| VI. Immutable and Reproducible History | Pass. Snapshot is copied at creation into a versioned, validated JSONB value; it has no dependencies on mutable scope/schedule child rows. |
| VII. One Controlled Mining Pipeline | Pass for this pre-mining stage. Application prevents concurrent active rows and idempotency keys protect retries. Feature 006 does not create a second mining pipeline; future processing reuses the lifecycle. |
| VIII. Observable Execution Lifecycle | Pass within scope. Lifecycle timestamps/status and safe errors are queryable. The orchestration-only path deterministically finishes; no progress or repository metrics are fabricated. |
| IX. Migration-Managed Persistence | Pass. Add an Alembic migration; PostgreSQL partial unique index and checks encode durable constraints. |
| X. Risk-Based Automated Verification | Pass. Unit, API, snapshot secrecy/immutability, and PostgreSQL concurrent request tests are required; tests are not reported as PostgreSQL-validated unless they run against PostgreSQL. |
| XI. Deliberate, Reusable User Experience | Pass. Existing application shell, feedback states, status badges, accessible tables, semantic sections, and keyboard patterns are reused. |
| XII. Incremental Simplicity | Pass. One versioned snapshot JSONB document is appropriate for a write-once historical value. No mining, scheduler, websocket, or new dependency is added. |

No constitutional exception is required.

## Project Structure

### Documentation (this feature)

```text
specs/006-execution-model-history/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── api-v1.md
└── tasks.md                 # Produced later by $speckit-tasks
```

### Source Code

```text
backend/
├── app/domain/
│   ├── entities/mining_execution.py
│   └── entities/execution_snapshot.py
├── app/application/
│   ├── ports/mining_execution_repository.py
│   └── use_cases/                 # create, transition, list, get execution
├── app/infrastructure/database/
│   ├── models.py
│   ├── sqlalchemy_repositories.py
│   ├── session.py
│   └── unit_of_work.py
├── app/api/v1/
│   ├── executions.py              # routes and DTO mapping only
│   └── execution_schemas.py       # execution request/response DTOs
├── alembic/versions/
│   └── 0005_mining_executions.py  # next revision after 0004
└── tests/
    ├── unit/
    ├── api/
    └── integration/               # PostgreSQL lifecycle/concurrency/history tests
src/features/executions/
├── api/
├── hooks/
├── types/
└── pages/                    # global list and detail
src/features/monitoring-configurations/
└── pages/                    # manual action and configuration history
src/shared/types/
└── presentation.ts           # shared execution status presentation if appropriate
src/test/features/
└── executions/               # journey, list, detail, conflict, accessibility tests
```

**Structure Decision**: Extend existing backend `app/domain`, `app/application`, `app/infrastructure`, and `app/api` boundaries and current frontend feature modules. Existing routes already reserve `/executions`, `/executions/:id`, and `/monitoring-configurations/:id/executions`; Feature 006 replaces the placeholder pages without redesigning the application shell.

The domain, persistence, API, and frontend wire unions use the exact status strings in the contract, including `partially_completed`. The existing visual `StatusBadge` may receive a presentation-only mapping to its `partially-completed` token; that is not a second execution status contract.

## Design Decisions

### Aggregate and lifecycle

`MiningExecution` is the persistence aggregate root. Its factory assigns UUID, trigger, `pending`, UTC `created_at`, zero counters, and a validated snapshot. The application lifecycle service is the only writer of status and lifecycle timestamps. Every persisted lifecycle mutation must verify the expected current source status using a row lock and conditional update within a transaction; no execution revision field is introduced. Thus `pending → running` requires persisted `pending`, `running → completed` requires persisted `running`, and `running → failed` requires persisted `running`. Stale reconciliation locks and re-reads the active row, confirms it is still `pending` or `running` and still stale, then conditionally transitions it to failed atomically. It permits `pending → failed` for a controlled failure before start or stale reconciliation, and `running → completed | partially_completed | failed`; setting `running` assigns `started_at` once, a final transition assigns `completed_at` once, and final states are immutable. A failure from pending leaves `started_at` null; a failure from running preserves its start time. Feature 006's successful sequence is pending creation, normal transition to running, then completed after its no-mining work succeeds. Controlled failure in either active state transitions to failed with normalized bounded error metadata.

All lifecycle work uses an injected/reference clock; domain tests use fixed UTC instants. `duration` is derived from start and completion instants and is absent until both exist. API response serialization does not assign lifecycle timestamps.

### Snapshot and persistence

Persist one schema-versioned JSONB snapshot per execution, validated to an explicit `ExecutionSnapshotV1` model before serialization and after loading. The snapshot contains configuration ID/name/enabled state, normalized GitLab URL, configuration revision, scope version where available, selected group and repository IDs with safe display metadata and their internal instance fingerprint, trigger type, and optional future schedule context. The scope arrays represent selection intent; groups remain group rules and are never expanded. Snapshot construction reads configuration and scope from the same application unit of work and does not query GitLab, credentials, or schedule for manual requests.

JSONB is chosen because the snapshot is immutable, consumed as a whole, and versioned at the application boundary; relational scope remains normalized for current editing. A typed schema avoids arbitrary dictionaries. Version 1 is internal persistence metadata, not exposed in the public DTO. Snapshot projection to API detail deliberately selects only approved display fields. There is no credential ID, credential revision, raw/decrypted token, encrypted token, or credential validation material in the snapshot.

### One-active-execution concurrency

Use two complementary PostgreSQL controls:

1. Lock the owning Monitoring Configuration row with PostgreSQL `SELECT ... FOR UPDATE NOWAIT` for the short creation transaction. If another request currently owns that row lock, normalize lock contention to HTTP 409 without exposing SQL details. After acquiring the row lock, re-read any committed `pending`/`running` execution before deciding whether to conflict or reconcile it.
2. Lock and re-read the candidate active execution row before reconciliation, and make lifecycle persistence conditional on its expected current status. If the original orchestration finalizes first, reconciliation sees a final row and does not rewrite it; the new request re-evaluates active work and proceeds if none remains. If reconciliation wins, the original finalization cannot overwrite `failed`. A partial unique index on `monitoring_configuration_id` where status is `pending` or `running` remains the final invariant and protects all insert/update paths. Translate its violation to a safe HTTP 409 as a defensive race guard. This strategy uses row locks, expected-status guards, transaction boundaries, and database-backed active uniqueness; it does not add an execution revision field.

Acquire the lock before reading mutable configuration/scope context and hold it across the short initial creation transaction. Use a transaction-level repeatable-read snapshot so configuration, scope version, and selected rows are captured consistently. Configure `EXECUTION_STALENESS_THRESHOLD_SECONDS` with default `300`; reject non-finite or non-positive values instead of silently falling back. For `pending`, measure age from `created_at`; for `running`, measure from `started_at`. An execution is stale only when elapsed time is strictly greater than the threshold, evaluated against an explicit UTC reference instant.

Within the locked transaction, a non-stale active execution yields the existing safe HTTP 409. A stale active execution is reconciled through the application lifecycle service to `failed`, with `completed_at` set to the reference instant, `started_at` preserved according to state, `error_code=execution_interrupted`, and a curated summary that the previous execution did not complete. Snapshot and counters are unchanged. For a distinct manual command, stale reconciliation and insertion of the replacement `pending` execution occur atomically in the same transaction; the stale row becomes final before the new active row is inserted, preserving the partial unique index. Failure in either step rolls both changes back. The owner-row lock serializes concurrent requests: only one request can reconcile/create, while a later contender sees the fresh active row or receives normalized lock conflict, so two active executions cannot be created.

Persist the new `pending` execution, snapshot, and optional idempotency receipt, then commit before orchestration; the active partial index makes this in-progress record visible to competing requests. In a second application-controlled lifecycle operation, transition to running, perform only the local no-mining orchestration, then commit completed. On a controlled orchestration error, transition to failed from running (or from pending if start did not succeed), persist only safe normalized error data and commit the final state. A PostgreSQL integration test covers fresh conflict, stale pending/running reconciliation, and concurrent requests racing to reconcile/create. PostgreSQL integration execution is required before claiming these concurrency invariants were runtime-verified.

If the process terminates after pending has committed but before a final transition can be stored, a subsequent manual request can reconcile it once the configured threshold is exceeded; no background recovery process is added. A stale record can remain until another manual request arrives, but it cannot permanently block future requests. Controlled application/orchestration exceptions are finalized as failed. A database outage that prevents persisting a final transition cannot be converted into a durable failed record; its API error remains generic and safe.

### Idempotency

Reuse the existing optional `Idempotency-Key` command pattern for POST manual execution, scoped/fingerprinted by configuration ID and the manual operation. A repeated key with the same request never creates another execution; after the original reaches a final state, replay returns its current final resource. If the original is still pending/running and non-stale, replay returns a safe 409 in-progress conflict. If it is stale, request-time reconciliation may finalize that same resource; replay returns the failed resource and does not create another row. Only a distinct command/key can reconcile a stale active record and create a replacement in the same transaction. A repeated key with a different fingerprint returns the established idempotency conflict. The row lock and partial unique index independently protect overlapping distinct requests. No client-selected trigger or request body is accepted.

### Retention and migration

Add a `mining_executions` table with UUID primary key, non-null configuration FK using `ON DELETE RESTRICT`, trigger/status strings constrained to supported values, UTC timestamps, nonnegative zero-default counters, bounded safe error code/summary, JSONB snapshot, and creation/filter indexes. Include a partial unique active index and lifecycle timestamp/status checks where expressible. Existing configuration lifecycle is soft retirement, so retirement leaves the configuration and execution FK intact; no physical configuration delete is exposed. RESTRICT protects history if a physical-delete path is ever attempted. Execution rows never FK to selected scope or schedule child rows.

### API and read semantics

`POST /api/v1/monitoring-configurations/{configurationId}/executions` creates manual execution only and returns a safe DTO. Global `GET /api/v1/executions`, configuration-scoped `GET`, and detail `GET` use dedicated response models. Lists are bounded and ordered by `created_at DESC, id DESC`; filters are status, trigger type, and configuration ID on the global endpoint. The public API does not expose generic transition/status mutation or raw snapshot JSON. The response distinguishes completed orchestration from mining and makes zero counters truthful.

Missing/retired configuration uses normalized 404; a non-stale active execution and idempotency conflict use normalized 409; unexpected failures use generic 500. Public errors never contain persistence exception text. No arbitrary status patch route is created.

### Frontend integration

Replace Feature 001 placeholder content in the existing global history, per-configuration history, and execution detail pages. Add a clearly named manual action and history link to configuration details. A successful request navigates to the execution detail. HTTP 409 shows accessible conflict feedback; no automatic retry is performed. Lists use existing semantic Material UI tables/status badges and loading/empty/error states. Detail includes snapshot display metadata, lifecycle, duration, counters, and an explicit statement that Feature 006 orchestration completed but repository mining has not occurred. No fake charts or findings are displayed.

## Constitution Check (Post-Design)

All pre-design gates remain satisfied. Design adds no external provider calls, no new dependency, no mutable snapshot joins, no public status mutation, no unbounded history response, and no claim of PostgreSQL concurrency validation absent an executed database test. The PostgreSQL owner-row lock serializes overlapping requests and the partial unique index gives the database final authority over active uniqueness, while a typed snapshot and DTO projection maintain the secret boundary. No unresolved design clarification remains.

## Implementation Sequencing Notes

The implementation tasks should preserve these dependencies: domain lifecycle/snapshot types before persistence; Alembic/model/repository and PostgreSQL constraint before create orchestration; normalized error translation before API concurrency tests; dedicated API DTOs before frontend API/types; detail/list placeholders and manual action before complete frontend journeys. Generate dependency-ordered tasks with `$speckit-tasks`; task generation is intentionally not part of this plan.

## Complexity Tracking

No constitution violations or extra runtime dependencies.
