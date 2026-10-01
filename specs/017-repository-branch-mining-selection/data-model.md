# Data Model: Repository Branch Mining Selection

## ScopeSelection

Scope rows identify directly selected repositories and selected Groups, keyed by Monitoring Configuration, GitLab instance fingerprint, and stable GitLab ID. Group membership remains dynamic. Scope has no branch field and does not persist an expanded list of Group descendants.

## RepositoryBranchPolicy

The existing Feature 014 repository-branch Policy is the only persisted source of mining branches.

| Field | Meaning |
|---|---|
| monitoring_configuration_id | Owning Monitoring Configuration |
| instance_fingerprint | GitLab instance identity |
| gitlab_project_id | Stable repository identity |
| branch | Exact Git ref selected from GitLab branch discovery |
| allowed_author_emails | Normalized allowlist for this branch; may be empty |
| full_path | Descriptive metadata only |

Unique identity: `(monitoring_configuration_id, instance_fingerprint, gitlab_project_id, branch)`. Duplicate Repository + Branch policies are rejected by persistence and API. Policy entries for repositories currently covered only through a selected Group are permitted after server-side effective-scope validation; they do not create static ScopeSelection rows.

## EffectiveRepository (derived)

Resolved at read/execution time by the shared effective-scope service:

- stable project ID and GitLab instance fingerprint
- current path/name
- whether it is directly selected or covered by selected Group(s)
- selected Group coverage metadata when needed for display/audit

Repositories are de-duplicated by stable project ID. New Group descendants appear dynamically. They have no Policy until a user creates one.

## MiningTarget (derived, then snapshotted)

One value per effective `(repository_id, branch)` RepositoryBranchPolicy, including the exact normalized allowed-author list. This is the sole input used by mining target fan-out and author comparison. Status is derived:

- **configured**: repository has at least one valid RepositoryBranchPolicy.
- **policy_required**: no such Policy exists.

## Legacy GroupAuthorPolicy

Feature 014 Group policies are branchless and are no longer effective for new executions. Existing database rows may remain as inactive compatibility data; they are not a MiningTarget, are not copied to new snapshots, and are not editable in the new Policy UI. Existing historical snapshots retain their prior captured Group policies unchanged.

## RepositoryExecution

- `target_branch`: branch from the snapshotted RepositoryBranchPolicy that this row attempted.
- `processed_branch`: actual branch processed; null until processing completes.
- Unique execution identity remains `(mining_execution_id, gitlab_project_id, target_branch)` to permit multiple branch Policies per repository.

## RepositoryCheckpoint

Identity remains `(monitoring_configuration_id, gitlab_project_id, branch)`. A checkpoint is read/written only for the exact snapshotted MiningTarget. A branch with no checkpoint establishes a baseline at its current HEAD without retrospective Findings.

## ExecutionSnapshotV4

Contains:

- Monitoring Configuration identity and safe context
- effective repositories resolved at execution start
- `mining_targets[]`: stable repository ID, descriptive path, exact Policy branch, normalized allowed authors
- trigger/schedule metadata already supported by the execution snapshot

Contains no GitLab credential, inactive Group Policy, global legacy author fallback, or Scope target-rule data. Later Scope, Group membership, and Policy changes do not affect V4.

V1–V3 remain readable for history. V3 snapshots may contain interim Scope target rules but those rules are obsolete and cannot be used to resume new work. Pending V3 work is failed safely.

## Finding

The existing Unauthorized Commit Author Finding remains associated with its RepositoryExecution. Its historical branch is derived from that immutable RepositoryExecution, never looked up from current Scope/Policy or GitLab.

## Migration

Alembic revisions `0010_repository_target_branches` and `0011_policy_mining_targets` perform a targeted transition. Revision 0010 deletes pre-existing `repository_checkpoints`, because their provenance cannot prove an exact Policy branch; it adds nullable `target_branch` to `repository_executions`, leaving legacy rows without an invented target while preserving their records and Findings. Revision 0011 drops the obsolete Scope `target_branch_rules` table/index and does not convert its rows into Policies because they lack branch-specific Allowed Authors. Configuration, credentials, Scope, schedules, author-policy rows, execution rows, snapshots, and Findings remain; legacy Group rows become ineffective for new runs. New checkpoints are branch-specific. Migration validation uses PostgreSQL.
