# Implementation Plan: Monitoring Configuration CRUD

**Branch**: `002-monitoring-configuration-crud` | **Date**: 2026-09-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification at `/specs/002-monitoring-configuration-crud/spec.md`

## Summary

Deliver the first persisted Monitoring Configuration lifecycle across the existing React frontend
and a new Python API. The frontend extends Feature 001's Monitoring Configurations area and keeps
its shell, theme, shared visual components, and centralized router. A versioned FastAPI API maps
explicit Pydantic contracts to domain/application use cases; SQLAlchemy and Alembic persist
configurations and create-request receipts in PostgreSQL. Domain rules normalize and validate
inputs, new configurations are always created disabled, stale edits are rejected, and deletion
retires records without removing their historical reference data.

## Technical Context

**Language/Version**: Python 3.14.x (support Python 3.13 and 3.14); existing strict TypeScript frontend

**Primary Dependencies**: Existing React, TypeScript, Vite, Material UI, React Router; FastAPI,
Pydantic 2, SQLAlchemy 2, Alembic, Psycopg 3, pytest, HTTPX, Vitest, Testing Library

**Storage**: PostgreSQL 16 or later; Alembic-managed schema; UTC-aware timestamps

**Testing**: pytest domain/application/API/integration tests against PostgreSQL; FastAPI TestClient
and HTTPX; existing Vitest and Testing Library frontend suite; migration upgrade/downgrade checks

**Target Platform**: Linux backend deployment; local development on supported Python platforms;
browser frontend uses the Feature 001 browser policy

**Project Type**: Existing React web frontend plus a separately packaged Python web API

**Performance Goals**: No feature-specific latency or throughput targets are specified. Avoid
blocking work in the browser. The expected initial collection volume is small to moderate; the
listing endpoint may return the full active collection. Pagination is intentionally deferred and
must be reconsidered when real usage or measured response size demonstrates a need. Do not
introduce arbitrary hard limits in this feature or specialized search indexes for the initial
volume.

**Constraints**: Preserve Feature 001 shell and shared patterns; version the public API at `/api/v1`;
backend is authoritative for validation; creation always sets `enabled=false`; enable/disable is a
post-creation action; optimistic concurrency rejects stale edits; retries use durable create
idempotency; retired rows remain available for future history; no GitLab access, credentials,
repository selection, scheduling, mining, execution, analytics, auth, or authorization

**Scale/Scope**: The initial expected volume is small to moderate. The listing endpoint may return
the full active collection; pagination is intentionally deferred and must be reconsidered when real
usage or measured response size demonstrates a need. Do not introduce arbitrary hard limits in this
feature. Caching, background processing, and specialized search indexes are also deferred until a
measured requirement justifies them.

## Constitution Check

*GATE: Pass before Phase 0 research; re-checked after Phase 1 design.*

| Principle | Plan evidence | Result |
|---|---|---|
| I. Clean Architecture and Responsibility Boundaries | Domain is framework-independent; application owns use cases and ports; API and SQLAlchemy are outer adapters; React is a separate client. | PASS |
| II. Domain-Centered Business Rules | Name/URL normalization, create-disabled default, lifecycle, and no-op semantics have one domain/application authority. Frontend validation is advisory presentation feedback; server validates every request. | PASS |
| III. Explicit, Versionable Contracts | `/api/v1` request/response/error schemas are documented independently; OpenAPI is generated from explicit Pydantic response contracts; breaking changes require a new API version. | PASS |
| IV. Abstracted External Integrations | No GitLab integration is introduced. PostgreSQL access is behind the application repository port. | PASS |
| V. Secure by Construction | No credentials are accepted or stored. Database URLs use environment/secret configuration, are redacted from errors, and are never sent to the frontend. | PASS |
| VI. Immutable and Reproducible Execution History | Soft deletion preserves configuration identity and values; no execution history is added. Future history will snapshot configuration values and will not depend on active-list membership. | PASS |
| VII. One Controlled Mining Pipeline | No scheduler or mining pipeline exists in scope. Enable/disable changes availability only and never trigger work. | PASS |
| VIII. Observable Execution Lifecycle | No mining execution is implemented; CRUD failures are returned as safe structured errors and logged without credentials or internal traces in responses. | PASS |
| IX. Migration-Managed Persistence | All schema creation and changes are represented by reviewed Alembic revisions; runtime metadata creation is prohibited. | PASS |
| X. Risk-Based Automated Verification | Domain, use-case, PostgreSQL repository, migration, idempotency, stale-update, API, and critical frontend flows have automated coverage. | PASS |
| XI. Deliberate, Reusable User Experience | Existing Feature 001 components express loading, empty, error, validation, success, disabled, and status behavior accessibly. | PASS |
| XII. Incremental Simplicity and Justified Dependencies | Backend dependencies are limited to the requested stack and test tools. One idempotency receipt record is justified by the accepted retry contract; no general framework or global state library is added. | PASS |

No constitutional violation requires an exception.

## Project Structure

### Documentation (this feature)

```text
specs/002-monitoring-configuration-crud/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- api-v1.md
`-- tasks.md                 # Produced later by $speckit-tasks
```

### Source Code (repository root)

```text
backend/
|-- pyproject.toml
|-- alembic.ini
|-- alembic/
|   |-- env.py
|   `-- versions/
|-- app/
|   |-- domain/
|   |   |-- monitoring_configuration.py
|   |   `-- errors.py
|   |-- application/
|   |   |-- ports/
|   |   |   |-- monitoring_configuration_repository.py
|   |   |   `-- create_request_store.py
|   |   `-- use_cases/
|   |       |-- create_monitoring_configuration.py
|   |       |-- list_monitoring_configurations.py
|   |       |-- get_monitoring_configuration.py
|   |       |-- update_monitoring_configuration.py
|   |       `-- retire_monitoring_configuration.py
|   |-- infrastructure/
|   |   `-- database/
|   |       |-- session.py
|   |       |-- models.py
|   |       `-- sqlalchemy_repositories.py
|   `-- api/
|       |-- main.py
|       |-- dependencies.py
|       |-- errors.py
|       `-- v1/
|           |-- schemas.py
|           `-- monitoring_configurations.py
`-- tests/
    |-- unit/domain/
    |-- unit/application/
    |-- integration/
    `-- api/

src/                                      # Feature 001 frontend; retain root location
|-- app/routes/routeConfig.tsx             # Add the edit route; keep centralized routing
|-- features/monitoring-configurations/
|   |-- api/monitoringConfigurationsApi.ts
|   |-- components/MonitoringConfigurationForm.tsx
|   |-- components/DeleteConfigurationDialog.tsx
|   |-- model/monitoringConfiguration.ts
|   `-- pages/
|       |-- MonitoringConfigurationsPage.tsx
|       |-- NewMonitoringConfigurationPage.tsx
|       |-- MonitoringConfigurationDetailsPage.tsx
|       `-- EditMonitoringConfigurationPage.tsx
`-- test/features/monitoring-configurations/
    |-- listing.test.tsx
    |-- create.test.tsx
    |-- details-edit.test.tsx
    `-- lifecycle.test.tsx
```

**Structure Decision**: Keep the existing frontend at repository-root `src/` and add a separate
`backend/` Python package. Within the backend, `domain` has no framework imports, `application`
defines use cases and repository/request-store ports, `infrastructure` implements PostgreSQL access,
and `api` translates HTTP/Pydantic models. The application layer owns transaction orchestration;
routes do not open commits or contain business rules. Feature components and API mapping stay under
the existing Monitoring Configurations area. Shared UI changes are avoided unless a genuinely
generic behavior is missing from Feature 001.

## Backend Architecture

- The domain entity uses Python value types and contains no SQLAlchemy, Pydantic, FastAPI, or
  PostgreSQL imports. Factory/update operations enforce trimmed non-empty names, absolute HTTP(S)
  URLs with a host, optional-description normalization, creation disabled, and actual-change-only
  `updated_at` behavior.
- Application use cases coordinate domain objects and ports for create, list/search, get, update,
  enable/disable, and retire. All writes run in a short transaction; create and its idempotency
  receipt commit atomically.
- Application ports expose only the operations needed by use cases. SQLAlchemy repository
  implementations map between ORM rows and domain entities. The API never returns ORM rows.
- Use synchronous SQLAlchemy 2 sessions scoped to one request. FastAPI synchronous route handlers
  use a yielding dependency to acquire/close sessions; the application/use-case boundary commits
  or rolls back mutations explicitly.
- Repository queries for normal listing/detail/update operate only on non-retired configurations.
  No physical delete or cascade is used.
- URL/name business validation has one domain implementation. Pydantic validates request shape and
  serializes contracts; API handlers map domain validation outcomes to field errors. Frontend native
  input constraints and inline hints improve feedback, while the backend remains authoritative.

## Persistence and Migrations

- Use SQLAlchemy 2 declarative mappings and Psycopg 3. Persist identifiers as UUIDs, date/time
  values as timezone-aware instants, and use the PostgreSQL-supported type mappings without
  requiring extensions.
- `monitoring_configurations` stores the specified values plus internal `revision` for stale-write
  detection and nullable `retired_at` for logical deletion. `enabled` is `NOT NULL DEFAULT FALSE`;
  the domain/use-case also explicitly constructs new configurations disabled so callers cannot
  override the creation default.
- `create_request_receipts` stores a unique create-request key, canonical normalized request
  fingerprint, creation time, and immutable response snapshot. This small extra table is required
  so same-key retries remain race-safe, durable, and return the original result even if the
  configuration later changes. A different payload with the same key returns conflict.
- Configuration names and GitLab URLs are not unique. UUID primary-key indexes are sufficient for
  the expected first release. Search trims the query, uses case-insensitive substring matching,
  treats an empty/whitespace-only query as no filter, and treats `%`, `_`, `*`, and other
  wildcard-like characters literally. Use a parameterized predicate; if SQL `LIKE`/`ILIKE` is used,
  escape wildcard and escape characters. No specialized PostgreSQL index is justified yet.
- Alembic revisions are the sole schema-change mechanism. Generate candidates only as a starting
  point, review the full upgrade/downgrade manually, test both directions on a disposable test
  database, and run schema drift checks in CI. Application startup never calls `create_all()`.
- Database connection strings and deployment credentials are loaded from environment/secret
  configuration. Checked-in examples contain placeholders only.

## API Contract Strategy

- Expose `/api/v1/monitoring-configurations` collection and item operations as documented in
  [contracts/api-v1.md](./contracts/api-v1.md).
- Use explicit Pydantic request/response types and response models; OpenAPI output is reviewed
  against the versioned contract. Persistence field names and ORM classes are not public API
  schemas.
- The backend generates the Monitoring Configuration UUID; the create body contains only name,
  description, and `gitlab_url`, rejects a client-provided configuration `id`, and always creates
  disabled. The generated ID is returned in the `201` response and `Location`. An optional
  `Idempotency-Key` is a separate opaque retry token, not a resource identifier; if supplied it must
  be 1–128 visible ASCII characters with no whitespace/control characters. Same key/same normalized
  payload replays the original response snapshot; same key/different payload yields `409`; a new key
  permits identical field values as a separate configuration. Without the optional key, each
  accepted POST is a separate create intent.
- Responses include an opaque `version` token and an `ETag`. `PUT` requires `If-Match`; missing
  precondition yields `428`, stale revision yields `412`, and a successful actual change increments
  revision and `updated_at`. An unchanged request is successful without advancing either value.
- Use `GET ?search=` for optional name filtering. Empty search returns all active records; response
  is a simple `items` array with no pagination metadata until scale requires it.
- Use `DELETE` for the UI-confirmed logical retirement; return `204` on success. Active detail and
  updates of retired/unknown IDs return `404`.
- Return RFC 9457-style Problem Details with a stable `errors` extension for field-specific
  validation. Map validation to `422`, missing active resource to `404`, idempotency payload
  mismatch to `409`, stale `If-Match` to `412`, and missing `If-Match` to `428`. Internal database
  failures return a generic `500` problem; never expose exception text or stack traces.

## Frontend Integration Strategy

- Replace the Feature 001 list fixture with API-backed loading and retryable error states. Empty
  state links to the existing create route; search sends a trimmed query; each row links to details
  and edit and exposes enable/disable/delete actions supported by the contract.
- Change the new-configuration page from the visual-only multi-step wizard to a single general
  information form for name, optional description, and GitLab instance URL. It creates the record
  disabled; no GitLab connection, repository, or scheduling steps are navigable.
- Add `/monitoring-configurations/:id/edit` in centralized route configuration. The details page
  reads persisted values and exposes edit, enable/disable, and confirmed delete actions. Existing
  details placeholder is replaced; future sections remain labeled placeholders only if useful.
- A shared feature API module uses native `fetch`, configured by `VITE_API_BASE_URL`, and maps
  Problem Details to field feedback and existing `ErrorState`/alerts. It aborts superseded list
  searches and does not write configuration data or request keys to browser storage.
- On edit, preserve the response `ETag`; send `If-Match`. A `412` keeps the local edit intact and
  presents reload/reapply guidance. Ordinary creation does not ask for or send a configuration ID.
  When retry replay is desired, reuse the optional `Idempotency-Key` for that intent; a distinct
  intent uses a new key. Keep request tokens in transient component/request memory only.
- Configure backend CORS with an explicit environment-provided origin allowlist for the Vite
  development origin and deployed frontend origin; expose only required `ETag` and `Location`
  headers. No wildcard origins with credentials.
- Keep labels, breadcrumb hierarchy, status badges, spacing, mobile drawer, and global layout from
  Feature 001. Use existing `PageHeader`, `ContentCard`, `StatusBadge`, `LoadingState`,
  `EmptyState`, `ErrorState`, and `FeedbackMessage`; do not fork them.

## Validation Strategy

- Unit-test domain normalization, URL rules, disabled creation, status transitions, no-op timestamps,
  immutable identity/creation date, retirement behavior, and stale revisions.
- Unit-test application use cases with in-memory port substitutes, including idempotency replay,
  key/payload conflict, atomic write expectations, and no duplicate create outcomes.
- Integration-test SQLAlchemy repositories and Alembic against PostgreSQL, including UTC-aware
  round trips, retired-row filtering, concurrent stale updates, uniqueness of idempotency keys, and
  migration upgrade/downgrade. SQLite is not used to stand in for PostgreSQL behavior.
- API tests cover all methods/status codes, Pydantic/OpenAPI contract shapes, field errors,
  Problem Details, `If-Match`/ETag behavior, idempotency replay, 404s, and generic unexpected errors.
- Frontend behavior tests cover listing success/empty/loading/error, search, create and backend
  validation errors, disabled-by-default creation, details, edits and conflicts, enable/disable,
  deletion confirmation/cancel/success/failure, and API unavailable feedback.
- Run the existing Feature 001 suite unchanged as regression coverage, then frontend tests/build,
  backend tests, Alembic migration checks, and the end-to-end quickstart flow.

## Deferred Functionality

GitLab credentials, token storage, GitLab connectivity, group/repository discovery and selection,
scheduling, scheduler execution, mining, execution history or results, dashboard analytics,
findings, authentication, authorization, restoration of retired configurations, audit-event feeds,
bulk operations, pagination, caching, and specialized search indexes remain out of scope.

## Technical Trade-offs

- Synchronous SQLAlchemy keeps the first API's transaction model straightforward and is sufficient
  for low-volume CRUD. Async database access can be introduced later only with measured I/O needs.
- PostgreSQL is the required production database, but SQLAlchemy generic UUID, Boolean, text, and
  timezone-aware datetime mappings avoid unnecessary vendor-only schema behavior.
- The idempotency receipt table adds one infrastructure entity, justified because the accepted
  contract requires atomic duplicate prevention and replay after lost responses; in-memory keys or
  value-based deduplication would be incorrect.
- Soft deletion preserves future historical associations but means ordinary endpoints cannot
  restore or inspect retired configurations. A later retention policy must preserve execution
  snapshots as required by the constitution.
- Optimistic versioning prevents lost edits without holding locks across user interaction. Clients
  receive a conflict and can reload/reapply; last-write-wins is rejected by the specification.
- No frontend query/state library is added. Feature-local request state and the existing shared UI
  primitives are enough for this bounded CRUD flow.

## Complexity Tracking

| Added element | Immediate purpose | Why the simpler alternative is insufficient |
|---|---|---|
| `create_request_receipts` persistence record | Durable, atomic replay when a client opts into create retry idempotency with an optional request key. | An in-memory map loses retry identity on restart and cannot arbitrate concurrent keyed duplicates; requiring this key for ordinary creation would conflate retry identity with the backend-owned resource ID. |
| Application repository ports | Keep business operations independent from SQLAlchemy and PostgreSQL while enabling domain/use-case tests. | Direct ORM access from API handlers would couple transport, business decisions, and persistence. |

No constitutional violation requires an exception; the two elements above are direct requirements, not speculative platform abstractions.
