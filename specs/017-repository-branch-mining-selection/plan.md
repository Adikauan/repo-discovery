# Implementation Plan: Repository Branch Mining Selection

**Feature**: `017-repository-branch-mining-selection`  
**Updated**: 2026-10-01  
**Spec**: [spec.md](spec.md)

## Summary

Replace the intermediate Scope TargetBranchRule source with Feature 014 Repository + Branch author Policies. Scope continues to select Groups and repositories only. The Policy page resolves the current effective repositories, including dynamic Group descendants, and lets the user configure one or more branch Policies per repository. Each such Policy both defines a mining target and supplies that branch's allowed authors. Manual and scheduled execution share one completeness/target resolver. No default branch is inferred.

Feature 014 Group author Policies are branchless and therefore cannot define targets. Per the clarified decision they are excluded from all new snapshots/resolution and shown, if retained in current configuration, only as inactive legacy records. Historical snapshots preserve their previous behavior unchanged.

## Technical Context

**Stack**: Python/FastAPI/SQLAlchemy/Alembic, PostgreSQL, React/TypeScript/Material UI, pytest, Vitest.  
**Provider**: existing GitLab abstraction and configured credential.  
**Execution**: existing shared manual/scheduled `CreateMiningExecution` and `ProcessMiningExecution` pipeline.  
**Constraints**: Policy is the only branch source; Scope has no branches; all current effective repositories need a Repository + Branch Policy before execution; no fallback; historical snapshots stay immutable.

## Architecture Decisions

### Effective Policy repository projection

Reuse `EffectiveScopeResolver` to resolve direct repositories and current descendants of selected Groups. Extract/share a read-oriented application service so Policy UI and execution validation use identical stable-ID de-duplication and provider failure behavior. Extend the Policy read contract to return effective repositories with scope origin, current branch Policies, and derived completeness state. Repository Policy mutations and branch discovery accept only a repository in this effective set; this allows policies for Group-derived descendants without persisting a static expansion in Scope.

### One mining-target resolver

Introduce a domain/application resolver over:

1. Effective repositories from Scope resolution.
2. Active Repository + Branch Policies for the same Monitoring Configuration and GitLab instance.
3. A complete-coverage check requiring at least one Policy for every effective repository.

Output is a deterministic de-duplicated set of `MiningTarget(repository_id, path, branch, normalized_allowed_authors)`. Multiple Policies per repository produce multiple targets. No Group Policy or Scope target data participates. Unavailable Policy branches fail only their Repository + Branch target; missing Policy blocks execution before MiningExecution creation.

### Manual and scheduled validation

Inject the same GitLab/provider/credential resolver and effective-Policy resolver into the shared `CreateMiningExecution` boundary. Resolve current Group membership, validate complete Policy coverage, and snapshot exact targets before persisting/starting a MiningExecution. Manual requests return standard 422 validation details on incomplete Policy. Scheduled dispatch uses the same rule and maps incomplete Policy to its existing safe ineligible/failure outcome without launching a partial execution. Provider failures remain safe and do not expose credentials.

### Snapshot and history

Introduce snapshot V4 with a frozen list of resolved repository/branch targets and each exact branch's author allowlist. Scope membership used for the run is fixed into the V4 target set; later Group membership or Policy changes do not rewrite history. V1–V3 snapshot deserialization stays available for history. V3 snapshots that contain obsolete Scope target rules MUST NOT be resumed as new work. New RepositoryExecution rows continue to store target/processed branch; checkpoint identity remains `(configuration, repository, branch)`.

### Group author-policy compatibility

Feature 014 Group Policies have no branch and were an author fallback. They are not included in V4 snapshots and are not used for target coverage, target derivation, or authorization in new executions. Existing snapshot payloads retain them for historical interpretation. If current DB rows are retained, expose them only as inactive legacy records (not editable, not effective, and not copied to new snapshots). Do not synthesize repository Policies from them. Feature 014 resolver remains available for old snapshot interpretation; new V4 processing uses the allowlist carried by the exact target.

### Persistence migration and sanitation

- Add Alembic revision `0011_policy_mining_targets` after `0010_repository_target_branches`.
- Drop the obsolete Scope target-rule table and its indexes/constraints. Do not convert its rows to Repository + Branch Policies.
- Preserve existing `author_policies`, branch Policies, Group Policy rows (inactive legacy), configurations, credentials, scope, schedules, execution history, and Findings. Historical snapshots are not edited.
- Revision 0010 already deletes legacy checkpoints because their default-branch provenance cannot prove an exact Policy branch. It adds nullable `target_branch` to `repository_executions`; old rows retain their descriptive history but have no fabricated target branch. New rows use branch-aware execution identity, and new checkpoints use `(configuration, repository, branch)`.
- Revision 0011 drops the obsolete `target_branch_rules` table and its index. It does not convert those rows to Policies. Together, revisions 0010/0011 preserve unrelated history while invalidating only ambiguous checkpoint state and obsolete Scope-branch configuration.
- Reject resumed pending V3 work safely; do not resolve from its stale Scope target rules.
- Document the targeted migration sanitation above; do not run broad database cleanup or rewrite historical snapshots, executions, or Findings.

### UI

- Remove `TargetBranchesEditor` from GitLab Scope; Scope remains Groups/repositories, search/tree, selection, unavailable state, sticky Selected Scope.
- Rename user-facing Authors step/page/headings/breadcrumbs/stepper/bottom navigation to **Policy**.
- Policy view consumes effective repository projection. Direct and Group-derived repositories appear once by stable repository ID. Group-derived rows may show source Group as derived metadata.
- Each row displays Configured/Policy required and branch Policies. Reuse GitLab branch discovery and author chips. Add/update/remove Repository + Branch Policies; support multiple branches and protect duplicate identities.
- New Group Policies cannot be authored. Existing Group Policy rows, if shown, are clearly marked inactive legacy and read-only; no Group author policy is copied into new execution data.
- Explain that Policy branch is the mining branch and the allowed-author rule for that branch.

## Data / Contract Touchpoints

- `backend/app/domain/author_policy.py` and existing `AuthorPolicy` remain the persisted `(configuration, instance, repository, branch, authors)` source. Group policy shape is legacy only.
- Add a `MiningTarget` value object and effective policy completeness/target resolver.
- Reuse `ResolveEffectiveScope`; expose current effective repositories to Policy UI through the author-policy read contract or a focused read-only endpoint.
- Remove the active `TargetBranchRule` entity/port/model/API and V3 capture from new paths. Retain only the legacy V3 snapshot DTO/reader required to display historical execution data and safely reject pending V3 work.
- Snapshot V4 captures effective MiningTargets; no credentials.
- Existing repository branch discovery is broadened from directly-selected repositories to any current effective repository, with server validation.
- Execution error for incomplete Policy is standard 422 at start; branch unavailable remains safe RepositoryExecution failure.

## Implementation Phases

1. **Artifact and contract foundation**: Policy-only source, effective repository projection, request/response shapes, legacy Group-policy semantics.
2. **Domain and persistence**: MiningTarget resolver, completeness rule, snapshot V4; Alembic 0011 removes obsolete Scope target-rule storage without converting data.
3. **Effective repository Policy API**: Resolve direct/Group repositories, branch discovery ownership, Repository + Branch CRUD, read-only inactive legacy Group policies.
4. **Execution eligibility and targets**: shared manual/scheduled preflight; snapshot exact resolved targets; no partial start; process V4 targets only.
5. **Frontend Policy integration**: remove Scope branch controls; rename Authors to Policy; render effective repositories/status; branch/author CRUD and errors.
6. **History and safety regression**: branch checkpoint/baseline, Finding, snapshot, migration, default-branch, Group legacy compatibility.
7. **Validation and convergence**: PostgreSQL migration/integration tests, full unit/API/frontend tests, production build, artifact/code audit, converge remediation.

## Validation Strategy

- Unit: effective repository de-duplication, complete coverage, one/multiple Repository + Branch policies, duplicate rejection, no Group/default branch target.
- API: effective scope reads, CRUD for direct and Group-derived repositories, scope ownership, GitLab branch discovery, 422 completeness, stale revisions, inactive Group policy behavior.
- Execution: one missing repository blocks manual/scheduled before a MiningExecution; new Group descendant transitions Policy required → executable after a Policy; same target resolver for both triggers.
- Worker: target branch passed unchanged to all GitLab calls, author evaluation, checkpoint, Finding; default branch is never queried as fallback.
- PostgreSQL: migration removes old Scope target table only; preserves config/security/scope/author-policy/schedule/history rows; no SQLite substitution.
- Frontend: Scope has no branch selector; Policy label and direct/Group descendant projection; `dev-larah` regression; completeness states; branch/author flows/accessibility.
- Build: frontend full tests/accessibility/build, backend unit/API/PostgreSQL integrations, migration validation.

## Constitution Check

- **I–IV**: Pass; resolution belongs in domain/application, GitLab access behind the current provider, persistence in infrastructure.
- **V**: Pass; credentials stay server-side and never enter target snapshots/logs.
- **VI**: Pass; V4 freezes resolved targets; V1–V3 history remains immutable; obsolete V3 work is not resumed.
- **VII**: Pass; manual/scheduled execution share preflight, snapshot and worker pipeline.
- **VIII–X**: Pass with explicit rejection outcomes, PostgreSQL migrations, and tests for resolver/security/history/parity.
- **XI**: Pass; Policy provides visible completeness, loading/error/retry and accessible author/branch controls; Scope retains existing UX.
- **XII**: Pass; existing provider, policy persistence, routes, and UI framework are reused.

## Assumptions

- Current Group Policy DB rows are retained as inactive compatibility data unless a later approved cleanup removes them; they have no effect in new executions and are not exposed as editable policies.
- Existing V3 execution snapshots remain historical records; any in-flight V3 execution is failed safely rather than resumed with the obsolete Scope target rules.
- Existing schedules remain unchanged; a scheduled occurrence with incomplete effective Policy coverage does not start mining.
