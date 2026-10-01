# Tasks: Feature 010 - Mining Findings

**Input**: Design documents from `/specs/010-mining-findings/`

**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts](contracts/), [quickstart.md](quickstart.md)

**Tests**: Required by the specification. Write focused tests before implementation where a task introduces a business rule or API behavior.

**Organization**: Tasks are grouped by the four prioritized user stories in `spec.md`. All user stories are P1, but dependencies below control delivery order.

## Phase 1: Setup

**Purpose**: Add the one bounded engine setting used by incremental commit processing.

- [X] T001 Add `email-validator>=2.3,<3` in `backend/pyproject.toml` and add `MINING_MAX_COMMITS_PER_REPOSITORY_EXECUTION` to `backend/app/config.py` with default `1000` and accepted integer range `1..10000`; add default, custom-value, lower-bound rejection, and upper-bound rejection coverage in `backend/tests/unit/test_config.py`.

## Phase 2: Foundational

**Purpose**: Establish migration-managed storage and shared domain contracts required by configuration, mining, and reads.

- [X] T002 Add SQLAlchemy mappings in `backend/app/infrastructure/database/models.py` and forward migration `backend/alembic/versions/0008_mining_findings.py` for configuration `allowed_author_emails` JSONB default `[]`, `repository_checkpoints`, and `findings`; include required/unique/check constraints and indexes from `data-model.md`, allow safe repository errors `commit_range_limit_exceeded` and `repository_checkpoint_unreachable`, use `ON DELETE RESTRICT` for history, and preserve legacy configuration/snapshot reads.
- [X] T003 Add immutable domain entities/value objects in `backend/app/domain/entities/finding.py`, `backend/app/domain/entities/repository_checkpoint.py`, `backend/app/domain/value_objects/normalized_commit.py`, and `backend/app/domain/value_objects/finding_candidate.py`; enforce `rule_id` max 100, `rule_version` max 32, severity `warning` for the initial rule, identity state `valid|missing|malformed`, full SHA identity, title max 160, summary max 500, author name max 200, and sanitized commit message max 500 Unicode code points.

**Checkpoint**: Settings, schema, and inner-layer result contracts are ready before story-specific behavior.

## Phase 3: User Story 1 - Configure allowed commit authors (Priority: P1)

**Goal**: Let configuration owners define normalized author emails and make each new manual/scheduled execution retain its immutable policy snapshot.

**Independent Test**: Save padded, mixed-case, and duplicate email values, create an execution, change the live configuration, and prove the old snapshot remains unchanged and drives historical evaluation.

### Tests for User Story 1

- [X] T004 [P] [US1] Add domain and snapshot tests in `backend/tests/unit/domain/test_monitoring_configuration.py` and `backend/tests/unit/test_execution_snapshot.py` for trim, Unicode case-fold, deduplication, sorted snapshot capture, empty-list acceptance, invalid addresses, the 500-entry/254-character bounds, legacy missing-field default, and manual/scheduled capture parity.
- [X] T005 [P] [US1] Extend create/update API tests in `backend/tests/api/test_configuration_create_and_read.py` and `backend/tests/api/test_configuration_update.py` proving `allowedAuthorEmails` validation, normalized persistence/response behavior, idempotency fingerprint inclusion, ETag conflict behavior, and no partial update for invalid input.

### Implementation for User Story 1

- [X] T006 [US1] Extend `backend/app/domain/monitoring_configuration.py` with allowed-email normalization and syntax validation using `email-validator` with DNS deliverability checks disabled: maximum 500 entries, maximum 254 characters per input, trim, Unicode case-fold, deduplicate, and deterministic sort; empty list is valid and invalid input raises existing field validation.
- [X] T007 [US1] Extend `backend/app/domain/entities/execution_snapshot.py`, `backend/app/application/use_cases/create_mining_execution.py`, and snapshot compatibility tests so shared manual and scheduled creation captures the normalized immutable `allowed_author_emails` tuple, while legacy snapshots default to empty and `backend/app/application/use_cases/get_execution.py` plus `backend/app/api/v1/execution_schemas.py` do not expose it publicly.
- [X] T008 [US1] Extend `backend/app/api/v1/schemas.py`, `backend/app/application/use_cases/create_monitoring_configuration.py`, `backend/app/application/use_cases/update_monitoring_configuration.py`, and configuration repository mappings in `backend/app/infrastructure/database/sqlalchemy_repositories.py` to accept/store/return the bounded policy without breaking current revision/ETag or request-idempotency semantics.
- [X] T009 [US1] Add an accessible allowed-author email editor to the existing configuration form in `src/features/monitoring-configurations/components/MonitoringConfigurationForm.tsx`, thread values through `src/features/monitoring-configurations/model/monitoringConfiguration.ts` and `src/features/monitoring-configurations/api/monitoringConfigurationsApi.ts`, and cover validation, edit round-trip, empty-list state, and keyboard/accessibility behavior in `src/test/features/monitoring-configurations/allowed-author-emails.test.tsx`.

**Checkpoint**: New executions contain the captured author policy, independent of later configuration edits.

## Phase 4: User Story 2 - Detect unauthorized commit authors incrementally (Priority: P1)

**Goal**: Establish branch baselines and persist deterministic Findings only for new commits after successful checkpoints.

**Independent Test**: With a mocked GitLab commit graph, first execution stores HEAD with no historical findings; a later execution detects unauthorized new commits, writes exact counters, and advances the checkpoint only after repository success.

### Tests for User Story 2

- [X] T010 [P] [US2] Add unit tests in `backend/tests/unit/domain/test_unauthorized_commit_author_rule.py` for exact/case-insensitive email match, whitespace, duplicate allowlist values, empty allowlist, unauthorized address, missing/whitespace-only email, malformed email with no raw-value retention, no name-based identity, warning severity, sanitized bounded message, deterministic candidate output, and zero candidates for authorized commits.
- [X] T011 [P] [US2] Add mocked GitLab adapter tests in `backend/tests/unit/infrastructure/test_gitlab_commit_history.py` for current HEAD, revision-range retrieval, all pages, duplicate SHAs, stable ordering, checkpoint reachability, malformed/incomplete pages, limit+1 overflow detection, timeout, forbidden, not-found, and raw response/token non-disclosure.
- [X] T012 [P] [US2] Add application processing tests in `backend/tests/unit/application/test_process_repository_findings.py` for first-run baseline without history scan, subsequent incremental range, valid/missing/malformed authors, finding count reconciliation, zero-commit range, rewritten history, and no checkpoint advancement before successful result persistence.

### Implementation for User Story 2

- [X] T013 [US2] Extend `backend/app/domain/services/mining_rule.py` with a normalized rule-result contract returning facts plus zero-or-more immutable Finding candidates, without importing HTTPX, SQLAlchemy, or FastAPI; preserve `RepositorySummaryRule` compatibility and its non-Finding result.
- [X] T014 [US2] Add pure `UnauthorizedCommitAuthorRule` in `backend/app/domain/services/unauthorized_commit_author_rule.py` using `backend/app/domain/value_objects/normalized_commit.py` and the execution snapshot allowlist; use the shared syntax validator without DNS checks, compare trimmed Unicode case-folded emails, treat empty allowlist as all valid emails unauthorized, create one warning candidate for every unauthorized/missing/malformed commit, discard malformed raw email, and never infer identity from author name.
- [X] T015 [US2] Create the application-owned GitLab repository port in `backend/app/application/ports/gitlab_repository_client.py` and implement normalized HEAD/range/reachability methods in `backend/app/infrastructure/gitlab/http_gitlab_repository_client.py`; follow every GitLab page, deduplicate full SHAs, return deterministic oldest-to-newest commits, verify the stored checkpoint is reachable from the selected branch, stop at configured limit plus one, and map failures to safe domain codes.
- [X] T016 [US2] Add Finding and RepositoryCheckpoint repository protocols in `backend/app/application/ports/finding_repository.py` and `backend/app/application/ports/repository_checkpoint_repository.py`, extend `backend/app/application/ports/monitoring_configuration_repository.py` unit-of-work contract, and implement them in `backend/app/infrastructure/database/sqlalchemy_repositories.py` with uniqueness handling, persisted-row count queries, and short transaction support; enforce checkpoint identity `(monitoring_configuration_id, gitlab_project_id, branch)` and Finding identity `(repository_execution_id, rule_id, rule_version, commit_hash)`.
- [X] T017 [US2] Extend `backend/app/application/use_cases/process_repository.py` to use the Feature 008 default branch and shared rule contract: baseline current HEAD when no checkpoint, otherwise retrieve only commits after the reachable checkpoint, fail safely on `commit_range_limit_exceeded` or `repository_checkpoint_unreachable`, and atomically insert findings, update RepositoryExecution finding_count/status, and advance checkpoint after all provider/rule work succeeds.
- [X] T018 [US2] Add or adjust `backend/tests/unit/application/test_process_mining_execution.py`, `backend/tests/unit/application/test_create_manual_execution.py`, and `backend/tests/unit/application/test_scheduled_execution_dispatch.py` to prove `MiningExecution.finding_count` reconciles with persisted Finding rows, existing Feature 008 aggregation derives counts from repository results, and both manual and scheduled executions invoke the same finding-producing mining pipeline with no scheduler-specific rule path.

**Checkpoint**: Successful repository processing produces durable, bounded, idempotent Findings and advances only that repository's checkpoint.

## Phase 5: User Story 3 - Inspect findings from an execution (Priority: P1)

**Goal**: Query persisted Findings through existing history APIs and display them in the existing dashboard Findings section.

**Independent Test**: Return zero, one, and multiple safe Finding DTOs; verify deterministic lists, ownership, normalized API errors, and dashboard empty/loading/error/populated states using persisted data only.

### Tests for User Story 3

- [X] T019 [P] [US3] Add API tests in `backend/tests/api/test_findings.py` for execution list, repository list, detail, filters, deterministic ordering, missing execution/repository/finding, nested ownership mismatch, safe DTO fields, and exclusion of snapshot policy, credentials, raw provider bodies, and internal errors.
- [X] T020 [P] [US3] Add frontend tests in `src/test/features/executions/execution-findings.test.tsx` for zero/one/multiple findings, repository association, rule/severity, commit hash, author email and missing/malformed states, sanitized summary, timestamp, loading, normalized API error/retry, keyboard access, semantics, and responsive readability.

### Implementation for User Story 3

- [X] T021 [US3] Add deterministic Finding list/detail query use cases and repository methods in `backend/app/application/use_cases/list_execution_findings.py`, `backend/app/application/use_cases/list_repository_findings.py`, `backend/app/application/use_cases/get_finding.py`, and `backend/app/infrastructure/database/sqlalchemy_repositories.py`; derive MiningExecution through RepositoryExecution and validate nested ownership.
- [X] T022 [US3] Add safe Finding DTOs and read-only routes in `backend/app/api/v1/finding_schemas.py` and `backend/app/api/v1/findings.py`, then register the router in `backend/app/api/main.py`; implement `/executions/{execution_id}/findings`, `/executions/{execution_id}/repositories/{repository_execution_id}/findings`, and `/findings/{finding_id}` with existing page/pageSize and Problem Details conventions.
- [X] T023 [US3] Add Finding API client types and list fetching in `src/features/executions/api/findingsApi.ts` and `src/features/executions/types/finding.ts`, reusing the current normalized API error/loading pattern and passing the existing execution/repository identifiers without querying live Monitoring Configuration data.
- [X] T024 [US3] Replace the Feature 007/008 placeholder in `src/features/executions/components/ExecutionFindingsSection.tsx` with the accessible persisted findings list; display rule, historical repository path, optional file/line, commit hash, author email or safe identity state, warning severity, safe summary, and timestamps; show an honest zero-result state distinct from loading/error.
- [X] T025 [US3] Integrate `ExecutionFindingsSection` with the existing selected execution context in `src/features/executions/pages/ExecutionDashboardPage.tsx` and add dashboard-level navigation/refetch/accessibility assertions in `src/test/features/executions/execution-findings.test.tsx`; preserve existing tabs, dashboard route, layout, and refresh behavior.

**Checkpoint**: Persisted findings are queryable and visible from normal execution history/dashboard navigation.

## Phase 6: User Story 4 - Preserve checkpoints and historical findings through failures (Priority: P1)

**Goal**: Prove repository failure isolation, transactional rollback, historical immutability, and idempotency under retries or partial provider results.

**Independent Test**: Inject failures before and during the repository result transaction; the failed repository retains its previous checkpoint and old findings, writes no uncommitted findings/counts, and unrelated repository workers complete normally.

### Tests for User Story 4

- [X] T026 [P] [US4] Add deterministic application failure tests in `backend/tests/unit/application/test_process_repository_findings_failures.py` for commit API timeout, forbidden/not-found, malformed response, rule failure, finding insert failure, checkpoint update failure, range overflow, and history rewrite; assert old checkpoint and previously committed findings remain unchanged and other repositories continue.
- [ ] T027 [P] [US4] Add PostgreSQL integration tests in `backend/tests/integration/test_finding_checkpoint_transactions.py` for checkpoint uniqueness, Finding uniqueness, transaction rollback across Finding/count/checkpoint writes, retained historical rows, and concurrent persistence protection using `TEST_DATABASE_URL` only.

### Implementation for User Story 4

- [X] T028 [US4] Harden the repository result transaction and safe failure mapping in `backend/app/application/use_cases/process_repository.py` plus the affected UOW implementation in `backend/app/infrastructure/database/sqlalchemy_repositories.py`; rollback all candidate Findings, count changes, and checkpoint advancement together, then persist only normalized RepositoryExecution failure state in a separate short transaction.
- [ ] T029 [US4] Add PostgreSQL migration upgrade/downgrade validation in `backend/tests/integration/test_finding_checkpoint_transactions.py` against `backend/alembic/versions/0008_mining_findings.py`; verify the project migration harness can create and reverse the Feature 010 schema while preserving pre-existing execution history.

**Checkpoint**: A failed or interrupted mining attempt cannot lose unprocessed commits, corrupt counts, or rewrite existing findings.

## Phase 7: Polish and Cross-Cutting Validation

**Purpose**: Validate traceability, security, and end-to-end readiness without expanding scope.

- [X] T030 [P] Update `specs/010-mining-findings/quickstart.md` and `specs/010-mining-findings/contracts/` if implementation-compatible details change; keep only approved API fields, safe error codes, and commit-range semantics documented.
- [X] T031 Run backend unit/domain/application/API/provider adapter tests from `backend/` and record exact results in the implementation report; do not mark PostgreSQL integration as passed unless `TEST_DATABASE_URL` tests actually run.
- [X] T032 Run the frontend findings/configuration and accessibility commands defined in `package.json` from the repository root; record exact results and correct implementation regressions before completion.
- [X] T033 Run the frontend production build, Alembic migration validation, and the Feature 010 quickstart scenarios; report PostgreSQL-only checks as pending when `TEST_DATABASE_URL` is unavailable.
- [X] T034 [US1] Document and verify the local Feature 010 runtime refresh in `specs/010-mining-findings/quickstart.md` and `plan.md`: rebuild/recreate the backend, confirm its configuration and findings API contracts, and smoke-test configuration creation with normalized allowed-author emails; remove the temporary smoke-test configuration.

## Dependencies and Execution Order

### Phase dependencies

- Setup T001 precedes mining range tests/implementation.
- Foundational T002â€“T003 block all user stories because configuration storage, Finding/checkpoint persistence shape, and normalized rule results are shared contracts.
- US1 T004â€“T009 precedes US2 rule execution because the immutable execution allowlist must exist before author evaluation.
- US2 T010â€“T018 creates findings and counters; US3 reads/rendering and US4 atomicity checks depend on these persisted results.
- US3 and US4 both depend on US2. They touch separate API/UI and persistence/failure code after the core pipeline is stable; execute only tasks marked `[P]` together.
- Polish T030â€“T033 follows all required stories.

### Task dependency graph

```text
T001 â”€â”
T002 â”€â”¼â”€> T004/T005 -> T006 -> T007 -> T008 -> T009
T003 â”€â”˜                                  |
                                         v
T010 + T011 + T012 -> T013 -> T014 -> T015 -> T016 -> T017 -> T018
                                                        |          |
                                                        |          +-> T019/T020 -> T021 -> T022 -> T023 -> T024 -> T025
                                                        +-> T026 -> T028
T027 PostgreSQL integration tests depend on T016/T017; T026 + T027 -> T028 -> T029.
T030-T033 follow all stories; T034 follows runtime/build validation and records the Compose smoke check.
```

Explicit task edges: T002 before T003; T004/T005 before T006â€“T009; T006 before T007/T008; T007/T008 before T009; T010/T011/T012 before T013â€“T017; T013 before T014; T014/T015 before T016/T017; T016 before T017; T017 before T018/T026/T027; T019/T020 before T021â€“T025; T021 before T022; T022 before T023; T023 before T024; T024 before T025; T026/T027 before T028; T028 before T029; all story work before T030â€“T033; T030â€“T033 before T034.

### Parallel opportunities

- T004 and T005 can run in parallel because they edit separate domain/snapshot tests and API tests.
- T010, T011, and T012 can run in parallel because their test modules are separate; implementation starts only after their contracts are reconciled.
- T019 and T020 can run in parallel because backend API tests and frontend tests are separate files.
- T026 and T027 can be authored in parallel after T017 because they use separate test modules; T028 implementation depends on both test tasks and PostgreSQL integration must use an isolated test database.
- T015 and T016 have separate adapter and persistence files, but the task IDs retain a conservative serial sequence; T017 depends on both.
- T025 depends on T024 because the dashboard page integration must consume the completed Findings section component.

## Requirement-to-Task Traceability

| Requirement | Tasks |
|---|---|
| FR-001â€“FR-003 | T002â€“T003, T016â€“T017, T021â€“T022 |
| FR-004â€“FR-007 | T002, T004â€“T009, T014 |
| Runtime configuration contract verification | T034 |
| FR-008 | T003, T010, T013â€“T017 |
| FR-009â€“FR-013 | T011â€“T017, T026â€“T029 |
| FR-014â€“FR-015 | T001, T011, T015, T017 |
| FR-016â€“FR-018 | T012, T016â€“T018, T026â€“T029 |
| FR-019 | T003, T010, T014, T022â€“T024 |
| FR-020â€“FR-021 | T019, T021â€“T023 |
| FR-022â€“FR-023 | T020, T023â€“T025 |
| FR-024 | T007, T018 |
| FR-025â€“FR-028 | T011, T015â€“T017, T019, T026â€“T033 |
| SC-001â€“SC-002 | T010â€“T018 |
| SC-003â€“SC-005 | T001, T011â€“T018, T026â€“T029 |
| SC-006 | T019â€“T025 |
| SC-007 | T004â€“T009, T012, T018 |
| Local runtime contract smoke check | T034 |

## Implementation Strategy

### MVP

Complete T001â€“T018: configure policy, capture snapshots, establish baseline, detect incremental unauthorized authors, persist findings/checkpoints, and reconcile real counters. This delivers the core backend value before dashboard exposure.

### Incremental delivery

1. Foundation + US1: author policy is editable and historically captured.
2. US2: one real deterministic Finding rule runs through manual and scheduled executions.
3. US3: Findings are readable through APIs and the existing dashboard.
4. US4: failure/rollback and PostgreSQL concurrency evidence closes the historical integrity boundary.

## Notes

- Feature 008 `RepositorySummaryRule` stays supported and does not produce Findings.
- Finding is immutable and has no triage workflow.
- Feature 009 scheduler and Feature 008 bounded repository worker behavior remain unchanged.
- No AI, semantic analysis, notifications, realtime transport, distributed workers, or new mining pipeline is in scope.
- `checklists/mining-findings.md` is reviewer-owned; implementation must not change its approval markers.
