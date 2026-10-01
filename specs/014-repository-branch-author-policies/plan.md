# Implementation Plan: Repository & Branch Author Policies

**Branch**: `014-repository-branch-author-policies` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

## Summary

Replace the single global author allowlist as the long-term policy model with group and repository/branch policies while preserving the Feature 010 list as a temporary fallback. Add migration-managed policy persistence, GitLab branch discovery scoped to selected repositories, immutable execution-time policy snapshots, and a deterministic resolver used by the existing Unauthorized Commit Author rule. The current mining pipeline, processed-branch selection, checkpoint behavior, Finding type, and manual/scheduled execution path remain unchanged.

## Technical Context

**Language/Version**: Python 3.13–3.14 backend; TypeScript frontend  
**Primary Dependencies**: Existing FastAPI, Pydantic, SQLAlchemy, Alembic, HTTPX, React, React Router, Vite, Material UI, pytest, Vitest, Testing Library, axe-core  
**Storage**: PostgreSQL; Alembic-managed relational policy and normalized author records  
**Testing**: pytest domain/application/API/PostgreSQL integration tests; Vitest component/accessibility tests; `npm run test:run` and `npm run build`  
**Target Platform**: Existing RepoMiner web application/backend deployment  
**Project Type**: Full-stack web application using Clean Architecture  
**Performance Goals**: Preserve existing bounded repository processing and GitLab HTTP timeout/pagination behavior; branch discovery must follow all provider pages and must not fetch branch lists for unrelated scope items  
**Constraints**: Preserve Features 004/006/008/009/010/013; no branch-scope expansion, no checkpoint reset, no new Finding type, no secrets in policy/snapshot/log/API, no second mining pipeline  
**Scale/Scope**: Policy configuration for selected groups and selected repositories, multiple branch policies per repository, normalized email entries, current branch discovery and execution paths only

## Constitution Check

- **Clean Architecture and domain rules**: policy normalization and resolution remain domain/application behavior; provider calls remain behind the existing GitLab port; persistence remains in infrastructure.
- **Explicit contracts**: add version-compatible policy and branch-discovery REST contracts; preserve existing routes and semantics, and derive Finding branch context from existing `RepositoryExecution.processed_branch`.
- **External integration abstraction**: add paginated branch listing to the existing GitLab repository client; provider DTOs remain in the HTTP adapter.
- **Secure by construction**: resolve and decrypt the configured credential only within branch-discovery/mining use cases; never include credentials in policy records, snapshots, logs, or responses.
- **Immutable history and one pipeline**: capture normalized applicable policy context in each new execution snapshot; manual and scheduled execution continue through Feature 008's existing orchestrator and repository processor.
- **Lifecycle, migration, and verification**: Alembic migration retains global author data; PostgreSQL uniqueness/CAS behavior and tests cover policy persistence and snapshots.
- **Accessible reusable UX**: implement the Feature 013 Authors step using existing MUI form/chip/autocomplete patterns; preserve loading, empty, error, and keyboard behavior.

No constitution exception is required.

## Clarified Policy Resolution (Normative)

1. An exact repository + processed-branch policy overrides a matching selected-group policy.
2. If no exact repository/branch policy matches, select the most-specific applicable selected Group policy: the closest selected ancestor Group to the repository. Do not union or intersect lists. If equal specificity cannot be deterministically ordered, fail the RepositoryExecution with safe `author_policy_ambiguous` error metadata and log safe identifiers only.
3. A selected-group policy applies to dynamically included descendant repositories only for branches the existing mining pipeline already processes. It does not add repositories or branches to mining scope.
4. If no scope-specific repository/branch or group policy matches, use the legacy global allowlist while configuration mode is `legacy`; in `scope_aware` mode, disable Unauthorized Commit Author detection for that repository/branch.
5. An explicitly present policy with zero authors is distinct from no policy and treats every valid author email as unauthorized.
6. Existing global allowed-author lists remain persisted and are a configuration-level fallback until a user explicitly switches that configuration to `scope_aware`. The transition is a one-way mode change; the retained legacy values are not deleted.
7. A policy outside current selected scope remains stored and is shown inactive; it is never reassigned or applied to another entity. The same stable entity may reactivate the policy if reselected.
8. If the branch the repository processor is actually processing is configured but unavailable, fail that RepositoryExecution with a normalized safe branch error; do not substitute a branch or advance its checkpoint.
9. Branch discovery/policies do not change existing branch selection or introduce multi-branch mining. The Authors UI states that policies are authorization targets and apply only when existing mining behavior processes their branch.

## Design Decisions

### Domain and execution behavior

Add an `AuthorPolicy` aggregate with scope type `group` or `repository_branch`. The group identity is `(configuration_id, GitLab instance fingerprint, group_id)`; repository branch identity is `(configuration_id, GitLab instance fingerprint, project_id, exact branch name)`. The fingerprint prevents numeric IDs from crossing GitLab instances. Author values use the existing Feature 010 trim/case-insensitive normalization and deterministic sorting/deduplication. Domain resolution accepts a repository, processed branch, selected ancestor group IDs, scoped policy snapshot, policy mode, and legacy list; it performs no GitLab I/O.

Resolution first checks an exact repository/branch policy. If none exists, choose the closest applicable selected ancestor Group by snapshotted hierarchy distance (smallest distance wins). Never union/intersect Group lists. If multiple matches tie at the closest distance and no ancestor ordering resolves them, return normalized `author_policy_ambiguous` error metadata, fail only that RepositoryExecution, and do not advance its checkpoint. The immutable V2 snapshot carries repository-to-selected-Group coverage and distance so the resolver needs no live GitLab hierarchy call. Explicitly empty repository/branch or Group policies remain matches. If no scoped policy applies, use the legacy list in legacy mode; otherwise skip detection and continue successful processing/checkpointing without unauthorized-author candidates.

The mining pipeline processes the same selected/default branch that Feature 008/010 currently processes; Feature 014 does not introduce multi-branch mining. Stored policies for other branches do not cause branch traversal or checkpoint creation and remain valid but have no effect until existing mining semantics process that branch. The Authors step displays helper text that author policies do not change which branches are mined and apply only when an execution processes the corresponding branch; it provides no branch-mining controls. A deleted/inaccessible saved policy branch is shown unavailable. It does not fail execution when that branch is not processed. If the branch selected for processing by existing mining semantics is unavailable, fail that RepositoryExecution safely without substitution or checkpoint advancement. The policy for the branch actually processed is matched by exact branch name.

Normal unauthorized detections remain successful rule results and use the existing Finding identity/idempotency. `RepositoryExecution.processed_branch` is the historical branch context; Finding read projections add that existing value where needed, without storing a second branch field on Finding. The Execution Findings UI renders the response branch next to repository/commit context, shows a safe unavailable label for legacy records without it, and never queries current GitLab state to render history.

### Legacy transition

Add configuration-level `author_policy_mode` with `legacy` and `scope_aware` values, defaulting existing rows and newly created API configurations to `legacy` for compatibility. Scoped policy records can be added while in legacy mode and take precedence when they match; the legacy list is a fallback for unmatched repository/branch decisions. The Authors step presents the scope-aware policy UI as the primary editor and does not show the legacy multiline textarea. While mode is `legacy`, the old list is clearly identified and read-only as fallback; an explicit, one-way **Switch to scope policies** action warns that unmatched items will have detection disabled. The transition updates only mode/revision; it preserves the legacy list, existing policies, execution snapshots, findings, and checkpoints. Legacy values are never resubmitted through policy routes or silently erased. New executions snapshot mode, normalized legacy fallback values when mode is legacy, and active scoped policies. No historical snapshot migration is performed.

### Persistence and concurrency

Use a single `author_policies` table with constrained scope columns and `author_policy_authors` child rows. Check constraints enforce that group policies carry only a group ID, while repository-branch policies carry project ID and branch. PostgreSQL partial unique indexes enforce each stable identity. Policies use restrictive configuration ownership and are retained when their scope item is removed. The scope-active indicator is derived when reading policies against the saved scope; it is not stored as policy state. The one-way policy mode is stored on MonitoringConfiguration.

Policy mutations and mode transition use the existing Monitoring Configuration revision/ETag (`If-Match`) and optimistic update. They increment the same revision and run in a short transaction. Branch reads are non-mutating. They validate active configuration, current GitLab fingerprint, credential validation fingerprint, direct repository selection, and group/repository selected scope before contacting GitLab. No transaction is held over provider calls.

Create Alembic revision `0009_author_policies`: add mode column with compatibility default, policy table, normalized-author child table, checks, indexes, and foreign keys. Do not drop or rewrite `allowed_author_emails`; it remains the legacy fallback. Existing execution snapshot JSON and Finding rows are not rewritten.

### Branch discovery and API

Extend `GitLabRepositoryClient` with paginated normalized branch listing for a project ID. The endpoint receives configuration ID and selected project ID only. The use case verifies instance identity and explicit repository scope, resolves the secure saved credential, decrypts it for the call lifetime, and maps timeout, forbidden, not-found, invalid, and provider failures to safe errors. Return only branch name, commit SHA, and default flag needed by branch selection; credentials/provider payloads never cross the application/API boundary.

Use REST routes under `/api/v1/monitoring-configurations/{configuration_id}/author-policies`:

- `GET /` returns mode, policies, active/unavailable scope state, and current legacy fallback metadata needed for transition UX.
- `PUT /groups/{gitlab_group_id}` upserts the group allowlist after current selected-group validation.
- `PUT /repositories/{gitlab_project_id}/branches` upserts one exact branch policy using `branch` and normalized `allowed_author_emails` in the request body (branch names are not path segments).
- `DELETE /{policy_id}` removes one explicitly requested policy after configuration ownership and `If-Match` validation.
- `POST /migration` switches the configuration from legacy to scope-aware mode once, preserving legacy values.
- `GET /repositories/{gitlab_project_id}/branches` returns branch discovery for a directly selected repository.

Mutation requests carry `If-Match`; stale writes use the existing stale configuration Problem Details response. All existing API fields and write behavior stay compatible. Additive Finding `branch` projection is derived from the associated RepositoryExecution.

### Snapshot and mining integration

Introduce a versioned execution snapshot shape (V2) while keeping V1 parsing for historical executions. V2 captures author policy mode, normalized legacy fallback values only while in legacy mode, selected group policies keyed by group ID, selected direct-repository branch policies keyed by project ID and branch, and for each resolved project its selected Group coverage with hierarchy distance/ancestor ordering. This coverage supports deterministic closest-ancestor resolution without live GitLab calls. Only policies belonging to current selected scope are active in the captured author-policy set; inactive retained policies remain configuration data and are not applied. Snapshot construction is part of the same existing execution-creation transaction that freezes configuration and scope. Public snapshot DTOs do not gain internal policy metadata by default.

Pass snapshot policy context and actual processed branch to the existing `UnauthorizedCommitAuthorRule`; skip rule detection only when resolver returns no policy. Continue baseline/incremental checkpoint progression and preserve the checkpoint on all failures, including unavailability of the branch selected for processing. An unavailable policy for a branch not processed does not fail execution. Manual and scheduler-triggered executions have identical behavior because both call the same process use case.

### Frontend

Replace Feature 013's `FutureAuthorPolicyPreview` and the legacy global multiline textarea with an Authors editor in the existing five-step wizard. Derive all rows from the saved Scope step/API, load scope, policy state, mode, and legacy fallback state, and never add an independent scope picker. Preserve Scope → Authors → Scheduling navigation. Back navigation preserves unsaved state under existing wizard conventions; advancing validates and saves dirty policies first, remains on Authors with associated errors if save fails, and must not silently discard edits. Repository rows show identity, paginated branch autocomplete, and a distinct chip list per branch. Helper text states that author policies do not change which branches are mined and apply only when an execution processes that branch; no branch-mining control is submitted. Group rows show “Branches do not apply to groups” and their own chip list. In legacy mode the old list is clearly labeled read-only fallback data; it is not sent to policy endpoints or deleted. The explicit one-way transition switches future policy resolution and preserves the legacy values. After migration, the list may remain visible as inactive compatibility data. All mutations include the current configuration version and refresh on stale conflict.

Use MUI Autocomplete/Chip and existing WizardShell, FormSection, feedback, and accessibility conventions. Empty, loading, no branches, unavailable saved branch, provider failure/retry, validation, save failure, and stale-write states are explicit. Email chips normalize locally for immediate duplicate feedback but backend/domain normalization is authoritative. On narrow widths, policy fields wrap/stack without changing policy semantics. Execution Findings display the branch returned from the historical Finding projection next to repository/commit context, with a safe unavailable label for legacy records; no GitLab lookup is used to render old findings.

### Visual references

Use all Feature 014 images under `specs/014-repository-branch-author-policies/references/`:

- `01-home-dashboard.png`: only confirms the existing Feature 013 app shell, spacing, cards, and typography context; Home is not redesigned by Feature 014.
- `02-monitoring-configurations.png`: confirms existing list/shell context; not in this feature's implementation scope.
- `03-new-configuration-general.png`: confirms five-step wizard shell, navigation and card proportions.
- `06-author-policies.png`: primary UX reference for the Authors step, scope-item cards, repository branch selectors, per-branch email chips, group branch-not-applicable display, and add-author area.

Images guide layout only; values and apparent extra controls do not define policy precedence, branch coverage, or scope behavior.

### Test strategy

Add unit tests for normalized author identity and the pure resolver, including parent-only, child-only, parent+child, closest-child wins, repository/branch override, no union/intersection, and safe equal-specificity ambiguity failure. Use mocked GitLab branch endpoints and pagination for adapter/application/API tests. Validate authorization through manually and schedule-created executions in the shared pipeline; prove configured branches do not alter branch selection, unprocessed branch policies are ignored, and processed branch policies apply normally. Add PostgreSQL integration coverage for uniqueness, transactional author replacement, optimistic concurrency, migration defaults, and preservation of legacy data. Frontend tests cover scope-derived rows, branch-specific chip collections, group state, branch-scope helper text/no branch-mining API field, legacy textarea replacement and preservation, Scope → Authors → Scheduling navigation/save behavior, historical Finding branch rendering including legacy missing values, transition confirmation, stale response, empty/loading/error states, keyboard access, and no out-of-scope persistence. Existing Feature 010/013 regression suites remain required. Manual visual review compares the Authors screen and wizard shell to `06-author-policies.png` and `03-new-configuration-general.png`.

## Constitution Re-check

- Clean Architecture: pass; normalized branch port and pure domain resolver preserve dependency direction.
- Security: pass; configuration-derived credential access and scope checks are server-side; snapshots and policy records are credential-free.
- Immutable execution history: pass; V1 remains readable, new policy context is captured in V2, and historical data is not rewritten.
- One controlled pipeline and lifecycle: pass; existing process use case handles both triggers and policy failures remain repository-isolated.
- Migration-managed persistence: pass; only Alembic revision 0009 is planned, with no destructive legacy data change.
- Contract compatibility: pass; additive author-policy routes/projections, ETag concurrency, no changes to existing meanings.
- Accessible/reusable UX: pass; existing wizard/MUI patterns and explicit loading/error/empty/keyboard states are retained.

No constitution exception is requested.

## Project Structure

```text
backend/app/domain/
  author_policy.py                         # policy identity, normalization, resolution
  entities/execution_snapshot.py           # V1-compatible parser and V2 policy snapshot
  services/unauthorized_commit_author_rule.py
backend/app/application/
  ports/author_policy_repository.py
  ports/gitlab_repository_client.py        # normalized branch list operation
  use_cases/get_author_policies.py
  use_cases/upsert_author_policy.py
  use_cases/delete_author_policy.py
  use_cases/migrate_author_policy_mode.py
  use_cases/list_repository_branches.py
  use_cases/process_repository.py           # existing shared processor integration
backend/app/infrastructure/
  gitlab/http_gitlab_repository_client.py
  database/models.py
  database/sqlalchemy_repositories.py
backend/app/api/v1/
  author_policies.py
  schemas.py
  findings.py                               # additive branch projection
backend/alembic/versions/0009_author_policies.py
backend/tests/{unit,api,integration}/       # existing suite conventions
src/features/monitoring-configurations/
  api/authorPoliciesApi.ts
  types/authorPolicies.ts
  components/AuthorPoliciesStep.tsx
  components/RepositoryBranchPolicyCard.tsx
  components/GroupAuthorPolicyCard.tsx
  components/AllowedAuthorChips.tsx
src/test/features/monitoring-configurations/ # Vitest feature tests
specs/014-repository-branch-author-policies/{research.md,data-model.md,quickstart.md,contracts/}
```

Use established file names and composition where possible; avoid creating a component if the current wizard structure can own the responsibility cleanly.

## Complexity Tracking

No constitution violations or new runtime dependencies are planned.
