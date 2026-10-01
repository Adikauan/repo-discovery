# Tasks: Repository Mining Engine

**Input**: Design documents from `/specs/008-repository-mining-engine/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, and `contracts/`

**Tests**: Tests are required by Feature 008's specification and are included by story. Provider interactions in automated tests use controlled mocks; PostgreSQL-specific validation is conditional on `TEST_DATABASE_URL` being available.

**Organization**: Tasks are grouped by the three user stories from `spec.md`. Dependencies below reflect shared pipeline, execution contract, API, and dashboard ownership.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel with other marked tasks in the same ready set because they have no unfinished dependency and do not modify the same files.
- **[Story]**: User story label maps to `spec.md` (US1â€“US3).
- Every task names the source/test/documentation paths it changes.

---

## Phase 1: Setup (Shared Mining Configuration)

**Purpose**: Establish validated, explicit bounds used by the pipeline.

- [X] T001 [P] Add `repository_mining_concurrency` (default 4, valid 1â€“8), `repository_mining_max_tree_entries` (default 50,000), `repository_mining_max_file_bytes` (default 1,048,576), and `repository_mining_max_extensions` (default 100, valid 1â€“100) settings and validators in `backend/app/config.py`.
- [X] T002 [P] Add configuration default and invalid-bound cases for all four mining settings in `backend/tests/unit/test_config.py`, including `repository_mining_max_extensions` default 100 and rejection below 1 or above 100.

---

## Phase 2: Foundational (Blocking Domain and Persistence)

**Purpose**: Define common value objects, repository lifecycle, persistence constraints and ports required by every story.

- [X] T003 [P] Create `RepositoryExecution` domain entity and lifecycle in `backend/app/domain/entities/repository_execution.py` with exactly `pending`, `running`, `completed`, and `failed`; allow `pending -> running`, `running -> completed`, and `running -> failed`; require nonnegative counters, ordered timestamps, and normalized safe error code/summary only for failed records.
- [X] T004 [P] Define immutable `RepositoryFileMetadata`, `RepositoryContext`, `RepositorySummaryResult`, and the `MiningRule` contract in `backend/app/domain/value_objects/repository_context.py`, `backend/app/domain/value_objects/repository_summary.py`, and `backend/app/domain/services/mining_rule.py`; distinguish metadata eligibility from text-content eligibility, allow optional provider file-size/reliable binary metadata, make the rule accept the validated configured extension limit (1â€“100, default 100), sort/truncate deterministically, use `(none)` for extensionless files, and keep factual summaries distinct from Findings.
- [X] T005 Add SQLAlchemy mappings in `backend/app/infrastructure/database/models.py` for `repository_executions` and additive MiningExecution `scope_resolution_failure_count` and private `repository_mining_completed`; enforce non-null execution FK with `ON DELETE RESTRICT`, positive `gitlab_project_id`, non-empty repository name/full path, statuses exactly `pending`, `running`, `completed`, `failed`, nonnegative `file_count`/`finding_count`/scope-failure count, safe error-pair/status consistency, unique `(mining_execution_id, gitlab_project_id)`, and at most 100 observed extensions. Include started/completed timestamps and processed branch, `extensions_truncated`, and the persisted summary fields.
- [X] T006 Create `backend/alembic/versions/0006_repository_executions.py` after migration `0005_mining_executions`, with the fields and constraints in `data-model.md`; include indexes for execution/path ordering, status, and GitLab project ID; enforce unique `(mining_execution_id, gitlab_project_id)`, positive project IDs, nonnegative file/finding/scope-failure counts, valid repository statuses and safe error pair; use `ON DELETE RESTRICT`; update the MiningExecution error check to permit only the approved scope-resolution codes on `partially_completed` in addition to existing failed errors. Backfill `scope_resolution_failure_count=0` and `repository_mining_completed=false` so legacy completion meaning is preserved. Depends on T005.
- [X] T007 [P] Define repository execution persistence methods and unit-of-work exposure in `backend/app/application/ports/repository_execution_repository.py`, `backend/app/application/ports/mining_execution_repository.py`, `backend/app/application/ports/monitoring_configuration_repository.py`, and `backend/app/infrastructure/database/unit_of_work.py`; include create, expected-status transition, summary/failure persistence, deterministic list/count, and execution aggregate update operations. Depends on T003 and T005.

**Checkpoint**: Domain contracts and migration-managed storage exist before story use cases are built.

---

## Phase 3: User Story 1 - Run a Real Mining Execution (Priority: P1) ðŸŽ¯ MVP

**Goal**: Process snapshot-selected, unique repositories and persist factual Repository Summary results through the existing manual execution lifecycle.

**Independent Test**: With mocked GitLab project/tree responses, process explicit repository and group scope; verify snapshot scope is authoritative, overlaps create one row per project, the default branch and deterministic summary are persisted, an honestly empty resolved scope completes with all counters zero, and manual execution uses the existing lifecycle.

### Tests for User Story 1

- [X] T008 [P] [US1] Add mocked HTTP transport contract tests for selected group validation, subgroup/project pagination with shared projects excluded, direct project lookup, declared default branch, recursive tree pagination (including full pages without `X-Next-Page` and a final short/empty page), malformed provider data, and tree entry limits in `backend/tests/unit/infrastructure/gitlab/test_http_gitlab_repository_client.py`.
- [X] T009 [P] [US1] Add resolver tests for explicit repositories, selected groups/subgroups, owned-project semantics, excluded shared projects, overlap deduplication, deterministic order, valid empty scope, and snapshot-only scope input without current Monitoring Configuration lookup in `backend/tests/unit/application/test_resolve_effective_scope.py`.
- [X] T010 [P] [US1] Add Repository Summary Rule and file-policy tests in `backend/tests/unit/domain/test_repository_summary_rule.py` for excluded directories not contributing to `file_count`, metadata-eligible oversized/binary files being countable, configured extension limit default 100 and a value below 100 being respected, deterministic ordering/truncation never exceeding the configured limit, extensionless `(none)`, zero-file repositories, oversized files being rejected before any text-content fetch, binary content never reaching text rules, and no blob/body retrieval solely for summary size/binary classification.
- [X] T011 [P] [US1] Add successful pipeline tests for repository row creation, summary persistence, all four counters, empty-scope completion, and Feature 006 lifecycle reuse in `backend/tests/unit/application/test_process_mining_execution.py`; add a concurrent same-configuration manual request integration test in `backend/tests/integration/test_manual_execution_concurrency.py` proving one active MiningExecution, only the winner starts `ProcessMiningExecution`, the loser receives the existing normalized conflict, and repository concurrency settings do not bypass that guard; add PostgreSQL RepositoryExecution uniqueness, FK retention, persisted-summary, and deterministic interrupted-worker persistence coverage in `backend/tests/integration/test_repository_execution_persistence.py`. For interruption, commit a running MiningExecution and running RepositoryExecution, stop the worker immediately after the repository running transition commits and before provider data retrieval, summary persistence, or terminal transition, then query with a fresh unit of work and assert both rows remain readable and active; preserve started timestamps, keep completed timestamps null, keep `processed_branch` absent, `file_count`/finding/success/failure counts at zero (with `repository_count=1` for its persisted row), `observed_extensions` empty, and `extensions_truncated=false`, and do not fabricate a repository error, summary payload, or parent completion. Existing Feature 006 stale reconciliation may change the parent only when separately invoked.

### Implementation for User Story 1

- [X] T012 [US1] Implement the mining-specific GitLab Groups/Projects and recursive Repository Tree adapter in `backend/app/infrastructure/gitlab/http_gitlab_repository_client.py`; validate groups and direct projects, enumerate subgroups and only group-owned projects (`include_subgroups=false`, `with_shared=false`), retrieve declared default branches and tree entries, normalize provider outcomes, page every result within configured bounds, disable automatic retries, and keep raw DTOs/HTTPX responses in infrastructure.
- [X] T013 [US1] Implement `EffectiveScopeResolver` in `backend/app/application/use_cases/resolve_effective_scope.py` using only `ExecutionSnapshotV1`; resolve direct projects and owned projects in selected group/subgroup hierarchies, deduplicate by instance/project identity, and return deterministic project order. Depends on T012.
- [X] T014 [P] [US1] Implement centralized file-policy predicates and `RepositorySummaryRule` in `backend/app/domain/services/repository_summary_rule.py` and `backend/app/domain/services/repository_file_filter.py`; define separate metadata and text-content eligibility; for metadata, ignore exact case-insensitive path segments `.git`, `node_modules`, `vendor`, `bin`, `obj`, `dist`, and `build`, count all remaining blob/file entries regardless of size or binary status, and never fetch content for summary classification; for future text input, exclude files above `repository_mining_max_file_bytes` and require binary safety before passing text. Normalize extensions to the final non-leading lowercased suffix with dot, use `(none)` for extensionless names/dotfiles without a later suffix, retain no more than the configured `repository_mining_max_extensions` (1â€“100, default 100) in deterministic sorted order, record truncation, and produce `finding_count=0`. Depends on T004.
- [X] T015 [US1] Implement the single-repository processor in `backend/app/application/use_cases/process_repository.py`; transition pending to running, retrieve project metadata and tree at the declared default branch, build normalized context, execute the registered summary rule, persist typed summary, and transition to completed. Depends on T003, T004, T007, T012, and T014.
- [X] T016 [US1] Implement the application-owned execution mining orchestrator in `backend/app/application/use_cases/process_mining_execution.py`; resolve scope, create exactly one pending row for each unique resolved project, process successful rows, reconcile repository counters from persisted records, and finalize successful or valid-empty outcomes through the Feature 006 lifecycle service. Depends on T007, T013, and T015.
- [X] T017 [US1] Replace the temporary orchestration-only path in `backend/app/application/use_cases/create_manual_execution.py` with the real `ProcessMiningExecution` invocation only after the existing Feature 006 active-configuration guard has admitted the request; preserve at-most-one-active-execution-per-configuration behavior, normalized conflict for a non-stale pending/running execution, request idempotency, stale reconciliation, and expected-status lifecycle transitions, without adding a second execution-concurrency mechanism. Depends on T016.
- [X] T018 [US1] Wire the mining provider, unit-of-work/session factory, credential cipher, and pipeline configuration in `backend/app/api/dependencies.py`, `backend/app/api/main.py`, and `backend/app/infrastructure/database/unit_of_work.py`; ensure each repository worker receives its own short-lived SQLAlchemy session. Depends on T017.

**Checkpoint**: A manual execution processes valid snapshot scope, persists factual summaries, and reports accurate counters without failures being fabricated as findings.

---

## Phase 4: User Story 2 - Isolate Repository and Scope Failures Safely (Priority: P1)

**Goal**: Preserve useful repository outcomes while normalizing repository, credential, instance, and scope failures; derive partial/failed status with bounded concurrency.

**Independent Test**: Process mixed valid/invalid selections and repositories that fail for missing default branch, forbidden/not-found responses, timeout, malformed data, or tree bounds. Verify resolved repositories continue, safe errors persist, credentials never leak, scope failures remain separate from repository counters, concurrency stays within its configured bound, and aggregate status reconciles.

### Tests for User Story 2

- [X] T019 [P] [US2] Add repository processor tests for missing default branch, not found, forbidden, timeout, malformed tree, over-limit tree, normalized safe errors, and continued processing of other repositories in `backend/tests/unit/application/test_process_mining_execution.py`; inject a deterministic interruption immediately after the persisted `running` transition and before provider data retrieval or summary/terminal persistence, and assert the repository remains running with its start timestamp, no completed timestamp/error/fabricated summary, and no false success outcome.
- [X] T020 [P] [US2] Add aggregation tests for repository success/failure mixtures, all repositories failed, partial selected-scope resolution, failed scope with no repository successes, valid empty scope, pre-processing failure, `scope_resolution_failure_count`, and reconciliation of each persisted repository counter in `backend/tests/unit/application/test_process_mining_execution.py`.
- [X] T021 [P] [US2] Add bounded-worker tests proving active repository processors never exceed configuration, all independent repositories settle, duplicate scope does not create duplicate work, and one failure does not cancel others in `backend/tests/unit/application/test_process_mining_execution.py`.
- [X] T022 [P] [US2] Add security tests proving missing/invalid credential and fingerprint mismatch cause no provider request and that tokens, headers, raw provider bodies, exception text, and database details are absent from records/loggable responses in `backend/tests/unit/application/test_process_mining_execution.py` and `backend/tests/api/test_repository_executions_api.py`.

### Implementation for User Story 2

- [X] T023 [US2] Add an allow-listed mining failure taxonomy and infrastructure-to-application normalization in `backend/app/domain/value_objects/mining_failure.py` and `backend/app/infrastructure/gitlab/http_gitlab_repository_client.py`; define safe codes/summaries for credential missing, instance mismatch, scope unavailable, repository not found/forbidden/timeout/invalid response, default branch missing, tree bound exceeded, and generic repository processing failure. Depends on T012.
- [X] T024 [P] [US2] Resolve the current encrypted credential and validate snapshot URL fingerprint, current configured URL fingerprint, credential validated URL fingerprint, and all snapshot scope fingerprints before provider access in `backend/app/application/use_cases/process_mining_execution.py`; decrypt only after checks, use snapshot URL for calls, and persist pre-processing failures without fake repository rows. Depends on T016 and T023.
- [X] T025 [P] [US2] Persist per-repository failures and continue processing in `backend/app/application/use_cases/process_repository.py`; a missing provider-declared default branch must fail safely without guessing, increment the persisted failed repository total, and leave other repositories processable. Depends on T015 and T023.
- [X] T026 [P] [US2] Extend MiningExecution safe scope aggregate fields and lifecycle validation in `backend/app/domain/entities/mining_execution.py` and `backend/app/application/use_cases/transition_execution.py`; permit `scope_resolution_incomplete` on `partially_completed` only, use `scope_resolution_failed` for a failed scope with no successes, and keep repository counters equal to persisted rows. Depends on T003 and T006.
- [X] T027 [US2] Add a bounded in-flight `ThreadPoolExecutor` worker pool and final aggregate algorithm in `backend/app/application/use_cases/process_mining_execution.py`; use `REPOSITORY_MINING_CONCURRENCY` default 4 and max 8 only inside one execution admitted by the Feature 006 same-configuration active-execution guard, commit short transactions outside provider calls, continue after per-repository failures, and derive completed/partially_completed/failed from persisted successes plus repository/scope failure counts. Do not add or bypass the execution-level guard. Depends on T024â€“T026.

**Checkpoint**: Explicit scope failures cannot become successful empty scope; repository errors are isolated, safely recorded, and aggregated without counter inflation.

---

## Phase 5: User Story 3 - Inspect Repository Processing History (Priority: P1)

**Goal**: Replace the Feature 007 Repositories placeholder with safe, deterministic persisted repository history in the existing dashboard.

**Independent Test**: Read an execution's repository list and detail through safe DTOs and view the existing dashboard section. Verify deterministic paging, success/failure/partial rows, safe errors, timestamps, processed branch, file/finding counts, honest empty states, and accessible retry/loading feedback.

### Tests for User Story 3

- [X] T028 [P] [US3] Add API tests for repository list/detail DTOs, pagination and deterministic ordering, missing parent/row normalization, safe errors, zero findings, scope failure count, and credential/provider-internal non-disclosure in `backend/tests/api/test_repository_executions_api.py`; read an interrupted persisted execution/repository through the normal read paths and assert real `running`/`pending` status, unchanged lifecycle timestamps, no completed translation or fabricated summary, no raw interruption detail, and no credential exposure.
- [X] T029 [P] [US3] Add dashboard repository section tests for loading, normalized failure/retry, completed-empty versus active/pre-processing empty states, successful/failed/mixed rows, safe error display, zero findings, long paths, keyboard/status/table accessibility, and representative 375px/768px/1440px responsive layouts in `src/test/features/executions/execution-repositories.test.tsx` and the shared `src/test/features/executions/execution-accessibility.test.tsx`; include an interrupted pending/running repository fixture and assert status/timing remain visible, no success state is shown, and summary fields are not rendered until persisted processing results exist.

### Implementation for User Story 3

- [X] T030 [P] [US3] Implement read-only repository list/detail use cases with page bounds 1â€“100 (default 25), ownership scoping by MiningExecution, and order `(repository_full_path ASC, gitlab_project_id ASC)` in `backend/app/application/use_cases/list_repository_executions.py` and `backend/app/application/use_cases/get_repository_execution.py`.
- [X] T031 [US3] Add safe Pydantic repository list/detail schemas and read-only routes `GET /api/v1/executions/{execution_id}/repositories` and `GET /api/v1/executions/{execution_id}/repositories/{repository_execution_id}` in `backend/app/api/v1/repository_executions.py`; register the router in `backend/app/api/main.py`, return normalized 404 for absent/mismatched parent rows, and expose no mutation route. Depends on T030.
- [X] T032 [P] [US3] Extend the execution detail DTO with `scopeResolutionFailureCount` and safe partial scope error projection, and use the private persisted `repository_mining_completed` marker to distinguish legacy Feature 006 orchestration-only `completionMeaning` from Feature 008 processing and valid empty-scope meanings in `backend/app/api/v1/execution_schemas.py`; preserve existing fields and safe projection boundaries. Depends on T026.
- [X] T033 [US3] Add typed repository list/detail response models and paginated read methods to `src/features/executions/types/execution.ts` and `src/features/executions/api/executionsApi.ts`; support `AbortSignal` and do not add configuration or GitLab requests.
- [X] T034 [US3] Replace the unavailable placeholder in `src/features/executions/components/ExecutionRepositoriesSection.tsx` with the paginated repository list, accessible status text, safe error, branch, file/finding counts, timestamps, loading/retry/error, and execution-aware empty states; render only API DTO values, keep pending/running rows visibly nonterminal, and show summary fields only when persisted processing results are present. Depends on T031 and T033.
- [X] T035 [US3] Pass the execution ID and persisted execution summary into `ExecutionRepositoriesSection` and show safe scope-resolution/completion meaning from execution detail in the existing dashboard context in `src/features/executions/pages/ExecutionDashboardPage.tsx` and `src/features/executions/components/ExecutionOverview.tsx`; preserve `/executions/:id`, tabs, layout, and Findings unavailable state. Depends on T032 and T034.

**Checkpoint**: Users can inspect persisted per-repository outcomes through the existing dashboard without GitLab calls from the browser or fabricated findings.

---

## Phase 6: Polish & Cross-Cutting Validation

**Purpose**: Validate the integrated feature and report environmental limits accurately.

- [X] T036 Run backend unit and API suites from `backend/`, then run migration/persistence/concurrency integration tests against PostgreSQL only when `TEST_DATABASE_URL` is available; record any unavailable PostgreSQL validation without substituting SQLite. Backend suite result: 208 passed; 26 PostgreSQL integration cases skipped because `TEST_DATABASE_URL` is unavailable. Alembic offline SQL generation and head validation succeeded.
- [X] T037 Run the execution frontend test/accessibility suite and production build from the repository root using the commands in `specs/008-repository-mining-engine/quickstart.md`; fix implementation-related failures and record any environmental blockers. Result: 141 tests passed, including accessibility coverage; production build succeeded.
- [X] T038 Review `specs/008-repository-mining-engine/spec.md`, `plan.md`, `data-model.md`, both contracts, and `quickstart.md` against the completed implementation; confirm no current-configuration scope substitution, provider calls from the browser, fake rows/findings, scheduler, AI, polling, or unbounded concurrency was introduced. Review confirmed historical snapshot scope, metadata-only summary, safe persisted read APIs, bounded repository workers, and no Feature 009/010 functionality.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies. T001 and T002 touch separate files and may run in parallel.
- **Foundational (Phase 2)**: Starts after Phase 1. T003, T004, and T005 may proceed in parallel; T006 depends on T005; T007 depends on T003 and T005. All foundational tasks block story implementation.
- **User Story 1 (Phase 3)**: Depends on Phase 2. Its four test tasks use separate files and may run in parallel; implementation proceeds provider â†’ resolver/rule â†’ processor â†’ orchestrator â†’ manual integration/wiring as task IDs specify.
- **User Story 2 (Phase 4)**: Depends on User Story 1 because its failure isolation, runtime credential/instance checks, scope failure aggregation, and bounded concurrency extend the pipeline created in US1. Four US2 test tasks may run in parallel after US1; implementation tasks then proceed in order due shared processor/orchestrator/lifecycle files.
- **User Story 3 (Phase 5)**: Depends on US1 persistence/read facts and US2 safe failure/aggregate contracts. T028 and T029 test tasks may run in parallel. T030 and T032 may run in parallel after US2; T031 depends on T030; T033 can run alongside backend read-contract work; T034 depends on T031 and T033; T035 depends on T032 and T034.
- **Polish (Phase 6)**: Depends on all three user stories.

### User Story Dependencies

- **US1 (P1)**: Depends on setup and foundational phases only. It delivers real successful and valid-empty repository processing.
- **US2 (P1)**: Depends on US1's resolver, processor, orchestrator and lifecycle integration; it adds failure isolation and partial-scope aggregation.
- **US3 (P1)**: Depends on US1's repository records and US2's final safe error/scope-failure contract before exposing rows in the dashboard.

### Parallel Execution Examples

```text
After Phase 1:
  T003 || T004 || T005
  T006 follows T005
  T007 follows T003 and T005 (T006 || T007)

US1 tests (after Phase 2):
  T008 || T009 || T010 || T011
US1 implementation, after provider/value-object foundations:
  T012 -> T013
  T014 may run alongside T012/T013
  T015 -> T016 -> T017 -> T018

US2 tests (after US1):
  T019 || T020 || T021 || T022
US2 implementation:
  T023 || T026
  T024 || T025 follow T023
  T027 follows T024, T025, and T026

US3 tests (after US2):
  T028 || T029

US3 read contracts:
  T030 || T032 || T033
  T031 follows T030
  T034 follows T031 and T033
  T035 follows T032 and T034
```

Do not run tasks that modify `process_mining_execution.py`, `process_repository.py`, `execution_schemas.py`, `ExecutionDashboardPage.tsx`, or `ExecutionRepositoriesSection.tsx` concurrently. Their task IDs define their file-owner order.

### Implementation Strategy

1. Complete setup and foundational domain/persistence work.
2. Deliver US1 as the backend MVP: snapshot-based scope resolution, deterministic summary, persisted rows/counters, and manual lifecycle integration.
3. Deliver US2 before exposing repository data: normalized failures, scope-failure aggregation, credential/instance validation, and bounded concurrency.
4. Deliver US3 using only the resulting safe read contracts and persisted records.
5. Complete cross-cutting validation; run PostgreSQL-specific validation only with PostgreSQL and keep Feature 009 scheduling and Feature 010 Findings deferred.

## Requirement Traceability

| Requirement group | Tasks |
|---|---|
| FR-001, FR-002, FR-022: one manual pipeline, lifecycle, same-configuration execution guard | T011, T016â€“T018, T026â€“T027 |
| FR-003â€“FR-006: snapshot authority, scope rules, deduplication, instance safety | T008â€“T009, T012â€“T013, T020, T022â€“T024 |
| FR-007, FR-012, FR-017: credential/provider security, normalization, retry policy | T008, T012, T022â€“T024, T036, T038 |
| FR-008â€“FR-009, FR-019: RepositoryExecution model, lifecycle, persistence/retention | T003, T005â€“T007, T011, T015, T019, T028, T036 |
| FR-010â€“FR-011: aggregation and real counters | T011, T016, T020, T026â€“T027 |
| FR-013â€“FR-015: branch behavior, metadata/text eligibility, summary rule, source bounds | T001â€“T002, T008, T010, T012, T014â€“T015, T019 |
| FR-016, SC-006: per-execution repository concurrency and single active execution per configuration | T001â€“T002, T011, T017, T021â€“T022, T027, T036 |
| FR-023: PostgreSQL/provider tests | T008, T011, T021â€“T022, T036 |
| FR-018: stale/interrupted safety and truthful in-progress persistence/read state | T011, T017, T019, T024, T027â€“T029, T034, T036 |
| FR-020: safe repository reads | T028, T030â€“T033 |
| FR-021: dashboard repository history | T029, T032â€“T035, T037 |
| FR-024 and scope boundaries: no scheduler, findings, AI or live progress | T014, T027, T034â€“T038 |
| FR-025: preserve truthful completion meaning for legacy and Feature 008 executions | T005â€“T006, T016, T032, T036, T038 |

Success-criterion coverage is explicit: SC-001 T009/T011/T021; SC-002 T011/T020/T027; SC-003 T019/T021/T025; SC-004 T010/T014; SC-005 T022/T028; SC-006 T011/T017/T021/T027; SC-007 T029/T034/T035; SC-008 T010/T014.

## Notes

- Every task uses the required unchecked checkbox, sequential ID, optional `[P]`, required story label in story phases, and concrete project file path.
- The reviewer-owned `checklists/mining-engine.md` remains a requirements-quality artifact; task completion does not approve or modify its markers.
- No Feature 010 Finding model, repository clone, scheduler, AI service, WebSocket/SSE, polling loop, or browser-side GitLab call is part of these tasks.

## Phase 7: Convergence

- [X] T039 Display each repository failure's allow-listed safe error code together with its safe summary in `src/features/executions/components/ExecutionRepositoriesSection.tsx`; extend `src/test/features/executions/execution-repositories.test.tsx` to prove raw provider details remain hidden (repository-dashboard.md, plan: API and dashboard integration) (partial).
- [X] T040 Add responsive repository section layout checks at 375px, 768px, and 1440px in `src/test/features/executions/execution-repositories.test.tsx`; verify paths and table controls remain readable and the page does not gain forced horizontal overflow (T029, repository-dashboard.md) (partial).
