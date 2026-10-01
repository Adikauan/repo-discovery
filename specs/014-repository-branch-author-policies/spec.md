# Feature Specification: Repository & Branch Author Policies

**Feature Branch**: `014-repository-branch-author-policies`  
**Created**: 2026-09-30  
**Status**: Draft  
**Input**: User description: Replace the global allowed-commit-author configuration with scope-aware policies for selected GitLab groups, repositories, and repository branches, and use those policies in the existing Unauthorized Commit Author mining rule.

## Clarifications

### Session 2026-09-30

- Q: When a group policy and a repository/branch policy both apply to a commit, which policy determines the allowed authors? → A: The repository/branch policy takes precedence over the group policy.
- Q: For which branches does a group policy apply to dynamically included repositories? → A: Only branches that the existing mining pipeline already processes; a group policy does not expand branch scope.
- Q: What happens when no author policy matches, and what does an explicitly empty policy mean? → A: No matching policy disables Unauthorized Commit Author detection for that repository/branch; an explicitly configured empty allowlist treats every valid commit author email as unauthorized.
- Q: How should existing Feature 010 global allowed-author lists be handled for future executions? → A: Preserve each list as a temporary configuration-level fallback until that Monitoring Configuration explicitly migrates to scope-aware policies; capture whichever policy source applies in each execution snapshot.
- Q: What happens to a policy when its group or repository is removed from selected scope? → A: Retain it as inactive/unavailable and do not apply it while the scope item is absent.
- Q: What happens if a configured branch is deleted or inaccessible? → A: Mark the policy branch unavailable in configuration. If the branch selected by existing mining semantics is unavailable when the repository is processed, fail that RepositoryExecution with a normalized safe error; do not substitute another branch or advance its checkpoint. An unavailable policy for a branch that this execution does not process is ignored and does not fail the execution.
- Q: If multiple selected Group policies apply to a repository, which one is used? → A: A matching Repository + Branch policy wins first. Otherwise, use only the most specific selected Group policy: the closest selected ancestor Group to the repository. Do not union or intersect author lists. If equal specificity cannot be deterministically ordered, fail policy resolution safely for that RepositoryExecution and log the invalid state without secrets.

### Clarified implementation boundaries

- Branch discovery and branch-policy configuration do not expand mining scope. An execution continues to process only the branch selected by existing repository-mining semantics (currently the repository default branch); only a policy matching the branch actually processed is evaluated. Other branch policies remain valid saved configuration and have no effect until existing mining semantics process that branch. The Authors step must explain this and must not offer branch-mining controls.
- The Authors wizard step replaces the global multiline author textarea as the primary editor. Legacy allowed-author data remains preserved and is presented as clearly labeled, read-only fallback data while the configuration remains in legacy mode. The explicit one-way migration action switches future policy resolution to scope-aware mode without deleting or submitting legacy values through policy APIs.
- The wizard must preserve the Scope → Authors → Scheduling flow, load scope/policy/legacy state, retain state on back navigation, validate/save before advancing as required by existing wizard conventions, and handle save errors without silently losing edits.
- Finding branch context is user-facing: render the historical branch in the Execution Findings table from the Finding's associated RepositoryExecution context. Never query current GitLab branch data to explain an old Finding; legacy findings without stored branch context use a safe unavailable value.

## User Scenarios & Testing

### User Story 1 - Configure repository branch author policies (Priority: P1)

As a Monitoring Configuration owner, I can select actual branches of repositories already included in the configuration scope and set a separate allowed-author list for each branch.

**Why this priority**: Branch-specific policy is the core new capability and must work without accepting arbitrary repository identifiers or branch names.

**Independent Test**: Select one repository in scope, retrieve its branches through the configured GitLab connection, save different normalized author lists for two branches, reopen the Authors step, and verify both policies are associated with the stable repository identity and correct branch.

**Acceptance Scenarios**:

1. **Given** a repository is selected in the Monitoring Configuration scope, **When** its author policies are configured, **Then** branch choices come from GitLab branch discovery and each branch can have an independent allowed-author list.
2. **Given** two branch policies exist for one repository, **When** one policy is changed, **Then** the other branch policy remains unchanged.
3. **Given** a repository is not part of the configuration's selected scope, **When** a client submits a policy or requests branch discovery for it, **Then** the server rejects the request without querying GitLab for that repository.

### User Story 2 - Configure dynamic group author policies (Priority: P1)

As a Monitoring Configuration owner, I can set an allowed-author policy on a selected GitLab group so it remains associated with that group while its descendant repositories are included dynamically by the existing scope behavior.

**Why this priority**: Group scope is dynamic in the existing product, and its policy must remain attached to the stable group identity rather than a one-time expansion of repositories.

**Independent Test**: Configure a policy on a selected group, add or remove a descendant repository in GitLab without changing the selected group, then verify policy association remains with the group and the group policy does not itself change which repositories or branches are mined.

**Acceptance Scenarios**:

1. **Given** a group is selected in scope, **When** its author policy is configured, **Then** the policy is stored against the stable GitLab group identity and the UI states that branches do not apply to groups.
2. **Given** repositories are dynamically included through a selected group, **When** execution resolves author policy, **Then** the group policy remains associated with the group and does not materialize that group as a static repository selection.
3. **Given** a group or repository policy is changed, **When** the configuration is saved, **Then** the existing Feature 004 scope semantics remain unchanged.

### User Story 3 - Apply policy to manual and scheduled mining (Priority: P1)

As a user reviewing mining results, I want the existing Unauthorized Commit Author rule to evaluate each commit using the applicable policy for its repository and processed branch, consistently for manual and scheduled executions.

**Why this priority**: Configuration has value only when the existing mining pipeline uses it predictably and records findings under the established rule.

**Independent Test**: Run equivalent manual and scheduled executions with the same captured policies and commit range; verify both use the same policy resolution, preserve branch context, and create only the existing Unauthorized Commit Author Finding for unauthorized authors.

**Acceptance Scenarios**:

1. **Given** an execution processes a repository branch with an applicable policy, **When** a commit is evaluated, **Then** the author email is normalized and compared with that policy's allowed authors.
2. **Given** an author is not authorized by the resolved policy, **When** the rule evaluates the commit, **Then** it creates the existing Unauthorized Commit Author Finding associated with the RepositoryExecution and sufficient branch context.
3. **Given** an execution has captured its author policies, **When** configuration policies or scope are later edited, **Then** that execution's snapshot and historical findings retain their original meaning.

### User Story 4 - Safely evolve existing author configuration (Priority: P2)

As an administrator with existing Monitoring Configurations and execution history, I can move to scope-aware policies without losing historical execution or finding records or exposing credentials.

**Why this priority**: The feature replaces an existing configuration model, so migration and backward compatibility must preserve auditability and avoid silently changing policy meaning.

**Independent Test**: Apply the approved migration to a database containing legacy global author lists, existing executions, findings, and checkpoints; verify all historical records remain readable and legacy configuration is handled according to the migration decision.

**Acceptance Scenarios**:

1. **Given** historical executions and findings exist, **When** policy storage is migrated, **Then** those records remain readable and are not reinterpreted.
2. **Given** a policy or branch lookup is requested, **When** credentials are resolved, **Then** credentials remain server-side and are absent from snapshots, policy records, API responses, and logs.
3. **Given** scope changes after policies are saved, **When** the configuration is reopened or executed, **Then** policies never apply to unrelated scope items and historical snapshots remain unchanged.

### Edge Cases

- The same repository may be selected directly and through one or more selected groups; effective repository processing continues to deduplicate according to existing scope behavior.
- A group can contain nested groups and dynamically included repositories; policy association remains keyed by group identity.
- A configured branch may later be deleted or become inaccessible. Show the saved policy as unavailable. Only if the branch selected for processing by existing mining semantics is unavailable does its RepositoryExecution fail with a normalized safe error; do not substitute another branch or advance that repository's checkpoint. An unavailable policy for an unprocessed branch does not affect that execution.
- A policy whose group or repository is removed from selected scope remains persisted as inactive/unavailable and is not applied; it may become applicable again only if the same stable identity returns to the selected scope.
- When both group and repository/branch policies apply to a commit, the repository/branch policy takes precedence.
- When no author policy matches a processed repository/branch, Unauthorized Commit Author detection is disabled for that repository/branch. An explicitly configured policy with zero authors is an empty allowlist, so every valid commit author email is unauthorized.
- For a Monitoring Configuration still using its preserved legacy global allowlist, that list is the fallback when no scope-specific policy matches. Once the configuration explicitly migrates to scope-aware policies, an unmatched repository/branch has no applicable policy and detection is disabled there.
- Allowed emails may contain surrounding whitespace, mixed case, or normalized duplicates; comparison trims whitespace, ignores case, and deduplicates normalized identities.
- Empty email entries must not be persisted. Validation must preserve current accepted-email behavior and must not reject unusual legitimate Git author values without an established requirement.
- Policy edits do not reset repository checkpoints or cause previously processed commits to be rescanned or reclassified.
- A GitLab instance URL change must not reinterpret historical group or repository identifiers against another instance.
- Branch discovery may return no branches, fail, or return an inaccessible repository; the UI must preserve saved policy context and offer safe feedback/retry where applicable.

## Requirements

### Functional Requirements

- **FR-001**: The Authors configuration workflow MUST operate only on groups and repositories selected in the Monitoring Configuration's existing GitLab scope; users MUST NOT enter arbitrary repository IDs or paths.
- **FR-002**: The system MUST support author policies for selected GitLab groups, identified authoritatively by stable GitLab group ID.
- **FR-003**: The system MUST support independent author policies for each selected repository and branch, identified by Monitoring Configuration, stable GitLab repository ID, and branch name.
- **FR-004**: Repository branch choices MUST be discovered from the configured GitLab instance using the Monitoring Configuration's secure credential; arbitrary free-text branch creation MUST NOT be the normal workflow.
- **FR-005**: Branch discovery MUST be restricted server-side to repositories validated as belonging to the Monitoring Configuration's selected scope.
- **FR-006**: Group policies MUST remain attached to selected group identity and MUST NOT convert dynamic group scope into a static repository list. Group policy configuration MUST communicate that branch selection does not apply to groups. A group policy applies only to branches the existing mining pipeline already processes and MUST NOT expand branch scope.
- **FR-007**: When both a group policy and a repository/branch policy match, the repository/branch policy MUST take precedence.
- **FR-008**: When no scope-specific policy matches a processed repository/branch, the system MUST use the preserved legacy global allowlist if the Monitoring Configuration has not explicitly migrated to scope-aware policies; otherwise, detection MUST be disabled for that repository/branch. An explicitly configured policy with no allowed authors MUST remain distinct and MUST treat every valid commit author email as unauthorized.
- **FR-009**: Allowed-author entries MUST be normalized by trimming surrounding whitespace, comparing case-insensitively, and deduplicating normalized email identities. Empty entries MUST NOT be persisted, and author names MUST NOT determine authorization.
- **FR-010**: The Authors UI MUST support structured author entry associated with its policy, including adding and removing individual author entries, and MUST NOT use a single multiline global textarea as the new policy model.
- **FR-011**: The application MUST validate policy mutations against current scope ownership and MUST NOT trust client-supplied group or repository identifiers without server-side validation.
- **FR-012**: When a group or repository is removed from selected scope, its policy MUST be retained as inactive/unavailable and MUST NOT be applied. It may become applicable again only if the same stable identity returns to scope; it MUST never be reassigned to another entity.
- **FR-013**: The existing Unauthorized Commit Author mining rule MUST resolve authorization policy using the actual repository and processed branch for each evaluated commit, according to the clarified policy semantics.
- **FR-014**: Manual and scheduled executions MUST use the same existing mining pipeline and the same author-policy resolution behavior; this feature MUST NOT create a second pipeline or a new Finding category.
- **FR-015**: Unauthorized commits MUST continue to use the existing Unauthorized Commit Author Finding concept and preserve RepositoryExecution association, commit identity, author context, and branch context sufficient to explain the decision.
- **FR-016**: Each execution MUST capture an immutable, normalized snapshot of the effective author-policy configuration needed to interpret that execution, using stable group/repository identifiers and branch names as applicable. Snapshots MUST NOT contain credentials.
- **FR-017**: Changes to live author policies, selected scope, or schedule MUST NOT reinterpret historical execution snapshots or Findings.
- **FR-018**: Author-policy changes MUST NOT reset Feature 010 checkpoints or automatically rescan/reclassify previously processed commits.
- **FR-019**: Persistence changes MUST be migration-managed and preserve existing configurations, execution history, Findings, and checkpoints. Existing Feature 010 global allowed-author lists MUST remain available as a temporary configuration-level fallback until an explicit per-configuration migration to scope-aware policies; legacy data MUST NOT be dropped or reinterpreted before that transition.
- **FR-020**: Read/write API contracts MUST support retrieving and managing group and repository-branch policies, and branch discovery where needed, using established API conventions and safe Problem Details errors. Credential values MUST NOT be accepted from or returned to the frontend for discovery.
- **FR-021**: Policy writes MUST follow established stale-write/concurrency conventions for Monitoring Configuration changes where applicable and MUST NOT silently overwrite concurrent policy edits.
- **FR-022**: The Authors UI MUST present selected groups and repositories with scope type, identity/path, policy state, and controls appropriate to each type. Repositories MUST support multiple branch policies; groups MUST show that branches are not applicable.
- **FR-023**: The UI and APIs MUST provide safe loading, empty, unavailable-branch, GitLab failure, policy-save failure, and stale/conflict states without exposing provider internals or credentials.
- **FR-024**: Policy configuration and branch discovery MUST be keyboard accessible, labelled, responsive, and expose validation/errors accessibly.
- **FR-025**: This feature MUST NOT add mining rule categories, word/keyword/table discovery, semantic or code-pattern analysis, AI/LLM/SLM analysis, code-review or Finding-triage workflows, or unrelated product capability.
- **FR-026**: A deleted or inaccessible configured branch MUST be represented as unavailable. If the branch selected for processing by existing mining semantics is unavailable, the RepositoryExecution MUST fail with a normalized safe error; the system MUST NOT substitute another branch or advance that repository's checkpoint. An unavailable policy for a branch not processed by that execution MUST be ignored and MUST NOT fail it.
- **FR-027**: Branch discovery and author-policy configuration MUST NOT change repository mining branch selection or introduce multi-branch mining. Only a policy matching the branch actually processed under existing mining semantics is evaluated. The Authors UI MUST explain that branch policies do not change which branches are mined.
- **FR-028**: Policy resolution MUST first select an exact Repository + Branch policy; otherwise it MUST select the most specific applicable selected Group policy, defined as the closest selected ancestor Group to the repository. Group author lists MUST NOT be unioned or intersected. If multiple applicable Group policies have equal specificity and no deterministic ancestor ordering can be established, the RepositoryExecution MUST fail safely with a normalized policy-ambiguity error.
- **FR-029**: The Execution Findings UI MUST display branch context from the historical Finding/RepositoryExecution response when available and MUST show a safe unavailable value for legacy records without branch context. It MUST NOT query live GitLab state to render historical branch context.
- **FR-030**: The Authors wizard MUST replace the global multiline author textarea as the primary editor, load selected scope and policy state, preserve the Scope → Authors → Scheduling navigation flow, preserve appropriate state on back navigation, and validate/save before advancing according to existing wizard conventions. Legacy global author values MUST remain clearly identified and preserved as read-only fallback data until explicit migration; policy APIs MUST NOT accidentally resubmit or delete those values.

### Key Entities

- **Group Author Policy**: An allowlist associated with one Monitoring Configuration and one stable GitLab group identity; group membership remains dynamic under existing scope rules.
- **Repository Branch Author Policy**: An allowlist associated with one Monitoring Configuration, one stable GitLab repository identity, and one discovered branch.
- **Allowed Commit Author**: A normalized email identity authorized by an applicable policy.
- **Author Policy Snapshot**: Immutable execution-time policy context required to interpret commit authorization historically, without credentials.
- **Branch Discovery Result**: Safe branch metadata retrieved for a repository validated against the configuration's selected scope.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can configure distinct allowed-author lists for at least two branches of one selected repository and recover those exact policies after reopening the configuration.
- **SC-002**: Repository branch selection is sourced from GitLab and server-side tests demonstrate that branch discovery and policy writes reject repositories outside the selected scope.
- **SC-003**: Group policies remain keyed to group identity and tests demonstrate that adding/removing descendant repositories does not materialize or rewrite the selected group scope.
- **SC-004**: Tests demonstrate deterministic policy resolution for repository, branch, and group overlap after clarification, including missing and explicitly empty policy cases.
- **SC-005**: Manual and scheduled execution tests show identical author-policy semantics and continue to produce only the existing Unauthorized Commit Author Finding type.
- **SC-006**: Execution snapshots preserve the normalized policy used at execution time, contain no credentials, and remain unchanged after later policy or scope edits.
- **SC-007**: Policy changes leave existing checkpoints unchanged and do not automatically reclassify historical commits or Findings.
- **SC-008**: Migration tests preserve existing Monitoring Configurations, execution history, Findings, and checkpoints and apply the clarified legacy-list strategy.
- **SC-009**: All policy management, branch discovery, and execution paths avoid exposing credentials or raw provider errors in responses, snapshots, or logs.
- **SC-010**: The Authors step supports keyboard-accessible structured author entry, multiple branch policies per repository, and group policies without branch selection.
- **SC-011**: Resolver tests prove closest-ancestor Group precedence, Repository + Branch override, no author-list union/intersection, and safe failure for equal-specificity ambiguity.
- **SC-012**: The Authors UI explains that branch policies do not change mined branches, and tests prove policy configuration does not submit branch-mining scope.
- **SC-013**: Execution Findings UI renders historical branch context from the API, handles legacy missing branch values safely, and never requests current GitLab branch state for historical findings.
- **SC-014**: Wizard interaction tests prove Scope → Authors → Scheduling navigation, back-state retention, safe validation/save behavior before advancing, and preservation of legacy author values during one-way migration.

## Assumptions

- Features 001-013 and the project constitution remain the functional source of truth for existing scope, execution, credential, checkpoint, Finding, and UI behavior.
- Feature 004's selected groups continue to represent dynamic scope over their eligible descendants; author policy does not alter scope membership.
- Feature 010's email normalization and the existing Unauthorized Commit Author Finding remain authoritative except where a clarification explicitly resolves policy applicability.
- GitLab branch access uses the existing secure connection and provider abstraction; provider-specific payloads remain outside domain/application contracts.
- The current global allowed-author configuration may exist in persisted data and remains available as the clarified temporary fallback until that Monitoring Configuration explicitly migrates to scope-aware policies.
- Policy precedence, branch coverage, missing/empty policy behavior, legacy fallback, scope-removal behavior, and unavailable-branch behavior are defined in the clarification decisions above and MUST be used without reinterpretation.

## Out of Scope

- New mining rule categories or Finding types.
- Word discovery, keyword discovery, table discovery, semantic analysis, code-pattern discovery, or AI/LLM/SLM analysis.
- Changing commit-range traversal, checkpoint/baseline behavior, or resetting checkpoints because policy changed.
- Reinterpreting or rewriting historical executions or Findings.
- Storing GitLab credentials in policy records or execution snapshots.
- Expanding mining scope through author policies.
- Code review, Finding triage, or unrelated product functionality.
