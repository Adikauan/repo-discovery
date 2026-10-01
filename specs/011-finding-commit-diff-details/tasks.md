---

description: "Dependency-ordered task list for Feature 011"
---

# Tasks: Finding Commit Diff Details

**Input**: Design documents from `specs/011-finding-commit-diff-details/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/finding-commit-diff-api.md

**Tests**: Required by spec. Tasks include domain/application/API/provider/frontend/accessibility test coverage.

**Organization**: Tasks are grouped by user story. Sequential task IDs also follow dependency order.

## Phase 1: Setup

- [X] T001 Add centralized commit-diff response limits and normalized per-file/response value objects in `backend/app/config.py` and `backend/app/domain/value_objects/commit_diff.py`; defaults MUST be 100 files, 256 KiB per-file UTF-8 diff text, 2 MiB cumulative UTF-8 diff text, 4096 UTF-8 bytes per repository/old/new path, and 200 UTF-8 bytes per repository name. Preserve Feature 010 Finding metadata bounds (64-character SHA, 254-character email, 200-code-point author name, 500-code-point message). Define `total_diff_bytes` as the sum of UTF-8 byte lengths of non-null normalized `diff` fields only; exclude JSON/HTTP serialization and all metadata. Model list completeness as `complete|truncated|unknown` and per-file `diff_truncated` independently, without persistence (FR-011–FR-013, FR-012a).

## Phase 2: Foundational

- [X] T002 [P] Add value-object tests in `backend/tests/unit/domain/test_commit_diff.py` for diff-text totals below, exactly at, and over budget; metadata not consuming diff-text budget; deterministic UTF-8 byte clipping; path bounds; unknown change type; empty text; and independent completeness/per-file truncation states (FR-003–FR-004, FR-011–FR-013, FR-012a).
- [X] T003 Define a normalized commit-diff operation on the existing GitLab repository client port in `backend/app/application/ports/gitlab_repository_client.py`; accept only server-derived project ID and Finding commit SHA and return normalized file metadata, never provider DTOs (FR-005–FR-007, FR-019).

## Phase 3: User Story 1 - Inspect an unauthorized commit (Priority: P1)

**Goal**: A user can request and read changed-file details for the exact commit represented by a persisted Unauthorized Commit Author Finding.

**Independent Test**: With persisted Finding/RepositoryExecution/snapshot fixtures and mocked GitLab responses, verify commit metadata and normalized changed files are returned using the stored project and SHA, including add/modify/delete/rename paths.

- [X] T004 [P] [US1] Add GitLab adapter tests in `backend/tests/unit/infrastructure/gitlab/test_http_gitlab_repository_client.py` for changed-file mapping, add/modify/delete/rename flags, provider order, completeness confirmed/explicitly truncated/unavailable mapping to `complete`/`truncated`/`unknown`, provider-limit behavior where supported, and malformed response normalization (FR-003, FR-006, FR-012, FR-012a).
- [X] T005 [US1] Extend `backend/app/infrastructure/gitlab/http_gitlab_repository_client.py` to call GitLab `GET /projects/:id/repository/commits/:sha/diff`, map provider paths/type/diff/collapsed/too_large attributes and reliable list-completeness evidence to normalized models, use `unknown` if evidence is absent, and keep raw payloads inside infrastructure (FR-003, FR-006, FR-012, FR-012a).
- [X] T006 [P] [US1] Add application query tests in `backend/tests/unit/application/test_get_finding_commit_diff.py` for persisted commit metadata, ownership traversal, provider lookup with stored SHA/project ID, unsupported rule/missing SHA, and independent Finding retention after lookup failure (FR-001–FR-008, FR-010).
- [X] T007 [US1] Implement `backend/app/application/use_cases/get_finding_commit_diff.py` to resolve the persisted Finding → RepositoryExecution → MiningExecution snapshot, reject unsupported/missing identity, validate historical GitLab instance identity before credential resolution/provider access, invoke the port with stored project ID/SHA, and return normalized bounded details without mutating records (FR-005–FR-010, FR-017, FR-019).
- [X] T008 [P] [US1] Add API contract tests in `backend/tests/api/test_finding_commit_diff.py` for successful response fields, not found, not applicable, ownership-derived metadata, exact route, and safe DTO shape (FR-002–FR-007, FR-019).
- [X] T009 [US1] Add safe diff response schemas and `GET /api/v1/findings/{finding_id}/diff` in `backend/app/api/v1/finding_schemas.py` and `backend/app/api/v1/findings.py`; accept no provider lookup parameters and use existing Problem Details conventions (FR-005, FR-010, FR-019).

**Checkpoint**: A persisted commit Finding can be resolved to a normalized changed-file response through a read-only, Finding-owned API.

## Phase 4: User Story 2 - Understand partial data and retrieval failures (Priority: P1)

**Goal**: Users receive bounded and truthful file details even when provider limits, application limits, binary/no-text changes, credentials, or provider access prevent a complete diff.

**Independent Test**: Mock provider and connection failures plus oversized, binary/no-text, collapsed, too-large, and truncated patches; verify explicit safe states, payload limits, no secret disclosure, and a retryable UI-facing error contract.

- [X] T010 [P] [US2] Extend `backend/tests/unit/application/test_get_finding_commit_diff.py` with cumulative diff-text budget below/equal/over-limit cases; prove paths, commit metadata and other fields do not consume the budget; assert deterministic provider-order clipping and UTF-8 byte counting; and cover file-count bounds plus provider completeness `complete`, `truncated`, and `unknown` (FR-011–FR-013, FR-012a).
- [X] T011 [P] [US2] Extend `backend/tests/api/test_finding_commit_diff.py` with credential-missing, instance-mismatch/no-provider-call, commit-not-found, forbidden, timeout, malformed response, unavailable provider, no arbitrary client IDs, and no credential/header/raw exception/body leakage assertions (FR-005, FR-008–FR-010).
- [X] T012 [US2] Complete normalized failure mapping and bounded-result behavior in `backend/app/application/use_cases/get_finding_commit_diff.py` and `backend/app/domain/value_objects/commit_diff.py`; compute the budget only from UTF-8 bytes in returned `diff` fields, preserve bounded metadata, clip deterministically at valid UTF-8 boundaries, set per-file `diff_truncated`, and derive list completeness as `complete`, `truncated`, or `unknown` only from evidence (FR-010–FR-013, FR-012a).
- [X] T013 [US2] Complete provider limit/pagination behavior in `backend/app/infrastructure/gitlab/http_gitlab_repository_client.py`; report `complete` only with reliable completeness evidence, `truncated` only with evidence of omitted entries, otherwise `unknown`, and normalize transport/status/malformed payload errors without raw details (FR-006, FR-010, FR-012, FR-012a).

**Checkpoint**: Per-file and total output is bounded; provider limitations and errors are safe and explicit without changing persisted Findings.

## Phase 5: User Story 3 - Inspect diffs in the execution dashboard (Priority: P1)

**Goal**: Users open one Finding's commit details in an accessible, responsive dialog without eager diff requests or losing the Findings list.

**Independent Test**: Render a populated Findings tab and verify no request occurs until “View diff” is activated; verify metadata, file selection, text states, retry, dialog keyboard/focus behavior, and narrow layout.

- [X] T014 [P] [US3] Add frontend normalized response types, including `filesCompleteness: 'complete' | 'truncated' | 'unknown'`, per-file `diffTruncated` and path clipping flags, repository name/path clipping flags, and an on-demand client method in `src/features/executions/types/findingDiff.ts` and `src/features/executions/api/findingsApi.ts`; request only `/findings/{findingId}/diff` with no provider lookup identifiers (FR-005, FR-014, FR-019, FR-012a).
- [X] T015 [P] [US3] Add dialog interaction/accessibility tests in `src/test/features/executions/finding-commit-diff.test.tsx` for no eager request, loading/error/retry, commit metadata/file selection/line markers, `complete` with no completeness warning, `truncated` with factual omitted-files warning, `unknown` with informational uncertainty, per-file clipping, Escape/close/focus return, and narrow viewport (FR-001–FR-004, FR-013–FR-016, FR-012a).
- [X] T016 [US3] Extend `src/features/executions/components/ExecutionFindingsSection.tsx` with a “View diff” action and responsive accessible dialog that fetches on explicit open, retains Finding data, prevents duplicate in-flight calls, supports retry/close, and renders changed-file diffs plus bounded path metadata. Show no completeness warning for `complete`, factual omitted-files warning for `truncated`, and calm informational uncertainty for `unknown`; render per-file diff clipping/collapsed/too-large/binary state separately (FR-001–FR-004, FR-011–FR-016, FR-012a).
- [X] T017 [US3] Add/adjust dashboard accessibility assertions in `src/test/features/executions/execution-accessibility.test.tsx` and run the relevant feature accessibility checks for dialog title, focus entry/return, keyboard operation, and perceivable loading/errors without altering reviewer checklist state (FR-014–FR-016).

## Phase 6: Polish and Cross-Cutting Validation

- [X] T018 Review `spec.md`, `plan.md`, `data-model.md`, `contracts/finding-commit-diff-api.md`, `quickstart.md`, and `tasks.md` for traceability and scope; verify no migration/persistence, diff prefetch, detection-rule changes, code-review workflow, or AI scope was introduced (FR-001–FR-019).
- [X] T019 Run the backend adapter/application/API tests, frontend Finding diff tests, full frontend test suite, accessibility checks, and production build using `package.json`; record actual results in the implementation report without claiming unrun PostgreSQL validation (SC-001–SC-007).

**Implementation validation note (2026-09-30)**: Feature-specific backend domain, application, GitLab adapter, config, and API tests passed (77 passed). Frontend Finding diff and accessibility tests passed (14 passed), the complete frontend suite passed (159 tests across 41 files), and `npm run build` passed. Vitest was run with a temporary validation config and thread pool because the default config loader/process pool is blocked by `spawn EPERM` in this environment. The build reported the existing large-chunk advisory. `TEST_DATABASE_URL` was not available; no PostgreSQL integration validation was claimed.

## Dependencies and Execution Order

### Phase dependencies

- Setup T001 and foundational T002–T003 precede all user stories.
- US1 tasks T004–T009 establish normalized provider retrieval and the safe read API. T004 precedes T005; T006 precedes T007; T008 precedes T009. T005 and T007 can proceed independently after T003; API integration T009 depends on the query and adapter tasks.
- US2 depends on US1's endpoint/query. T010 and T011 can be authored in parallel after T009; T012 and T013 may proceed in parallel after those tests because they edit the application/domain bounder versus the infrastructure adapter.
- US3 depends on the normalized API/completeness contract finalized by US2. T014 and T015 can proceed in parallel after T013; T016 depends on T014 and T015. T017 follows T016. T018–T019 follow all stories.

### User story dependency notes

- US1 is the backend MVP and depends only on foundational normalized diff/port contracts.
- US2 extends the same normalized read path to define failure and bounded-result semantics; it depends on US1's endpoint/use case, not on frontend work.
- US3 consumes the established API contract. It does not alter mining rules or backend persistence. Dashboard integration follows its client and interaction tests.

### Parallel execution examples

```text
After T001:
  T002 and T003 may proceed independently (domain tests vs application port).

After T003:
  T004 and T006 can be prepared in parallel (adapter tests vs use-case tests).
  T005 and T007 touch different files and can proceed after their respective tests/port.

After T009:
  T010 and T011 can run in parallel (application bounds vs API security/error cases).
  T012 and T013 can run in parallel after those tests (application/domain normalization vs provider adapter).

After T012 and T013:
  T014 and T015 may be authored in parallel (client/types vs frontend interaction tests).
  T016 depends on T014 and T015; T017 follows T016.
```

No parallel example assigns multiple tasks to the same implementation file at once.

## Requirement-to-Task Traceability

| Requirement | Tasks |
|---|---|
| FR-001–FR-004: finding action, commit metadata, changed-file details, readable per-file line diffs | T006–T009, T015–T016 |
| FR-005–FR-007: persisted identity authority, normalized provider boundary, stored commit lookup | T003–T009, T014 |
| FR-008–FR-010: snapshot instance validation, secure credentials, safe errors | T006–T013 |
| FR-011–FR-013, FR-012a: diff-text budget, provider flags, explicit list completeness, binary/no-text states | T001–T005, T010–T016 |
| FR-014–FR-016: on-demand request, accessible responsive dialog | T014–T017 |
| FR-017–FR-019: no persistence, scope exclusions, safe public DTO | T001, T007–T009, T014, T018 |
| SC-001–SC-007: user-visible diff, request timing, security, bounds, partial honesty, accessibility, Finding retention | T006–T019 |

## Implementation Strategy

1. Complete T001–T003 as shared contract foundations.
2. Deliver US1 backend endpoint and mocked contract tests as the first independently demonstrable increment.
3. Complete US2 bounds and normalized failure handling before UI integration.
4. Deliver US3 dialog with on-demand fetching; zero migrations and no change to mining execution.
5. Run cross-cutting validation and document environment-dependent limitations accurately.

**MVP**: US1 produces a secure normalized read endpoint for a persisted Unauthorized Commit Author Finding; the user-facing feature is complete after US3 integrates the dialog.

## Notes

- All tasks use `- [ ] T### [P?] [US#?] Description with file path` format.
- [P] indicates file-safe parallel work; numeric ordering follows the dependency graph.
- Feature 011 adds no PostgreSQL schema changes.
- No Feature 008/009 pipeline changes, new finding rules, code review workflows, or AI functionality are in scope.

