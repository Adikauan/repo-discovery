# Tasks: Repository & Branch Author Policies

**Input**: Design documents from `/specs/014-repository-branch-author-policies/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Required by Feature 014; cover domain policy semantics, API scope/security, PostgreSQL constraints/migrations, snapshot integrity, shared mining pipeline, frontend interactions, and accessibility.

**Organization**: Tasks are ordered by user story and explicit dependency. Story references map to spec User Stories 1–4.

## Phase 1: Setup

- [X] T001 [P] Add Feature 014 policy, branch discovery, and PostgreSQL test fixture helpers in `backend/tests/conftest.py`.
- [X] T002 [P] Add scope-derived author policy frontend fixture types/data in `src/features/monitoring-configurations/fixtures/wizardFixtures.ts`.

## Phase 2: Foundational Model, Migration, and Snapshot Support

**Purpose**: Establish policy identity, normalization, persistence, concurrency, and historical snapshot contracts required by all stories.

- [X] T003 Add AuthorPolicy and AuthorPolicyAuthor domain validation tests for group/repository-branch shape, normalized author uniqueness, and explicit empty policy in `backend/tests/unit/test_author_policies.py`.
- [X] T004 Implement policy scope types, stable GitLab instance identity, author normalization reuse, and explicit empty-policy representation in `backend/app/domain/author_policy.py`.
- [X] T005 Add PostgreSQL model constraint tests for policy identity uniqueness, scope shape checks, and duplicate author rejection in `backend/tests/integration/test_author_policy_persistence.py`.
- [X] T006 Add AuthorPolicy and AuthorPolicyAuthor relational mappings, partial unique indexes, checks, and repository/UOW support in `backend/app/infrastructure/database/models.py` and `backend/app/infrastructure/database/sqlalchemy_repositories.py`.
- [X] T007 Create Alembic migration `backend/alembic/versions/0009_author_policies.py` adding `author_policy_mode` with `legacy` default and policy tables/indexes while preserving `allowed_author_emails`, MiningExecutions, Findings, and checkpoints.
- [X] T008 Add V1 historical snapshot compatibility and V2 capture tests in `backend/tests/unit/test_execution_snapshot.py`, including repository-to-selected-Group coverage and hierarchy distances required for closest-ancestor resolution.
- [X] T009 Implement immutable V2 execution policy snapshot values, deterministic Group coverage/distance capture, and V1 deserialization compatibility in `backend/app/domain/entities/execution_snapshot.py`.
- [X] T010 Add immutable resolver unit tests in `backend/tests/unit/test_author_policy_resolution.py` for parent-only, child-only, overlapping parent+child, closest child winning, exact Repository + Branch overriding both, no union/intersection, equal-specificity ambiguity failing safely, legacy fallback, disabled missing policy, and explicit empty policy.
- [X] T011 Implement pure closest-ancestor Group resolution in `backend/app/domain/services/author_policy_resolver.py`; exact Repository + Branch wins, otherwise smallest snapshotted hierarchy distance wins, lists are never combined, and unresolved equal-specificity ties return normalized `author_policy_ambiguous` without selecting arbitrarily.
- [X] T012 Add author policy repository/application ports and wire the UOW without holding transactions across provider calls in `backend/app/application/ports/author_policy_repository.py` and `backend/app/application/ports/monitoring_configuration_repository.py`.

## Phase 3: User Story 1 - Configure Repository Branch Policies (Priority: P1)

**Goal**: Configure separate normalized author allowlists for actual discovered branches of directly selected repositories.

**Independent Test**: Select one repository, discover branches from mocked GitLab pages, save different lists for two branches, reopen policy state, and reject out-of-scope repository IDs before provider access.

- [X] T013 [P] [US1] Add normalized GitLab branch model and branch-list operation contract tests, including pagination, empty results, deleted branch, malformed response, timeout, forbidden, and no credential exposure in `backend/tests/unit/test_gitlab_repository_branches.py`.
- [X] T014 [US1] Extend the GitLab repository client port with complete paginated branch listing in `backend/app/application/ports/gitlab_repository_client.py`.
- [X] T015 [US1] Implement normalized paginated GitLab branch retrieval and safe error mapping in `backend/app/infrastructure/gitlab/http_gitlab_repository_client.py`.
- [X] T016 [US1] Add branch discovery use-case tests for configuration ownership, direct selected-repository scope, instance fingerprint validation, credential resolution, and no provider call for invalid scope in `backend/tests/unit/test_list_repository_branches.py`.
- [X] T017 [US1] Implement scoped branch discovery with minimum-lifetime credential decryption and normalized output in `backend/app/application/use_cases/list_repository_branches.py`.
- [X] T018 [US1] Add branch discovery and repository-branch policy API contract tests for request shape, scope rejection, safe Problem Details, and `If-Match` stale writes in `backend/tests/api/test_author_policies.py`.
- [X] T019 [US1] Define additive policy/branch request and response schemas in `backend/app/api/v1/author_policy_schemas.py`.
- [X] T020 [US1] Implement repository-branch policy read/upsert/delete use cases with exact branch identity, scope validation, normalization, and configuration revision CAS in `backend/app/application/use_cases/author_policies.py`.
- [X] T021 [US1] Implement policy and branch discovery routes under `/api/v1/monitoring-configurations/{configuration_id}/author-policies` in `backend/app/api/v1/author_policies.py` and register them in `backend/app/api/v1/main.py`.
- [X] T022 [US1] Add typed policy/branch API client functions and models in `src/features/monitoring-configurations/api/authorPoliciesApi.ts` and `src/features/monitoring-configurations/types/authorPolicies.ts`.
- [X] T023 [US1] Add repository branch policy UI tests in `src/test/features/monitoring-configurations/author-policies.test.tsx` for scope-derived rows, discovered branches, unavailable retained branches, policy-only request payload, latest-revision retry after partial save, and inactive identities.
- [X] T024 [US1] Implement repository branch policy cards, GitLab branch discovery, branch-scope explanatory helper text, and distinct normalized author chips per branch in `src/features/monitoring-configurations/pages/AuthorPoliciesPage.tsx`; submit authorization policies only, never mining branch selection.

## Phase 4: User Story 2 - Configure Dynamic Group Policies (Priority: P1)

**Goal**: Configure policy against a selected stable Group identity without branch selection or static expansion of descendant repositories.

**Independent Test**: Save a Group policy, change dynamic descendants, and verify the policy remains keyed to Group identity and the UI communicates branch N/A.

- [X] T025 [P] [US2] Add Group policy scope validation, no-branch-shape, inactive retention, and dynamic identity API tests in `backend/tests/api/test_author_policies.py`.
- [X] T026 [US2] Complete Group policy GET/upsert behavior using stable selected group ID and existing author policy application service in `backend/app/application/use_cases/author_policies.py`.
- [X] T027 [US2] Add Group policy and accessibility coverage, including branch-not-applicable wording, in `src/test/features/monitoring-configurations/author-policies-accessibility.test.tsx`.
- [X] T028 [US2] Implement Group policy presentation and per-Group author chips without a branch selector in `src/features/monitoring-configurations/pages/AuthorPoliciesPage.tsx`.
- [X] T029 [US2] Add inactive retained policy presentation and deletion tests in `src/test/features/monitoring-configurations/author-policies.test.tsx`, asserting stable identity and no reassignment.
- [X] T030 [US2] Integrate Group and repository policy cards from saved GitLab scope, including inactive policies, in `src/features/monitoring-configurations/pages/AuthorPoliciesPage.tsx`.

## Phase 5: User Story 3 - Apply Policies in the Existing Mining Pipeline (Priority: P1)

**Goal**: Apply snapshot-bound policy resolution for commits while preserving the existing rule, Finding type, checkpoint behavior, and manual/scheduled pipeline.

**Independent Test**: Run Feature 008 repository processing with snapshot policies and mocked commit ranges; verify authorized commits create no Finding, unauthorized commits create the existing Finding with branch context, and failures do not advance checkpoints.

- [X] T031 [P] [US3] Add process-repository regression tests in `backend/tests/unit/test_process_repository.py` proving policy configuration does not alter existing branch selection, non-processed branch policies are ignored, the processed-branch policy applies, exact Repository + Branch and closest Group semantics are used, equal-specificity ambiguity fails safely, and legacy/missing/empty policy modes remain correct.
- [X] T032 [US3] Add branch-availability tests in `backend/tests/unit/test_process_repository.py` proving an unavailable policy for an unprocessed branch is ignored, while an unavailable branch selected by existing mining semantics fails safely without rule/checkpoint advancement.
- [X] T033 [US3] Preserve existing processed-branch selection and ensure only the actually processed branch is required for policy resolution in `backend/app/application/use_cases/process_repository.py`; do not preflight/fail on unrelated unprocessed branch policies.
- [X] T034 [US3] Pass snapshot policy context, resolved dynamic Group coverage/hierarchy distance, and actual processed branch to the existing Unauthorized Commit Author rule in `backend/app/application/use_cases/process_repository.py` and `backend/app/domain/services/unauthorized_commit_author_rule.py`; map ambiguous policy state to safe repository failure and structured secret-free logging.
- [X] T035 [US3] Add Finding API branch projection tests in `backend/tests/api/test_findings.py` and `backend/tests/unit/test_list_execution_findings.py` proving branch is derived from immutable RepositoryExecution context and is nullable for legacy data without new Finding persistence.
- [X] T036 [US3] Add nullable historical `branch` to Finding response projections from the owning RepositoryExecution in `backend/app/api/v1/finding_schemas.py` and `backend/app/application/use_cases/list_execution_findings.py`; never look up current GitLab branch state.
- [X] T037 [US3] Add manual/scheduled shared-pipeline regression tests across `backend/tests/unit/application/test_process_mining_execution.py`, `backend/tests/unit/application/test_create_mining_execution.py`, and `backend/tests/unit/test_author_policy_resolution.py` for captured policies, dynamic Group ancestry, immutable history, unchanged Finding type/idempotency, no multi-branch expansion, and checkpoint preservation after policy edits.

## Phase 6: User Story 4 - Preserve Legacy Configuration and Historical Records (Priority: P2)

**Goal**: Keep the Feature 010 global list as fallback until an explicit per-configuration migration to scoped mode, without rewriting history or losing legacy data.

**Independent Test**: Existing legacy configuration uses its snapshot-bound list where no scoped policy matches; explicit mode migration preserves stored legacy emails and changes only future execution resolution.

- [X] T038 [P] [US4] Add PostgreSQL persistence/history tests for legacy policy state, policy table constraints, and unchanged snapshots/findings/checkpoints in `backend/tests/integration/test_author_policy_persistence.py` and `backend/tests/integration/test_author_policy_history.py`.
- [X] T039 [US4] Add optimistic migration-mode transition tests for `If-Match`, stale revisions, one-way transition, and retained legacy email values in `backend/tests/api/test_author_policies.py`.
- [X] T040 [US4] Implement explicit idempotent legacy-to-scope-aware mode transition under Monitoring Configuration revision CAS in `backend/app/application/use_cases/migrate_author_policy_mode.py` and `backend/app/api/v1/author_policies.py`.
- [X] T041 [US4] Add legacy fallback and post-migration no-policy behavior to execution snapshot/application tests while preserving V1 snapshot semantics in `backend/tests/unit/test_execution_snapshot.py` and `backend/tests/unit/test_process_repository.py`.
- [X] T042 [US4] Add legacy UI tests in `src/test/features/monitoring-configurations/author-policies.test.tsx` proving the old multiline textarea is absent, fallback data is clearly labeled/read-only in legacy mode, transition is explicit and one-way, and legacy values are neither resubmitted nor deleted.
- [X] T043 [US4] Implement the scope-policy primary editor, clearly labeled read-only legacy fallback, explicit mode-transition warning, and per-configuration migration in `src/features/monitoring-configurations/pages/AuthorPoliciesPage.tsx` and `src/features/monitoring-configurations/api/authorPoliciesApi.ts`.

## Phase 7: Integration, Accessibility, and Validation

- [X] T044 Add cross-story API compatibility tests proving existing Monitoring Configuration write fields/meanings remain compatible and new policy routes are additive in `backend/tests/api/test_author_policies.py` and `backend/tests/api/test_monitoring_configurations.py`.
- [X] T045 Add axe accessibility coverage for the Authors editor, labelled email input, policy context, and actions in `src/test/features/monitoring-configurations/author-policies-accessibility.test.tsx`.
- [X] T046 [US3] Add Findings UI tests in `src/test/features/executions/execution-findings.test.tsx` proving branch is shown from the historical API response and legacy missing branch uses a safe unavailable label.
- [X] T047 [US3] Render the nullable historical Finding branch in the Execution Findings presentation in `src/features/executions/components/ExecutionFindingsSection.tsx`; use API data only and never query GitLab to render a historical Finding.
- [X] T048 [US4] Add Authors navigation, unsaved-state, and save-retry tests in `src/test/features/monitoring-configurations/author-policies.test.tsx` for Scope → Authors → Scheduling and safe partial-save behavior.
- [X] T049 [US4] Integrate the saved Authors page into wizard navigation and route lifecycle in `src/features/monitoring-configurations/pages/AuthorPoliciesPage.tsx`, `src/features/monitoring-configurations/components/ConfigurationWizardProgress.tsx`, and `src/app/routes/routeConfig.tsx`.
- [X] T050 [US4] Add Authors-step reachability, loading, scope-aware editing, legacy fallback preservation, and no accidental legacy submission coverage in `src/test/features/monitoring-configurations/author-policies.test.tsx` and `src/test/features/monitoring-configurations/feature013-list-and-author-preview.test.tsx`.
- [X] T051 Run Feature 014 PostgreSQL migration, uniqueness, transaction, and stale-write integration validation using `TEST_DATABASE_URL`; record the result in `specs/014-repository-branch-author-policies/quickstart.md`.
- [X] T052 Run backend domain/application/API/mocked-GitLab regression suite and frontend tests/build for Features 010/013/014; record actual commands/results in `specs/014-repository-branch-author-policies/quickstart.md`.
- [ ] T053 Perform manual visual validation against `specs/014-repository-branch-author-policies/references/06-author-policies.png` and `03-new-configuration-general.png` for scope grouping, branch selectors, author chips, Group branch N/A, legacy transition, responsive layout, and wizard consistency; leave open if not actually performed.

## Dependencies and Execution Order

- Phase 1 setup precedes all implementation phases.
- Phase 2 model, migration, repository ports, snapshot V2, and resolver precede policy APIs and mining integration.
- User Story 1 depends on T006–T007 and T012; API/UI integration depends on branch discovery and policy contracts.
- User Story 2 reuses the policy model and use cases from User Story 1; its Group identity and UI must not add a static repository expansion.
- User Story 3 depends on snapshot V2 (T008–T009), pure closest-ancestor resolver and ambiguity behavior (T010–T011), and branch discovery API support (T014–T021) before branch selector integration (T023–T024). Mining integration T034 follows resolver T011. Finding branch UI work T046–T047 depends on API projection T035–T036.
- User Story 4 depends on `author_policy_mode` and migration from T006–T007, snapshot/mining integration from T009/T034, and the policy APIs. Legacy UI migration T043 follows migration tests and mode transition (T038–T040), with tests T042 before that UI change. Wizard navigation tests/implementation (T048–T049) depend on policy integration T030 and legacy behavior T043; end-to-end wizard tests T050 follow wizard integration T049.
- T051/T052/T053 are final PostgreSQL, automated regression/build, and manual visual validations after affected implementation tasks.
- Branch-policy UI/API work does not configure or submit mining branch selection; only a policy for the branch processed by existing mining behavior is evaluated.

## Parallel Opportunities

- T001 and T002 can run in parallel (separate test fixture files).
- T003 and T005 can run in parallel because domain and persistence test files differ; model implementation T004/T006 follows its corresponding tests.
- T013 and T018 can be authored in parallel; provider contract tests and API contract tests use separate files.
- T023 and T027 can be authored in parallel; repository and Group UI tests are separate files.
- T038 and T042 can be authored in parallel; PostgreSQL and frontend legacy tests are separate files.
- Do not parallelize tasks that edit `author_policies.py`, `process_repository.py`, `AuthorPoliciesStep.tsx`, `authorPoliciesApi.ts`, `ConfigurationWizard.tsx`, or shared API schemas.
- Finding branch projection/API work (T035-T036) precedes its UI tests/rendering (T046-T047). Authors navigation/save-retry tests (T048) and wizard integration (T049) depend on the policy UI/legacy behavior (T030/T043); end-to-end wizard regression (T050) follows integration T049.

## Independent Test Criteria by Story

- **US1**: Save two distinct policies for discovered branches on one directly selected project; reload them; reject out-of-scope IDs before GitLab requests.
- **US2**: Save a Group policy using stable Group ID; no branch field/selector exists; dynamic descendant changes do not rewrite the Group policy or static scope.
- **US3**: Manual and scheduled runs use captured scope-aware policy data in the existing pipeline; authorized authors create no Finding, unauthorized authors create the existing Finding, branch is historical, and checkpoints do not reset.
- **US4**: Legacy configurations retain Feature 010 behavior until the explicit transition; migration preserves old values and historical snapshots/findings/checkpoints.

## Implementation Strategy

Deliver foundational persistence and snapshot compatibility first, then repository branch policies as the first visible increment, followed by Group policies and shared mining resolution, and finally legacy transition/integration validation. Tests precede the corresponding domain, API, and UI implementation except that the wizard end-to-end test follows the wizard integration it exercises. PostgreSQL-specific claims require PostgreSQL execution; visual manual tasks remain open until reviewed against the references. Overlapping Group policies use the closest selected ancestor rule established in spec.md and the snapshot contract.

## Phase 8: Convergence

- [X] T054 Correct stale dependency references in the Parallel Opportunities summary to match current Finding branch and Authors wizard task IDs per tasks.md task ordering (partial)
