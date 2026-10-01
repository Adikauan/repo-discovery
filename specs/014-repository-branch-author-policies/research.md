# Research: Repository & Branch Author Policies

## Existing architecture inspected

- Feature 010 currently stores `allowed_author_emails` on `MonitoringConfiguration`, normalizes it in `domain/monitoring_configuration.py`, and captures it in `ExecutionSnapshotV1`.
- `ProcessRepository` resolves the current default branch, uses repository checkpoints, calls the existing `UnauthorizedCommitAuthorRule`, persists Findings, and advances the checkpoint only on successful completion.
- Feature 008's processing scope and bounded repository workers are shared by manual and scheduled execution. This feature must not create a second path.
- `RepositoryExecution.processed_branch` already persists the branch used for processing; Finding projections can derive historical branch context from the associated RepositoryExecution.
- GitLab access is behind `GitLabRepositoryClient` and `HttpGitLabRepositoryClient`; the latter already normalizes HTTP failures and supports paginated REST traversal.
- API writes use Monitoring Configuration `If-Match` / revision checks. Use that same revision as the optimistic concurrency boundary for policy mutations.
- Frontend uses React, TypeScript, MUI, a five-step wizard, and the existing visual preview component `FutureAuthorPolicyPreview`.

## Decisions

### Policy identity and relational shape

**Decision**: Use one constrained policy table with one normalized author child table. Group policies key by configuration, GitLab instance fingerprint, and stable group ID. Repository branch policies key by configuration, instance fingerprint, stable project ID, and exact branch string. Enforce uniqueness in PostgreSQL and validate scope membership in the application layer.

**Rationale**: A shared policy identity with a strict scope discriminator avoids duplicate persistence logic while relational author children support uniqueness and edits. Instance fingerprint prevents historical numeric IDs from crossing GitLab instances.

**Alternatives considered**: Separate group/repository policy tables would offer more explicit column nullability but duplicate author persistence behavior. JSON arrays would match current configuration storage but cannot enforce per-policy duplicate authors as directly and are less relational for new policy entities.

### Precedence and resolution

**Decision**: An exact repository/branch policy overrides group policy. The group policy applies only to existing mined branch scope. If no scoped policy matches, use the legacy global allowlist only while mode is `legacy`; after explicit migration, no match disables detection. An explicit empty policy is a match and authorizes no valid email identities.

**Rationale**: These rules are recorded by Feature 014 clarification. Policy evaluation is pure domain logic over the immutable execution snapshot and actual processed branch.

**Alternatives considered**: Unioning repository and group allowlists would prevent repository-specific restriction; treating missing policy as empty would produce unauthorized findings from absent configuration; falling back to legacy after migration would defeat explicit cutover.

**Clarified resolution**: An exact Repository + Branch policy wins first. If none matches, select the single most-specific applicable selected Group policy: the closest selected ancestor Group to the repository in the GitLab hierarchy. Do not union or intersect author lists. If equal specificity cannot be deterministically ordered, fail policy resolution for the affected RepositoryExecution with a normalized safe ambiguity error and log only safe identifiers/state. Snapshot the selected Group coverage and hierarchy distance needed to resolve this deterministically without live GitLab calls.

**Branch-scope boundary**: Branch discovery is for authorization targets only. It does not expand repository mining scope or enable multi-branch mining. The current repository mining branch selection remains authoritative; policies for other discovered branches are saved but have no effect until existing mining semantics process that branch. The Authors UI must state this explicitly. An unavailable saved branch is shown unavailable, but it does not fail an execution unless it is the branch actually selected for processing under existing mining semantics.

**Legacy editor boundary**: The Authors step replaces the global multiline editor. While a configuration remains in legacy mode, the legacy list is shown as clearly labeled read-only fallback data and is preserved. The explicit one-way mode transition makes scoped policies authoritative for future executions; legacy values are not sent through policy mutation requests or deleted.

### Legacy compatibility and explicit transition

**Decision**: Keep the legacy email list and introduce a persisted per-configuration mode (`legacy` / `scope_aware`). Existing and new configurations begin in legacy mode. Scope-specific policies can take effect when they match while legacy mode remains enabled; the list is used only where no scoped policy matches. The UI offers an explicit one-way switch to scope-aware mode; that switch keeps legacy data but turns off fallback for future executions.

**Rationale**: It preserves Feature 010 behavior without copying a global list into branch rows that may not exist and avoids loss of legacy data. Explicitness keeps a missing branch policy distinguishable from inherited old configuration.

**Alternatives considered**: Migrating into every branch requires live GitLab enumeration during migration and cannot safely cover dynamic group descendants. Immediate deletion/reinterpretation would break current configurations. An implicit switch on first policy edit could disable fallback before users understand the change.

### Execution snapshots and history

**Decision**: Add a versioned V2 snapshot that captures policy mode, the legacy allowlist if it is active, and normalized group/repository branch policies applicable to the execution's selected scope. Keep V1 deserialization unchanged; never rewrite historical snapshot JSON. Do not expose the new internal policy snapshot fields through public snapshot DTOs by default.

**Rationale**: Execution inputs must remain immutable and sufficient for historical interpretation. The existing RepositoryExecution branch field supplies branch context for findings.

**Alternatives considered**: Reading the live Monitoring Configuration during commit evaluation would reinterpret old runs. Persisting the entire live scope expansion would convert dynamic group scope to a static list. Duplicating branch on Finding is unnecessary while RepositoryExecution owns it.

### Branch discovery and branch lifecycle

**Decision**: Add a paginated normalized branch-list operation to the existing GitLab repository client. The API accepts only configuration and directly selected project identity, validates scope and GitLab instance before provider access, and resolves the existing secure credential server-side. A saved branch missing from GitLab is shown as unavailable; it does not fail an execution unless it is the branch selected by existing mining semantics. This validation does not add branch mining scope: commit traversal remains the current Feature 008/010 processed branch, and policies for other branches are ignored until that branch is processed.

**Rationale**: The clarification requires safe failure when the branch actually selected for processing is deleted/inaccessible and forbids silent substitution. An unrelated unprocessed branch policy must not affect the execution. All-pages discovery prevents false availability from a truncated branch list. Scope authorization must be checked before using client-supplied IDs.

**Alternatives considered**: Free-text branch names are not an authoritative GitLab reference. Replacing a missing branch with the default branch would misapply authorization. Persisting branch discovery results is unnecessary and would introduce stale provider state.

### Scope removal and reactivation

**Decision**: Retain policies when a scope item is removed. Mark them inactive in projections derived from the current saved scope, never apply them outside that scope, and reactivate only when the same stable identity is selected again.

**Rationale**: This is the clarified user-intent-preserving behavior and requires no tombstone state or scope-driven policy deletion.

**Alternatives considered**: Deleting with scope edits loses policy intent; reassigning by path/name risks using a policy on a different GitLab entity; blocking scope edits adds a new workflow constraint.

### Finding and checkpoint integration

**Decision**: Continue using the same Unauthorized Commit Author rule and Finding uniqueness. Derive branch from `RepositoryExecution.processed_branch` in read projections. Policy updates never reset the checkpoint; baseline and incremental commit ranges remain unchanged.

**Rationale**: The feature changes authorization policy, not history traversal or finding taxonomy.

**Alternatives considered**: New finding types or checkpoint namespaces would be unrelated semantics and could rescan/reclassify old history.

### Test and storage constraints

**Decision**: Continue PostgreSQL and Alembic; test database constraints, migration compatibility, and concurrent stale writes against PostgreSQL when `TEST_DATABASE_URL` is available. Use mocked GitLab branches for normal automated tests.

**Rationale**: PostgreSQL-specific partial uniqueness and migration behavior cannot be validated by replacing the project database with SQLite.

**Alternatives considered**: SQLite does not prove PostgreSQL index/transaction behavior; live GitLab tests would require credentials and be unreliable for standard CI.
