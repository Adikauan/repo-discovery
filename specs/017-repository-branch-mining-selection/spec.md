# Feature Specification: Repository Branch Mining Selection

**Feature Branch**: `017-repository-branch-mining-selection`  
**Status**: Updated Draft  
**Input**: Authoritative product decision: Scope selects Groups and repositories; repository branch Policies define both mining targets and allowed authors. This supersedes the interim Scope target-branch model.

## Purpose

Use the branch already selected in each repository Policy as the mining branch. Remove the duplicate Scope branch configuration so there is one source of truth for a Repository + Branch target and its allowed authors.

## User Stories

### US1 — Resolve repositories from Scope for Policy configuration (P1)

As a configuration owner, I need Policy to show every effective repository selected directly or included through selected Groups, so I can configure mining and authorization without selecting repositories twice.

**Acceptance scenarios**

1. A directly selected repository appears in Policy without another repository picker.
2. Current repositories under a selected Group appear in Policy and are identifiable as Group-derived.
3. If a new repository later appears under that selected Group, it appears as **Policy required**; no branch is inferred for it.
4. Scope contains only Group/repository selection and does not contain a mining-branch selector.

### US2 — Configure mining and author Policy by repository and branch (P1)

As a configuration owner, I need each effective repository to have one or more branch Policies, each with its own allowed-author list, so each Policy branch is also the branch mined.

**Acceptance scenarios**

1. A repository Policy for `dev-larah` yields the mining target `(repository, dev-larah)` without any branch configuration in Scope.
2. A repository can have multiple Policies, such as `main` and `dev-larah`, with independent author lists and branch histories.
3. Duplicate Repository + Branch Policies are rejected or prevented by the existing uniqueness contract.
4. Branches are chosen through scoped GitLab branch discovery; credentials remain server-side.
5. Policy clearly shows **Configured** or **Policy required** for each effective repository.

### US3 — Enforce complete Policy coverage for direct and dynamic Scope (P1)

As an operator, I need executions blocked unless every currently effective repository has at least one valid Repository + Branch Policy, so incomplete Group membership cannot cause silent omissions or inferred mining.

**Acceptance scenarios**

1. Manual and scheduled execution are allowed only when every effective repository has at least one valid branch Policy.
2. If any repository lacks a Policy, execution is rejected with the standard validation response before mining starts; configured repositories are not mined as a partial subset.
3. If a new repository appears under a selected Group, manual and scheduled execution are blocked until a Policy is saved for it.
4. Once that Policy is saved, execution is eligible and mines the configured branch.
5. No missing Policy, unavailable branch, or provider failure falls back to `default_branch`, `main`, `master`, or another inferred branch.

### US4 — Preserve branch-specific execution history and trigger parity (P1)

As an operator, I need branch targets, checkpoints, Findings, and execution snapshots to use the same Policy branch and behave identically for manual and scheduled runs.

**Acceptance scenarios**

1. Manual and scheduled triggers use the same effective-scope and Policy resolver.
2. Each Repository + Branch has independent baseline/checkpoint state.
3. A first run with no exact branch checkpoint establishes a baseline at that branch HEAD and does not create Findings before baseline.
4. RepositoryExecution, Finding context, and immutable execution snapshot identify the actual processed branch.
5. Later changes to Scope or Policy do not reinterpret historical snapshots or Findings.

## Functional Requirements

- **FR-001**: Scope MUST define only directly selected repositories and dynamically selected Groups. Scope MUST NOT configure mining branches.
- **FR-002**: Policy MUST be the only source of mining branch targets. Each active mining target MUST be derived from an applicable Repository + Branch Policy that also carries that branch's allowed authors.
- **FR-003**: Policy MUST show all currently effective repositories: directly selected repositories and currently accessible repositories dynamically resolved under selected Groups. Users MUST NOT reselect those repositories in Policy.
- **FR-004**: A repository MAY have multiple Policies for different branches. A Policy is uniquely identified by Monitoring Configuration, GitLab instance, stable repository ID, and exact branch name. Duplicate identities MUST be prevented.
- **FR-005**: Branches MUST be selected using GitLab branch discovery scoped to the Monitoring Configuration and an effective repository. Credentials MUST remain server-side.
- **FR-006**: For each effective repository, at least one valid Repository + Branch Policy MUST exist before a Monitoring Configuration can start a manual or scheduled execution.
- **FR-007**: If any effective repository lacks a Policy, execution MUST be rejected before mining begins using the standard validation/Problem Details conventions. The system MUST NOT silently skip the repository or mine only a configured subset.
- **FR-008**: New repositories dynamically discovered under a selected Group MUST appear as requiring Policy. They MUST NOT receive an inferred branch or become executable until a Repository + Branch Policy is configured.
- **FR-009**: Branches in a Policy MUST be both the mining target and the branch used for allowed-author evaluation. No other branch source may override or supplement them.
- **FR-010**: GitLab `default_branch` MUST never be an implicit target or fallback. If a Policy branch is unavailable, that Repository + Branch processing fails safely without substituting another branch.
- **FR-011**: Manual and scheduled execution MUST call the same effective-scope resolution, Policy-completeness validation, target derivation, and mining pipeline.
- **FR-012**: Checkpoint identity MUST include Monitoring Configuration, stable repository identity, and exact branch. Baseline and checkpoint progress MUST be independent per Repository + Branch.
- **FR-013**: A new branch target without a valid exact-branch checkpoint MUST establish its own baseline at HEAD and MUST NOT scan pre-baseline commits by default.
- **FR-014**: New snapshots MUST immutably capture the effective repository/branch targets and the corresponding author policies used for that execution. They MUST NOT contain credentials.
- **FR-015**: RepositoryExecution and new Unauthorized Commit Author Findings MUST expose the actual processed branch from historical execution context. Branch MUST NOT be looked up live to render old results.
- **FR-016**: Feature 014 Group-level author Policies are discontinued for new executions. They MUST NOT produce mining targets or authorize new execution commits. Existing execution snapshots remain unchanged and continue to describe their historical Group-policy decisions. Existing live Group-policy rows MUST NOT be converted to repository Policies by guessing branches.
- **FR-017**: Existing Scope target-branch records are obsolete. They MUST NOT be used to resolve new execution targets and MUST be removed through a migration or targeted sanitation. They MUST NOT be migrated into Policies automatically.
- **FR-018**: Checkpoints present before explicit Policy-sourced branch identity MUST NOT be reused unless exact Repository + Branch provenance is proven. Revision 0010 deletes the legacy checkpoint rows because their provenance cannot be proven; a new Policy branch establishes its own baseline.
- **FR-019**: Scope removal, Group membership changes, and Policy edits MUST affect future executions only; historical snapshots, RepositoryExecutions, and Findings MUST not be rewritten or reassigned. The one-time migration invalidation/deletion of unprovable legacy checkpoints required by FR-018 is permitted; new checkpoints are keyed to the exact Repository + Branch.
- **FR-020**: API and UI MUST distinguish **Policy required** from **Configured**, derived from effective Scope plus saved Repository + Branch Policies; no separate persisted readiness state is required.
- **FR-021**: All data mutations and branch discovery MUST validate Monitoring Configuration ownership and current effective-scope membership server-side.
- **FR-022**: Safe loading, empty, unavailable, provider-failure, retry, and validation states MUST be provided for effective repository discovery and Policy management.
- **FR-023**: All execution validation and provider failures MUST preserve existing repository failure isolation and safe Problem Details/error conventions.

## Non-Goals

- Group-level branch rules or implicit branch inheritance.
- Default branch inference or fallback.
- Scope-level mining-branch configuration.
- New Finding types, mining rules, persistence for analytics, or unrelated discovery/semantic/AI functionality.
- Reinterpreting historical executions or changing checkpoint behavior beyond branch identity.

## Key Entities

- **ScopeSelection**: selected stable Group and repository identities; Groups remain dynamic.
- **RepositoryBranchPolicy**: `(Monitoring Configuration, GitLab instance, repository ID, branch)` plus normalized allowed authors.
- **MiningTarget**: effective repository plus the branch from its RepositoryBranchPolicy.
- **BranchAwareCheckpoint**: configuration, repository, branch, successful commit hash.
- **ExecutionSnapshot**: immutable resolved MiningTargets and author lists for the execution.
- **RepositoryExecution / Finding**: historical result associated with the actual processed branch.

## Assumptions and Clarifications

- Scope Group membership is resolved dynamically through the existing GitLab integration. Newly discovered repositories do not inherit branches or policies.
- A Group with no current descendant repositories contributes no mining target. When descendants appear, each requires its own Repository + Branch Policy.
- Feature 014 Group author Policies are branchless legacy behavior. By the explicit decision for this update, they are inactive for future execution and retained only in existing historical snapshots. They are never migrated into branch Policies.
- Existing live Group policy records may be retained as inactive compatibility data until a separately approved cleanup; new Policy UI and snapshots exclude them.
- Existing snapshots are immutable. V1–V3 readers remain for history, but obsolete V3 Scope target rules cannot drive new or resumed mining.
- Existing global author fallback data is not a mining-target source. A new execution still requires Repository + Branch Policies for complete effective Scope.

## Success Criteria

- **SC-001**: A Repository + Branch Policy alone yields that repository/branch mining target; no Scope branch entry is needed.
- **SC-002**: Scope has no mining-branch field or control, and Policy is the sole mining-branch source.
- **SC-003**: Every current effective repository, including Group descendants, appears in Policy and exposes configured/incomplete state.
- **SC-004**: A new Group descendant without Policy blocks both manual and scheduled execution before MiningExecution starts.
- **SC-005**: Once each effective repository has at least one branch Policy, manual and scheduled execution resolve the same target set.
- **SC-006**: No tested missing, unavailable, deleted, or failing Policy branch causes a request to GitLab `default_branch` as fallback.
- **SC-007**: Multiple Policies for one repository create independent RepositoryExecutions, baselines, checkpoints, Findings context, and snapshot targets.
- **SC-008**: Existing Group Policies are absent from new execution authorization decisions while snapshots containing them remain unchanged and readable.
- **SC-009**: PostgreSQL migration removes obsolete Scope target-branch storage without fabricating Policies or damaging unrelated configuration/security data.

## Existing Behavior to Preserve

- Existing dynamic Group Scope, manual/scheduled shared pipeline, Feature 014 normalized author comparison for exact repository-branch policies, baseline/checkpoint rules, Finding identity, safe errors, and credential security.
- Historical snapshots and Findings remain readable and immutable.
