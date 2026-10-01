# Implementation Plan: GitLab Scope Selection

**Branch**: `004-gitlab-scope-selection` | **Date**: 2026-09-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification at `specs/004-gitlab-scope-selection/spec.md`; implementation decisions supplied with `$speckit-plan`.

## Summary

Extend Feature 003's GitLab connection port and HTTP client with normalized group, subgroup, and direct-project discovery, using complete pagination only for the root list or a group being expanded. Persist explicit group and project rules in normalized PostgreSQL tables, keyed by stable GitLab IDs and an internal fingerprint of the originating GitLab instance. Store a separate scope version and use the existing `ETag`/`If-Match` optimistic concurrency convention. A selected group remains a dynamic rule; effective repository resolution deduplicates coverage while preserving redundant explicit selections as user intent. Add config-scoped discovery and scope APIs plus a dedicated React tree page, retaining stale-instance rules until users remove them.

## Technical Context

**Language/Version**: Python 3.13–3.14 backend; strict TypeScript frontend; Node.js 26.x development runtime

**Primary Dependencies**: Existing FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, psycopg 3, PostgreSQL, HTTPX; React, Vite, Material UI, React Router, Vitest, and Testing Library. No new runtime dependency is planned.

**Storage**: PostgreSQL 16+ using Alembic migrations. Existing configurations have a valid empty scope; scope rows are created only when a scope is first saved.

**Testing**: pytest unit/application/API tests, PostgreSQL integration and migration tests, HTTPX `MockTransport`, Vitest/Testing Library, TypeScript build, and production Vite build.

**Target Platform**: Existing Linux/container backend and browser frontend; GitLab SaaS and compatible self-managed GitLab using REST API v4.

**Project Type**: Existing React web application plus separate Python Clean Architecture API.

**Performance Goals**: Do not materialize the complete GitLab hierarchy before navigation is available. The initial load retrieves the root-level group set only and makes it interactive. Expanding one group requests only its direct subgroups and directly owned projects; unrelated branches and descendant pages are not fetched recursively. The deterministic 1,000-entity check distributes entities across multiple root groups and nested branches, asserts that navigation is available after root load, and asserts that expanding one group leaves unrelated branches unloaded. The backend may resolve every page for the specific root list or expanded group's direct children before returning that node; it must not fetch descendants that were not requested. Streaming or finer-grained pagination within a single requested node, including a group with thousands of direct children, is deferred until measured need. No fixed latency benchmark is specified.

**Constraints**: Preserve the Feature 001 shell and Feature 003 connection boundary. Use the saved credential only; never expose it or raw GitLab payloads. Preserve Feature 003's URL normalization, TLS verification, redirect prohibition, finite HTTPX timeouts, and no-retry behavior. Keep selected group rules dynamic and do not resolve their descendants while saving. Retain stale-instance rules and mark them stale; do not send old IDs to the new instance. No mining, cloning, schedule, execution, or finding functionality.

**Scale/Scope**: One scope per Monitoring Configuration, containing zero or more explicit group rules and repository rules. Hierarchy data is fetched per root/expanded node and held only in the active browser editing session; no instance-wide hierarchy materialization or persistent hierarchy cache.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate evidence | Result |
|---|---|---|
| I. Clean Architecture and Responsibility Boundaries | Domain defines scope and normalized hierarchy concepts; application owns discovery, reconciliation, scope save and coverage policy; HTTPX, SQLAlchemy and React remain outer adapters. | PASS |
| II. Domain-Centered Business Rules | Group intent, explicit repository intent, duplicate effective coverage, stale-instance identity and concurrency have one application/domain authority. Tree partial state is derived presentation only. | PASS |
| III. Explicit, Versionable Contracts | Dedicated Pydantic request/response schemas document discovery, read, replacement, ETag and safe error behavior under `/api/v1`. Provider DTOs do not cross the adapter. | PASS |
| IV. Abstracted External Integrations | Extend the application-owned Feature 003 GitLab client protocol; keep REST paths, pagination headers and provider payload mapping in infrastructure. | PASS |
| V. Secure by Construction | Decrypt the saved credential only for a scoped outbound call, send it only in `PRIVATE-TOKEN`, never log or return it, and expose neither instance fingerprints nor raw provider errors. | PASS |
| VI. Immutable and Reproducible Execution History | No execution data is created or changed. Scope remains editable configuration intent for future work; execution snapshots remain deferred. | PASS |
| VII. One Controlled Mining Pipeline | No pipeline, scheduler or repository work is added. | PASS |
| VIII. Observable Execution Lifecycle | No execution lifecycle is added. Discovery and persistence failures return stable safe categories and retain prior scope/drafts. | PASS |
| IX. Migration-Managed Persistence | Add one reversible Alembic revision for scope version and selection records; do not use runtime schema creation or SQLite substitution. | PASS |
| X. Risk-Based Automated Verification | Cover scope semantics, pagination, provider failures, optimistic concurrency, stale URL/credential reconciliation, API redaction, PostgreSQL migration and tree behavior with controlled GitLab responses. | PASS |
| XI. Deliberate, Reusable User Experience | Reuse Feature 001 shell and tree visuals, extend their limited static primitives with controlled accessible behavior, and design loading/empty/error/unavailable/unsaved states. | PASS |
| XII. Incremental Simplicity and Justified Dependencies | Reuse the existing HTTP client, UoW, API client and shared components; introduce no new runtime dependency, external cache, search service or distributed lock. | PASS |

**Pre-design gate**: PASS. The supplied specification and implementation directions resolve product behavior. Research confirms the provider API semantics and existing project boundaries.

## Architecture and Decisions

### Scope persistence and domain semantics

- Add `MiningScope`, `SelectedGitLabGroup`, and `SelectedGitLabRepository` domain concepts. Keep hierarchy discovery nodes/results separate from persisted selection rules. Scope objects contain stable provider IDs, safe display metadata, and an internal originating-instance identity; tree expansion, search, loading, and partial selection are not persisted.
- Use a lazy scope-state row for independent scope concurrency versioning and two normalized child tables: selected groups and selected repositories. Each selection has an opaque UUID for safe round-tripping/removal, a stable GitLab numeric ID, the internal instance fingerprint, and last-known display name/path plus parent-group ID where applicable. Unique constraints cover configuration + instance fingerprint + provider entity ID. The state row's primary key references the Monitoring Configuration with `ON DELETE CASCADE`; soft retirement retains scope rows under Feature 002 lifecycle behavior.
- A missing state row is an empty scope at virtual ETag version `0`. First save inserts version `1`; later successful scope saves increment the scope version. Saving an empty scope creates/retains a state row with no selection rows. The migration does not make credentials or scope mandatory for existing configurations.
- Reuse Feature 003's normalized URL identity/fingerprint helper. Persist only the internal SHA-256 fingerprint, never the raw originating URL; do not treat the digest as encryption. Compare each selection's stored fingerprint with the current configuration URL fingerprint. Different origins remain separate selections in one saved scope until explicit removal.
- Retain explicit redundant choices, including a selected repository under a selected group and a selected subgroup under a selected ancestor. This follows the specification's user-intent rule. For effective coverage, resolve against a candidate `(instance fingerprint, repository ID, ancestor group IDs)` set, include a repository if explicitly selected or covered by a current-origin selected group, and deduplicate by `(instance fingerprint, repository ID)`. Stale-origin rules never cover repositories on the current instance. Feature 004 defines and tests this policy without enumerating descendants during save or implementing mining.
- `If-Match` uses the scope ETag, independent from Monitoring Configuration's ETag so unrelated form edits do not invalidate scope drafts. A stale save returns HTTP 412 using the existing Feature 002 convention; missing precondition returns 428. Update version and replace all submitted group/project rows in one transaction.

### GitLab discovery and pagination

- Extend `GitLabConnectionClient` in `backend/app/domain/ports/gitlab_connection_client.py` with normalized operations for top-level groups, direct subgroups, direct group projects, and single-group/project lookup for save validation and reconciliation. Return domain-owned hierarchy results with IDs, name/path, parent IDs and entity type; use typed safe failure outcomes. Do not leak HTTPX responses, headers, or GitLab schemas.
- Extend `HttpGitLabConnectionClient` in `backend/app/infrastructure/gitlab/http_gitlab_connection_client.py`; retain Feature 003's URL builder, client timeouts, TLS, `PRIVATE-TOKEN`, no redirects, and normalized error policy. Send all requests with the configuration URL and decrypted saved credential. Do not add retries.
- Root request lists only top-level groups (`top_level_only=true`, `all_available=true`). Expanding a group fetches its visible direct subgroups and directly owned projects. The project request MUST explicitly set `include_subgroups=false` and `with_shared=false`; direct subgroups are represented as `group` nodes. Recurse by expanding each subgroup. This prevents recursive list overlap, avoids shared projects, and allows the tree to reflect the hierarchy.
- The adapter sets `per_page=100` and follows `X-Next-Page` until empty for each specifically requested list. It de-duplicates by `(type, GitLab ID)` and uses a stable ordering by node type then case-insensitive full path and ID. A failure on any page fails that node load as a whole; it never returns an apparently complete partial list. Root loading requests only root groups and exposes navigation once that root result is returned. Expanding a group requests only that group's direct subgroups and directly owned projects; it MUST NOT recursively request descendant groups or their projects. A group with thousands of direct children may wait for all pages of that requested node before its result returns; streaming or finer-grained per-node pagination is deferred until measured need.
- A group is expandable because it may contain direct children; expanding an empty group returns an explicit empty child set. Repository nodes are leaves. The normalized child response is a complete direct-child set and does not contain provider pagination tokens.

### Request flow, errors, and reconciliation

- Discovery first loads the active configuration and credential snapshot, decrypts the credential, then closes/rolls back the read transaction before any GitLab call. After all pages return, it rechecks the current URL identity and credential revision in a short read; changed configuration/credential returns safe `409 gitlab_connection_changed`. No transaction remains open during outbound HTTP.
- Saving newly chosen nodes validates structural IDs, resolves new entity details against the current GitLab credential/instance, and stores authoritative safe metadata. Existing rules round-trip by `selection_id`; a client cannot change the provider ID/type of an existing selection ID. Existing stale rules are preserved only when the user includes their IDs in the full desired selection payload. Omitting an unavailable/stale ID is the explicit user removal. New rules always bind to the current normalized instance fingerprint. Provider lookups finish and the connection snapshot is rechecked before the scope CAS transaction begins.
- `GET scope` returns every saved rule, current safe metadata when reconciliation succeeds, `available`, `unavailable`, `unresolved`, or `stale` status, and scope ETag. Current-origin entries are checked with targeted group/project detail operations using bounded concurrency; stale-origin entries are not queried against the active instance. 404/403 for a targeted item marks it unavailable; transport, rate limit, malformed response, or provider failure marks it unresolved and remains retryable. Status is derived at read time and is not persisted; refreshed display metadata may be stored without advancing the selection-set version. A failure never deletes a selection.
- Credential replacement/removal in Feature 003 does not mutate scope rows. Subsequent reads reconcile through the current saved credential. If no credential exists, saved rules and their metadata remain readable/removable; discovery and requests adding new IDs return safe `409 gitlab_credential_required`. A scope replacement containing only recognized existing selection IDs (or an empty set) is allowed without a credential so users can retain remaining rules or clear the scope.
- URL changes do not mutate stored fingerprints. Old entries are returned as stale and are not checked against the new host/path, including when IDs collide. New instance selections can coexist with stale rows; users remove old rows explicitly. A URL that normalizes to the same instance identity does not stale scope.
- Use existing RFC 9457 `ProblemDetails` shapes. Map config missing/retired to 404, missing credential to 409, invalid GitLab URL to 422, stale scope ETag to 412, and upstream timeout/unreachable/auth/rate-limit/unavailable/invalid-response outcomes to stable safe provider codes (504 for timeout, 503 for rate limit/unavailability, 502 for other upstream failures). For an inaccessible selected entity, return a successful scope read with `unavailable`; do not fail the entire read. Never include provider body/exception/token.

### API contracts

Implement the router module in `backend/app/api/v1/gitlab_scopes.py`, explicit schemas in `backend/app/api/v1/schemas.py`, and error mapping in `backend/app/api/errors.py`. The router module defines the Feature 004 routes and is included by the FastAPI application in `backend/app/api/main.py` only after the module exists. Reuse current config-scoped resource convention:

- `GET /api/v1/monitoring-configurations/{id}/gitlab-scope/root` returns the fully paginated top-level group set only; it does not load descendants or projects.
- `GET /api/v1/monitoring-configurations/{id}/gitlab-scope/groups/{group_id}/children` returns all direct subgroup and owned-project nodes for the requested expanded group only; it does not recursively load descendant children.
- `GET /api/v1/monitoring-configurations/{id}/gitlab-scope` returns persisted group/repository rules with reconciliation statuses and ETag.
- `PUT /api/v1/monitoring-configurations/{id}/gitlab-scope` replaces explicit rules atomically, requires `If-Match`, and accepts arrays of `{selection_id?, gitlab_id}` per node type. New nodes have no selection ID; persisted selections include their existing ID so stale entries can be retained intentionally. The server binds new nodes to the active instance and retains the original instance for recognized IDs. Response uses the safe scope representation and the new ETag.

Hierarchy node response fields are `id` (provider numeric ID), `type` (`group` or `repository`), `name`, `full_path`, `parent_group_id` when available, and `expandable` (true for groups, false for repositories). Selection entries add opaque `selection_id` and `availability`. The API omits raw token, ciphertext, normalized URL fingerprint, credential revision, raw GitLab response, and unapproved provider fields. Request bodies never accept a credential. Full schemas and status examples are in [contracts/api-v1.md](contracts/api-v1.md).

### Frontend architecture

- Add a nested route `/monitoring-configurations/:id/scope` through `src/app/routes/routeConfig.tsx` and `canonicalPaths`. Add a scope action/link from the configuration details page. Leave `MonitoringConfigurationForm`'s unrelated-field update payload unchanged.
- Add scope API/types/hook under `src/features/monitoring-configurations/{api,types,hooks}` and a `GitLabScopePage`, `RepositoryTree`, `ScopeTreeNode`, `ScopeSelectionSummary`, and `UnavailableScopeItem` under `components/pages`. Reuse Feature 001's `TreePanel`, `TreeNodeRow`, and `SelectedItemsPanel` visual primitives, extending them to controlled, accessible props; keep GitLab semantics in this feature.
- Keep one draft model with selected group and repository rule IDs, serialized as explicit group and repository rules. Derive checkbox `checked`, `indeterminate`, and inherited-by-selected-ancestor indication from rules plus loaded ancestry; never persist checkbox booleans. Selecting a group performs no descendant fetch. Removing a group leaves explicit descendant group/project IDs untouched.
- Keep expanded node IDs, loaded direct children, per-node loading/error, current search string, current/persisted rules, and dirty state in page/session memory. Cache loaded children only until leaving the scope editor or until the configuration URL/credential changes. Local search filters only loaded nodes and never changes rules or prunes hidden selections.
- The summary displays separate groups, repositories, and stale/unavailable/unresolved rules. Redundant repository rules remain visible in the explicit summary, optionally labeled as also covered by a selected group. Save sends all desired rules and existing selection IDs, including retained stale entries. Remove actions change the draft; only Save persists. A navigation guard follows existing form conventions.
- Provide prerequisite feedback when no connection credential is configured, loading/empty/retry states, save/conflict feedback, accessible expand/check controls and indeterminate labels, and responsive layout aligned with Feature 001 test viewports.

## Constitution Check (Post-Design)

| Principle | Post-design evidence | Result |
|---|---|---|
| I–IV. Boundaries and integration | Domain ports and normalized results separate use cases from GitLab REST, SQLAlchemy, FastAPI and React. | PASS |
| V. Secure construction | Credential remains encrypted at rest and transient for one outbound call; URLs/fingerprints, provider bodies and tokens are not emitted to clients or logs. | PASS |
| VI–VIII. Execution integrity | No execution/scheduler/pipeline is added; future execution resolution uses saved intent without modifying any execution record. | PASS |
| IX. Migration-managed persistence | New normalized tables and constraints are managed by reversible Alembic migration `0003`; no runtime schema mutation. | PASS |
| X. Verification | Planned unit, provider, API, PostgreSQL, and frontend scenarios cover requirements and failure cases. | PASS |
| XI. UX | Existing shell/shared visual patterns are retained and extended with deliberate accessible hierarchy and scope states. | PASS |
| XII. Simplicity | No new dependency, global state framework, distributed locking, or persistent hierarchy cache. | PASS |

**Post-design gate**: PASS. No constitution exception or complexity tracking entry is required.

## Project Structure

### Documentation

```text
specs/004-gitlab-scope-selection/
├── plan.md
├── research.md
├── data-model.md
├── contracts/api-v1.md
├── quickstart.md
└── tasks.md                 # generated in Phase 2 by $speckit-tasks
```

### Source Code

```text
backend/app/
├── domain/
│   ├── entities/mining_scope.py
│   ├── value_objects/gitlab_hierarchy_node.py
│   ├── value_objects/gitlab_discovery_result.py
│   └── ports/gitlab_connection_client.py            # extend Feature 003 port
├── application/
│   ├── ports/mining_scope_repository.py
│   └── use_cases/
│       ├── get_gitlab_scope_tree.py
│       ├── get_mining_scope.py
│       └── replace_mining_scope.py
├── infrastructure/
│   ├── gitlab/http_gitlab_connection_client.py       # extend Feature 003 adapter
│   └── database/
│       ├── models.py
│       ├── sqlalchemy_repositories.py
│       └── unit_of_work.py
└── api/v1/
    ├── gitlab_scopes.py
    └── schemas.py
backend/alembic/versions/0003_gitlab_scope.py
backend/tests/
├── unit/application/test_gitlab_scope.py
├── unit/infrastructure/gitlab/test_gitlab_scope_client.py
├── api/test_gitlab_scope.py
└── integration/test_gitlab_scope_persistence.py

src/app/routes/routeConfig.tsx
src/features/monitoring-configurations/
├── api/gitlabScopeApi.ts
├── types/gitlabScope.ts
├── hooks/useGitLabScope.ts
├── pages/GitLabScopePage.tsx
└── components/{RepositoryTree,ScopeTreeNode,ScopeSelectionSummary,UnavailableScopeItem}.tsx
src/test/features/monitoring-configurations/gitlab-scope-*.test.tsx
```

**Structure Decision**: Extend the existing split web application. Reuse the Feature 003 GitLab adapter and application request wiring, SQLAlchemy unit of work, API error envelope, Feature 001 shared tree visuals, and Feature 002 optimistic concurrency. No separate service or project is introduced.

## Test Strategy and Traceability

| Requirements / outcomes | Planned evidence |
|---|---|
| FR-001–005; SC-002, SC-005 | API/application tests for prerequisites, root-only initial discovery, requested-group-only expansion, no recursive/unrelated-branch fetches, all-page completeness for the requested node, safe normalized hierarchy and error atomicity; MockTransport pagination, malformed response, duplicate and failure-on-later-page cases; UI assertions that navigation is available after root load and unrelated branches remain unloaded. |
| FR-006–011; SC-003, SC-006 | Domain/use-case tests for mixed explicit group/repository rules, group selection without child fetch, group and repository removals, clear/empty scope, partial/inherited checkbox derivation, overlap deduplication while preserving explicit intent, dirty/save behavior and stale ETag conflict; UI summary, filtering/collapse and save tests. |
| FR-012–015; SC-004 | PostgreSQL/API tests for stable ID and same-instance rename/move, inaccessible/deleted unresolved entries, credential replacement/removal retaining rows, stale URL fingerprint behavior and same-ID cross-instance collision; frontend stale/unavailable summary and explicit removal tests. |
| FR-016–020 | API contract tests for local loaded-node search, empty persisted scope, unchanged enabled/unrelated configuration values, safe ProblemDetails, no raw provider payloads, and `If-Match` 428/412 semantics. |
| FR-021; SC-001 | Complete test matrix above runs with fake ports or HTTPX MockTransport; isolated PostgreSQL migration/CAS integration; no live GitLab required. A frontend integration-style workflow test with representative mocked hierarchy completes the SC-001 visible-control path; no formal timing/participant study is part of this feature. |
| FR-022 | Scope review asserts no mining, cloning, execution, schedule, or findings APIs/jobs are introduced. |

## Deferred Scope

- Feature 005+ execution-time resolution of current group membership into effective repositories, cloning, and mining.
- Global GitLab full-text search and frontend-managed provider pagination for one exceptionally large direct-child set.
- Authentication/authorization, scheduling, execution state/history, findings, and analytics.

## Complexity Tracking

No constitution violations or unjustified complexity.
