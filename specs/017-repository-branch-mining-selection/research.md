# Research: Repository Branch Mining Selection

## Product Model Decision

The interim design stored independent Group/repository `TargetBranchRule` rows in Scope. The final approved model removes that second branch source:

- Scope selects direct repositories and dynamic Groups only.
- Policy contains a Repository + Branch and the Allowed Authors for that branch.
- That Policy branch is the mining target.
- Every currently effective repository requires at least one Repository + Branch Policy before execution.

This single source avoids duplicate branch editing, makes the policy identity the execution unit, and directly binds the branch mined to the author allowlist applied.

## Feature 014 Group Policy Compatibility

Feature 014 defines Group author Policies as branchless fallbacks for dynamically included repositories, with repository/branch Policy precedence. The resolver in `backend/app/domain/services/author_policy_resolver.py` confirms that behavior. These Group policies cannot produce concrete Repository + Branch targets. The authoritative Feature 017 decision therefore discontinues them for new executions while preserving snapshots that already captured them. Current stored Group Policy rows are retained as inactive compatibility data and are neither editable nor included in new snapshots. They are not expanded or migrated into repository Policies because no branch may be inferred.

## Effective Repository Projection

Reuse `EffectiveScopeResolver` for direct repositories and current descendants of selected Groups. The same resolved/deduplicated set must feed:

1. Policy UI read model.
2. Repository + Branch Policy ownership validation and branch discovery.
3. Manual/scheduled execution completeness validation.
4. Immutable execution target snapshots.

Stable GitLab repository ID is identity; full path and source Group are descriptive. Current Group membership is resolved at configuration read and execution start. A new descendant appears with Policy required and blocks the entire execution until configured.

## Mining Target Resolution

MiningTarget is derived only from effective Scope plus active Repository + Branch Policies. It includes repository ID/path, branch, and normalized allowed authors. Multiple branches produce multiple targets. No target can be derived from Scope alone, a Group author Policy, GitLab default_branch, or historical records.

Completeness is evaluated over all effective repositories before creating a MiningExecution. Empty Allowed Authors is still an explicit branch Policy and preserves Feature 014 empty-allowlist semantics. No Policy is distinct: it makes execution invalid.

## Execution Snapshot and Legacy History

Snapshot V4 captures the resolved repository/branch set and its branch-specific Allowed Authors. It excludes credentials, branchless Group policies, global legacy fallback, and obsolete Scope target rules. V1–V3 readers remain for history. V3 target rules cannot be used to resume mining under the final model. Existing snapshots and findings are never rewritten to current policies.

## Migration and Cleanup

Revision 0010 deletes all pre-existing repository checkpoints because the earlier default-branch-based progress cannot prove which explicit Policy branch it belongs to. It also adds nullable `target_branch` to RepositoryExecution; legacy rows remain readable but are not assigned a guessed branch. Revision 0011 drops the obsolete Scope target-rule table/index. Neither revision converts old Scope rules into Policies. Configuration, credentials, scope, schedules, policies, execution rows, snapshots, and Findings are preserved; no broad execution-history cleanup is run. New checkpoint identity is branch-aware. Historical V3 snapshots remain readable but pending V3 work fails safely.

The PostgreSQL migration integration test verifies this exact sanitation: checkpoint rows are removed, legacy RepositoryExecution target branch stays null, and unrelated configuration/security/scope/schedule/policy/execution/Finding records remain. Historical snapshots are not rewritten.

## Branch Discovery and Policy API

Reuse the existing GitLab branch client and configured credential. Expand ownership checks from directly selected repositories to repositories in current effective Group scope. The frontend never sends URL or token. Policy read data lists effective repositories, policies, `configured` / `policy_required` status, and source scope. Group Policy rows are not offered as writable policy items.

## Alternatives Rejected

- **Keep separate Scope target and Policy branch**: creates competing branch sources and was the failure mode in the `dev-larah` regression.
- **Infer branches for new Group descendants**: violates the explicit no-inference decision and can mine an unintended branch.
- **Use branchless Group author Policy to select target**: cannot identify a concrete branch, so it is not a target source.
- **Use `default_branch` when Policy is missing**: explicitly prohibited.
- **Materialize Group descendants in stored Scope**: changes dynamic Group semantics and freezes membership.
- **Convert old Scope target rows into Policies**: records do not contain branch-specific Allowed Authors and conversion would fabricate Policy state.
- **Delete or rewrite historical snapshots**: violates immutable execution history.
