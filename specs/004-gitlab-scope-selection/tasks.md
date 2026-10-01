---
description: "Dependency-ordered implementation tasks for GitLab Scope Selection"
---

# Tasks: GitLab Scope Selection

**Input**: Design documents from `/specs/004-gitlab-scope-selection/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/api-v1.md](contracts/api-v1.md), [quickstart.md](quickstart.md)

**Tests**: Included because FR-021 explicitly requires backend, provider, persistence, and frontend automated coverage. GitLab interactions must use controlled responses; PostgreSQL integration must use PostgreSQL, not SQLite.

**Organization**: Tasks are grouped by user story. Shared domain/persistence/API foundations precede the stories; US2 and US3 build on the usable scope editor delivered by US1.

## Format

Every task uses `- [ ] T### [P?] [US#?] Description with exact file path`; completed tasks are marked `[X]`. `[P]` is present only when the task can proceed independently against different files.

## Phase 1: Setup

**Purpose**: Add reusable deterministic test data for normalized GitLab hierarchy and persisted selection scenarios.

- [X] T001 [P] Add normalized hierarchy and provider-page fixture builders in `backend/tests/conftest.py`
- [X] T002 [P] Add scope/tree/reconciliation frontend fixture builders in `src/test/features/monitoring-configurations/gitlabScopeFixtures.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish shared scope concepts, persistence, migration, and API wiring required by all user stories.

- [X] T003 Define `MiningScope`, selected group/repository rules, hierarchy node/result, and availability concepts in `backend/app/domain/entities/mining_scope.py`, `backend/app/domain/value_objects/gitlab_hierarchy_node.py`, and `backend/app/domain/value_objects/gitlab_discovery_result.py`
- [X] T004 Define the application-owned scope repository port and extend the GitLab client port with normalized top-level groups, direct subgroups/projects, and entity lookup operations in `backend/app/application/ports/mining_scope_repository.py` and `backend/app/domain/ports/gitlab_connection_client.py`
- [X] T005 Add SQLAlchemy scope-state, selected-group, and selected-repository models with foreign keys, uniqueness, positive ID/version, and fixed 64-character internal fingerprint constraints in `backend/app/infrastructure/database/models.py`
- [X] T006 Add Alembic revision `0003_gitlab_scope` after `0002_gitlab_credentials`, creating only the scope tables and preserving existing configurations as empty scopes, in `backend/alembic/versions/0003_gitlab_scope.py`
- [X] T007 Implement SQLAlchemy scope repository loading, full-set replacement, and transactional version compare-and-swap in `backend/app/infrastructure/database/sqlalchemy_repositories.py` and `backend/app/infrastructure/database/unit_of_work.py`
- [X] T008 Add shared dependency providers and safe GitLab-scope error mappings without importing or registering the Feature 004 router in `backend/app/api/dependencies.py` and `backend/app/api/errors.py`
- [X] T009 Add shared scope request/response and normalized hierarchy schemas in `backend/app/api/v1/schemas.py`
- [X] T010 Add mock-provider/PostgreSQL fixtures and migration-test registration for Feature 004 in `backend/tests/conftest.py` and `backend/tests/integration/conftest.py`

**Checkpoint**: Domain and persistence contracts are defined, the migration is registered, and shared API dependencies/error mappings are ready. Feature 004 routes remain unregistered until T019 creates their router module.

---

## Phase 3: User Story 1 - Browse and save a repository scope (Priority: P1) — MVP

**Goal**: Browse accessible hierarchy and persist/reload explicit group and repository intent, including a valid empty scope.

**Independent Test**: Using a configured test credential and controlled GitLab responses, load root groups, expand nested groups, select groups and repositories without loading all descendants, save/reopen the exact explicit rules, verify overlap is counted once but both rules remain editable, and save an empty scope without changing configuration enabled state.

### Tests for User Story 1

- [X] T011 [P] [US1] Test scope invariants, group dynamic coverage, repository independence, overlap deduplication, and empty scope in `backend/tests/unit/application/test_gitlab_scope.py`
- [X] T012 [P] [US1] Test complete root/child pagination, direct-only project membership, no shared/descendant projects, stable ordering, duplicate-page handling, and later-page failure atomicity in `backend/tests/unit/infrastructure/gitlab/test_gitlab_scope_client.py`
- [X] T013 [P] [US1] Test root/children/read/replace API contracts, missing credential/invalid URL outcomes, ETag preconditions, no credential/provider payload disclosure, and unchanged enabled state in `backend/tests/api/test_gitlab_scope.py`
- [X] T014 [P] [US1] Test first-save/reload/empty-scope and concurrent scope-version compare-and-swap using PostgreSQL in `backend/tests/integration/test_gitlab_scope_persistence.py`
- [X] T015 [P] [US1] Add a frontend end-to-end or integration-style test using representative mocked GitLab hierarchy data that completes the visible-control workflow—open scope, browse, expand a nested group, select a group or repository, review the summary, and save—and also cover selecting an unloaded group, overlap, reload, empty state, and dirty navigation in `src/test/features/monitoring-configurations/gitlab-scope-selection.test.tsx`

### Implementation for User Story 1

- [X] T016 Extend `HttpGitLabConnectionClient` with normalized GitLab v4 top-level-group, direct-child, and detail lookups; follow every `X-Next-Page` page with `per_page=100`, `include_subgroups=false`, and `with_shared=false` for group projects in `backend/app/infrastructure/gitlab/http_gitlab_connection_client.py`
- [X] T017 Implement lazy root/direct-child discovery and safe connection snapshot checks around outbound calls in `backend/app/application/use_cases/get_gitlab_scope_tree.py`
- [X] T018 Implement scope retrieval/reconciliation status projection and atomic full-set replacement with scope ETag compare-and-swap in `backend/app/application/use_cases/get_mining_scope.py` and `backend/app/application/use_cases/replace_mining_scope.py`
- [X] T019 Create `gitlab_scopes.py`, define root, direct-children, saved-scope GET, and If-Match-protected full-set PUT routes with contract DTOs and normalized errors, then include/register that router in the FastAPI application only after the module exists in `backend/app/api/v1/gitlab_scopes.py` and `backend/app/api/main.py`
- [X] T020 Add frontend hierarchy/scope API calls, explicit TypeScript contracts, and scope query/save hooks in `src/features/monitoring-configurations/api/gitlabScopeApi.ts`, `src/features/monitoring-configurations/types/gitlabScope.ts`, and `src/features/monitoring-configurations/hooks/useGitLabScope.ts`
- [X] T021 Implement scope route, configuration-page entry point, and GitLab scope editor page using the established application shell in `src/app/routes/routeConfig.tsx`, `src/app/routes/canonicalPaths.ts`, `src/features/monitoring-configurations/pages/GitLabScopePage.tsx`, and `src/features/monitoring-configurations/pages/MonitoringConfigurationDetailsPage.tsx`
- [X] T022 Implement controlled accessible tree nodes, draft selection semantics, derived checked/indeterminate/inherited presentation, and loaded-node-only search in `src/features/monitoring-configurations/components/RepositoryTree.tsx` and `src/features/monitoring-configurations/components/ScopeTreeNode.tsx`
- [X] T023 Implement explicit-rule summary, overlap labeling, remove/clear actions, save feedback, and unsaved navigation protection in `src/features/monitoring-configurations/components/ScopeSelectionSummary.tsx` and `src/features/monitoring-configurations/pages/GitLabScopePage.tsx`

**Checkpoint**: US1 is usable and testable without reconciliation complexity: users can browse, edit, save, reopen, and clear scope intent.

---

## Phase 4: User Story 2 - Understand selections and unavailable entities (Priority: P2)

**Goal**: Retain saved selections through rename/move, loss of access, credential replacement/removal, and GitLab instance changes; expose safe statuses and explicit removal.

**Independent Test**: Persist rules, then simulate renamed/moved accessible entities, 403/404 entities, temporary provider errors, credential changes/removal, and URL changes including colliding numeric IDs. Reopen and verify metadata/status, old-instance isolation, retention until explicit removal, and successful clear/retention without a credential.

### Tests for User Story 2

- [X] T024 [P] [US2] Test accessible rename/move refresh, unavailable 403/404, unresolved provider failure, credential replacement/removal retention, stale URL fingerprint isolation, same-ID cross-instance collision, and no-credential remove/clear in `backend/tests/unit/application/test_gitlab_scope.py`
- [X] T025 [P] [US2] Test PostgreSQL preservation of scope rows across credential changes, URL changes, reconciliation failures, and explicit removal in `backend/tests/integration/test_gitlab_scope_persistence.py`
- [X] T026 [P] [US2] Test read API status DTOs, safe provider errors, stale entries never queried against the active instance, and no fingerprint/credential disclosure in `backend/tests/api/test_gitlab_scope.py`
- [X] T027 [P] [US2] Test unavailable/stale/unresolved summary display, retained entries, current metadata refresh, explicit removal, and retry feedback in `src/test/features/monitoring-configurations/gitlab-scope-reconciliation.test.tsx`

### Implementation for User Story 2

- [X] T028 Reconcile current-origin persisted IDs through bounded normalized provider lookups, refresh safe display metadata, preserve unresolved entries, and skip provider lookups for stale origins in `backend/app/application/use_cases/get_mining_scope.py`
- [X] T029 Preserve selection origin on existing selection-ID round-trip, bind new selections only to the active instance, and retain omitted/unavailable records on failed validation or CAS conflict in `backend/app/application/use_cases/replace_mining_scope.py`
- [X] T030 Return selection-level available/unavailable/unresolved/stale status and safe actionable API errors without exposing instance fingerprints in `backend/app/api/v1/gitlab_scopes.py` and `backend/app/api/v1/schemas.py`
- [X] T031 Implement unavailable/stale scope row presentation, accessible explicit removal, and retryable reconciliation feedback in `src/features/monitoring-configurations/components/UnavailableScopeItem.tsx` and `src/features/monitoring-configurations/components/ScopeSelectionSummary.tsx`
- [X] T032 Preserve old-instance selections while allowing new-instance rules to coexist, and prevent the discovery tree from interpreting stale IDs against the active URL in `src/features/monitoring-configurations/pages/GitLabScopePage.tsx` and `src/features/monitoring-configurations/hooks/useGitLabScope.ts`

**Checkpoint**: US2 proves saved intent is durable and instance-bound even when current provider visibility changes.

---

## Phase 5: User Story 3 - Navigate a large hierarchy (Priority: P3)

**Goal**: Keep deeply nested and large GitLab hierarchies navigable with per-branch progress, complete pagination, local search, and unaffected draft state.

**Independent Test**: Use a deterministic mocked hierarchy with at least 1,000 entities distributed across multiple root groups and nested branches. Assert the initial request fetches only root-level groups and the tree becomes interactive after that response; assert expanding one group fetches every page of only that group's direct children, without recursively fetching its descendants; assert unrelated branches remain unloaded until expanded. Also cover deep nesting, empty/error branches, repeated names, per-branch retry, and filtering/collapse preserving draft rules.

### Tests for User Story 3

- [X] T033 [P] [US3] Test a mocked 1,000-entity hierarchy distributed across root groups/nested branches; assert root discovery requests only root groups, one application expansion invokes discovery only for the requested group, the provider fetches all pages for that group's direct children without recursively requesting descendants, unrelated branches remain untouched, and later-page failure does not return partial success in `backend/tests/unit/application/test_gitlab_scope.py` and `backend/tests/unit/infrastructure/gitlab/test_gitlab_scope_client.py`
- [X] T034 [P] [US3] Test that the tree becomes interactive after root load, expanding one group loads only that branch while unrelated branches remain unloaded, and navigation does not wait for descendant fetches; also test accessible keyboard behavior, per-node loading/retry, empty branches, local filtering, hidden-selection retention, collapse retention, and the 1,000-entity hierarchy in `src/test/features/monitoring-configurations/gitlab-scope-tree.test.tsx` and `src/test/features/monitoring-configurations/gitlab-scope-accessibility.test.tsx`

### Implementation for User Story 3

- [X] T035 Maintain per-node loaded children, in-flight/loading/error state, retry, ordering, and editing-session cache invalidation on URL/credential changes in `src/features/monitoring-configurations/hooks/useGitLabScope.ts`
- [X] T036 Ensure tree expansion reports node-specific loading, empty, and recoverable errors while preserving unaffected branches and draft selections in `src/features/monitoring-configurations/components/RepositoryTree.tsx` and `src/features/monitoring-configurations/components/ScopeTreeNode.tsx`
- [X] T037 Refine local search over loaded nodes and keyboard/ARIA behavior for nested groups, selected coverage, and indeterminate state in `src/features/monitoring-configurations/components/RepositoryTree.tsx` and `src/features/monitoring-configurations/components/ScopeTreeNode.tsx`

**Checkpoint**: US3 makes all branch data reachable without requiring instance-wide hierarchy materialization.

---

## Phase 6: Polish & Cross-Cutting Verification

**Purpose**: Run the complete feature matrix, validate migration/quickstart, and ensure Feature 004 boundaries remain intact.

- [X] T038 [P] Verify API/telemetry/logging schemas and frontend storage/state contain no credential, raw provider payload, or internal instance fingerprint in `backend/tests/api/test_gitlab_scope.py`, `backend/tests/unit/application/test_gitlab_scope.py`, and `src/test/features/monitoring-configurations/gitlab-scope-reconciliation.test.tsx`
- [X] T039 Validate migration upgrade/downgrade, constraints, cascade lifecycle, and CAS integration against isolated PostgreSQL in `backend/tests/integration/test_gitlab_scope_persistence.py` and `backend/tests/integration/test_migrations.py`
- [X] T040 Run database-independent Feature 004 backend suites from `backend/`: `.venv/Scripts/python.exe -m pytest tests/unit/application/test_gitlab_scope.py tests/unit/infrastructure/gitlab/test_gitlab_scope_client.py tests/api/test_gitlab_scope.py`
- [X] T041 Run isolated PostgreSQL Feature 004 suites using `TEST_DATABASE_URL`: `.venv/Scripts/python.exe -m pytest tests/integration/test_gitlab_scope_persistence.py tests/integration/test_migrations.py`
- [X] T042 Run Feature 004 frontend suites and production build from repository root: `npm test -- --run src/test/features/monitoring-configurations/gitlab-scope-tree.test.tsx src/test/features/monitoring-configurations/gitlab-scope-selection.test.tsx src/test/features/monitoring-configurations/gitlab-scope-reconciliation.test.tsx src/test/features/monitoring-configurations/gitlab-scope-accessibility.test.tsx` and `npm run build`
- [ ] T043 Complete the manual scenarios in `specs/004-gitlab-scope-selection/quickstart.md`, confirm the deterministic SC-001 visible-control workflow test in `src/test/features/monitoring-configurations/gitlab-scope-selection.test.tsx`, and record PostgreSQL integration results separately when the local PostgreSQL service is unavailable; do not require a participant study or timing threshold
  - Not executed: live GitLab manual steps require a user-provided instance and credential; automated mock scenarios, local API startup, and isolated PostgreSQL tests were executed.
- [X] T044 Confirm no scheduler, mining execution, cloning, commit traversal, findings, execution-history/dashboard, or authentication/authorization capability was introduced in `specs/004-gitlab-scope-selection/plan.md`, `backend/app/`, and `src/features/monitoring-configurations/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; fixture helpers may be completed in parallel.
- **Foundational (Phase 2)**: Depends on setup. Domain/persistence/shared API dependencies block every story; migration must precede PostgreSQL runtime validation. T008 does not import or register the Feature 004 router.
- **US1 (Phase 3)**: Depends on Phase 2. Delivers the first complete browse-and-save increment.
- **US2 (Phase 4)**: Depends on US1 contracts and saved-selection IDs; adds durable reconciliation and stale-instance UX.
- **US3 (Phase 5)**: Depends on US1 tree and selection state; adds scale/accessibility refinements. It can proceed in parallel with US2 after US1 if separate contributors own separate files.
- **Polish (Phase 6)**: Depends on all stories selected for delivery; PostgreSQL tasks require an isolated PostgreSQL database and must not substitute SQLite.

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; no dependency on other user stories.
- **US2 (P2)**: Requires US1's persisted scope contracts and summary/editor; its backend reconciliation work may begin after Foundational, but full story acceptance depends on US1 integration.
- **US3 (P3)**: Requires US1's tree/draft model; independent from US2's reconciliation behavior and can be parallelized after US1.

T019 creates `backend/app/api/v1/gitlab_scopes.py` before including it from `backend/app/api/main.py`; T008 provides only shared dependencies and error mappings and has no router-module dependency.

### Dependency Graph

```text
Setup → Foundational → US1 ─┬→ US2 ─┐
                            └→ US3 ─┴→ Polish
```

### Parallel Opportunities

- Phase 1: T001 and T002 touch separate test-fixture files.
- Phase 2 after T003/T004 contracts: T005 model, T008 shared dependency/error infrastructure, and T009 schemas can be split across owners; T006 migration follows T005; T007 persistence follows T003/T005. T008 does not register routes.
- US1: T011–T015 are independent test files/suites; T016 provider adapter can proceed separately from frontend T020–T023 once contracts are stable.
- US2: T024–T027 are independent tests; its UI component work (T031) can proceed separately from backend reconciliation (T028–T030).
- US3: T033 and T034 are independent tests; after US1, US3 can proceed alongside US2 using tree/hook files distinct from reconciliation summary files where possible.

## Parallel Example: User Story 1

```text
After Phase 2 contracts exist, run T011–T015 in parallel across their separate test files.
Then split implementation by boundary: backend provider/application/API (T016–T019) and frontend API/tree/editor (T020–T023).
Integrate and run the US1 independent test before beginning dependent UI reconciliation work.
```

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Phase 1 and Phase 2, including the Alembic scope tables and repository CAS. Do not import the Feature 004 router into `backend/app/api/main.py` until T019 creates it.
2. Complete Phase 3: normalized lazy discovery, explicit scope read/write, usable selection tree, summary, and save.
3. Run the US1 independent test with controlled GitLab responses and PostgreSQL persistence verification.
4. Run the deterministic SC-001 frontend workflow test and demo the MVP with one selected dynamic group, individual repositories, reload, overlap, and empty scope.

### Incremental Delivery

1. Deliver Setup + Foundational and confirm migrations on PostgreSQL.
2. Deliver US1 as a browse/save/reload MVP.
3. Deliver US2 to retain/reconcile unavailable and stale-instance intent.
4. Deliver US3 to validate large/deep hierarchy navigation and accessible branch states.
5. Run Phase 6 suites and quickstart; report PostgreSQL integration separately if unavailable.

## Notes

- `[X]` records implementation and automated verification completed by this run. T043 remains open because its live GitLab manual scenarios require a user-provided GitLab instance and credential; the mocked integration scenarios, PostgreSQL verification, and local startup check do not substitute for a live provider smoke test.
- `[P]` marks only independent work on distinct files. `[US1]`, `[US2]`, and `[US3]` map directly to the specification's user stories.
- Scope selection stores intent only. Effective future repository resolution, cloning, and mining remain deferred to later features.

## Phase 7: Convergence

- [ ] T045 Execute the remaining manual scenarios in `specs/004-gitlab-scope-selection/quickstart.md` against a disposable Monitoring Configuration and GitLab test scope; verify live hierarchy discovery, save/reload, unavailable and stale-instance retention, and stale-edit conflict behavior, then record pass/fail outcomes without credentials or other secrets per plan: live GitLab quickstart validation (partial)
  - Read-only live smoke check passed: credential status was validated; root discovery, one group's direct-child discovery, and persisted-scope retrieval succeeded. No selection, credential, or URL was changed. The remaining scenarios require a disposable configuration so existing user scope is not modified.
