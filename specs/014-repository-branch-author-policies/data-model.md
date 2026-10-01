# Data Model: Repository & Branch Author Policies

## Existing records retained

### MonitoringConfiguration

Existing fields remain unchanged. Feature 014 adds:

| Field | Type | Constraints / meaning |
|---|---|---|
| `author_policy_mode` | enum/string: `legacy`, `scope_aware` | Non-null; defaults to `legacy` for existing configurations and API-compatible creation. One-way explicit transition to `scope_aware`; does not delete legacy values. Updated under existing configuration revision CAS. |

`allowed_author_emails` remains the Feature 010 legacy fallback. It is not copied into child policies and is not dropped by migration.

## New persistence entities

### AuthorPolicy

One row represents either a selected Group allowlist or one Repository + Branch allowlist.

| Field | Type | Constraints / meaning |
|---|---|---|
| `id` | UUID | Primary key, opaque outside API policy operations. |
| `monitoring_configuration_id` | UUID | Required FK to MonitoringConfiguration; restrictive deletion behavior follows existing historical retention policy. |
| `scope_type` | enum/string | Exactly `group` or `repository_branch`. |
| `gitlab_instance_fingerprint` | fixed-length string | Required; binds numeric provider identity to the configured GitLab instance. |
| `gitlab_group_id` | positive bigint, nullable | Required only for `group`; stable GitLab identity, never display name/path. |
| `gitlab_project_id` | positive bigint, nullable | Required only for `repository_branch`; stable GitLab identity, never display name/path. |
| `branch_name` | non-empty text, nullable | Required only for `repository_branch`; exact discovered GitLab branch name. |
| `scope_name` | text | Descriptive metadata for UI; not identity. |
| `scope_path` | text | Descriptive metadata for UI; not identity. |
| `created_at` | timestamptz | Creation timestamp. |
| `updated_at` | timestamptz | Last successful update timestamp. |

**Constraints**:

- A check constraint requires group rows to have a group ID and no project/branch values.
- A check constraint requires repository-branch rows to have project ID and non-empty branch and no group ID.
- Partial unique constraint for group policy: `(monitoring_configuration_id, gitlab_instance_fingerprint, gitlab_group_id)` where `scope_type = 'group'`.
- Partial unique constraint for repository branch policy: `(monitoring_configuration_id, gitlab_instance_fingerprint, gitlab_project_id, branch_name)` where `scope_type = 'repository_branch'`.
- The application verifies policy identity belongs to current selected scope on every write; on reads it derives `active` from current scope and returns retained out-of-scope records as inactive.
- Group policy has no branch field and no static descendant-project list.

### AuthorPolicyAuthor

One row is a normalized allowed email belonging to a policy.

| Field | Type | Constraints / meaning |
|---|---|---|
| `policy_id` | UUID | Required FK to AuthorPolicy with delete cascade when a policy itself is explicitly deleted. |
| `normalized_email` | string(254) | Trimmed and case-folded identity; non-empty; unique within `policy_id`. |
| `display_email` | string(254) | Canonical normalized representation returned to the UI; no secret. |

The policy row exists even when it has zero child author rows. This distinguishes an explicit empty policy (all valid commit email identities unauthorized) from no matching policy.

## Execution snapshot V2

Historical `ExecutionSnapshotV1` documents remain readable without rewriting. New executions use an immutable V2 shape containing the existing V1 scope/trigger data plus:

| Field | Type | Constraints / meaning |
|---|---|---|
| `author_policy_mode` | `legacy` or `scope_aware` | Captures whether legacy fallback was active for this execution. |
| `legacy_allowed_author_emails` | tuple of normalized email strings | Captured only when mode is `legacy`; empty tuple preserves Feature 010 legacy empty-list behavior. No credential data. |
| `group_author_policies` | tuple of snapshot records | Selected group ID, instance fingerprint, descriptive path/name, normalized allowed email tuple. Dynamic group identity remains; no frozen descendant repositories. |
| `repository_branch_author_policies` | tuple of snapshot records | Selected project ID, instance fingerprint, descriptive path/name, exact branch, normalized allowed email tuple. |
| `repository_group_coverage` | tuple of coverage records | Resolved project ID, selected applicable group ID, and hierarchy distance to project, captured to resolve the closest ancestor without live GitLab calls. |

Snapshot records and nested tuples are frozen/immutable. Only policies whose stable scope item is selected at execution creation are active in the snapshot. Retained policies whose item is outside selected scope are excluded from the effective policy set. Historical V1 snapshots continue to carry and use their original global `allowed_author_emails` field.

## Derived values (not persisted)

- **Policy active state**: Derived from the saved Monitoring Configuration scope and GitLab instance fingerprint. Removing an item from scope does not mutate/delete its AuthorPolicy.
- **Applicable policy**: Resolved from immutable snapshot, current repository identity, actual processed branch, and captured repository-to-selected-Group coverage. Exact repository/branch match wins; otherwise the closest selected ancestor Group (smallest snapshotted distance) wins. Group lists are not combined. Equal closest distance without deterministic ancestry fails safely with `author_policy_ambiguous`. Legacy fallback applies only when no scoped match exists and captured mode is legacy.
- **Finding branch**: Derived from the owning RepositoryExecution's immutable `processed_branch`. Do not add a duplicate branch field to Finding unless future evidence shows derivation is impossible.
- **Branch discovery item**: Normalized GitLab branch name, HEAD commit SHA, and default marker; transient read result, not persisted.

## Migration

Alembic revision `0009_author_policies` adds `author_policy_mode` with `legacy` default, `author_policies`, and `author_policy_authors`, checks, partial unique indexes, and required indexes. It does not rewrite execution snapshots, Findings, checkpoints, monitoring scope, or the existing JSONB `allowed_author_emails` field. The legacy list remains preserved after switching mode, but is omitted from future effective policy decisions in scope-aware mode.
