# Feature 004 Data Model: GitLab Scope Selection

## Domain and persisted concepts

### MiningScope

The explicit scope intent owned by one Monitoring Configuration. It is composed of selected group rules and selected repository rules, including rules originating from older GitLab instance identities.

| Field | Type | Rules |
|---|---|---|
| `configuration_id` | UUID | Existing Monitoring Configuration identity; one scope state per configuration. |
| `version` | positive integer | Scope-only concurrency version exposed through an opaque ETag. A missing scope state is the empty scope at version `0`. |
| `updated_at` | UTC timestamp | Time the explicit selection set last changed. |
| `groups` | selected group rules | May be empty; each rule has its own origin identity. |
| `repositories` | selected repository rules | May be empty; each rule has its own origin identity. |

Tree expansion, loaded children, search input, checkbox presentation, availability and transient loading/errors are not persisted scope state.

### SelectedGitLabGroup

One user-selected group rule, including a top-level group or subgroup. Selecting it covers projects that belong to that group and any descendants when a future execution resolves the scope. It does not cover a project merely shared with the group.

| Field | Type | Rules |
|---|---|---|
| `selection_id` | UUID | Opaque stable rule ID for API round-trip and explicit removal. |
| `configuration_id` | UUID | FK to the scope state. |
| `instance_fingerprint` | fixed 64-character SHA-256 hex | Internal normalized GitLab instance identity; never returned publicly. A digest is not encryption. |
| `gitlab_group_id` | positive integer | Stable GitLab group ID. Unique per configuration + origin fingerprint. |
| `name` | bounded text | Last-known display value, not identity. |
| `full_path` | bounded text | Last-known display value, not identity. |
| `parent_group_id` | positive integer, nullable | Last-known parent ID for tree/partial-selection presentation. |
| `updated_at` | UTC timestamp | Last safe metadata refresh or rule change. |

### SelectedGitLabRepository

One explicitly selected GitLab project/repository. It remains selected even if a selected group also covers it; effective resolution later deduplicates targets.

| Field | Type | Rules |
|---|---|---|
| `selection_id` | UUID | Opaque stable rule ID for API round-trip and explicit removal. |
| `configuration_id` | UUID | FK to the scope state. |
| `instance_fingerprint` | fixed 64-character SHA-256 hex | Internal normalized GitLab instance identity; never returned publicly. A digest is not encryption. |
| `gitlab_project_id` | positive integer | Stable GitLab project ID. Unique per configuration + origin fingerprint. |
| `name` | bounded text | Last-known display value, not identity. |
| `full_path` | bounded text | Last-known display value, not identity. |
| `parent_group_id` | positive integer, nullable | Last-known owning namespace group ID, where available. |
| `updated_at` | UTC timestamp | Last safe metadata refresh or rule change. |

### GitLabHierarchyNode

An ephemeral normalized discovery model, not a persistence record. It includes `id`, `type` (`group` or `repository`), `name`, `full_path`, optional `parent_group_id`, and `expandable`. Provider-only data, URLs, raw response bodies, access tokens, and transient UI state are excluded.

### ScopeAvailability

Derived on `GET scope` and not persisted: `available`, `unavailable`, `unresolved`, or `stale`. `unavailable` means targeted lookup returned not-found/forbidden; it does not claim deletion vs revoked access. `unresolved` means the provider could not be checked. `stale` means the stored instance fingerprint differs from the current normalized URL identity and prevents any lookup against the current instance.

## Relationships and constraints

```text
MonitoringConfiguration 1 ── 0..1 MiningScopeState
MiningScopeState       1 ── 0..* SelectedGitLabGroup
MiningScopeState       1 ── 0..* SelectedGitLabRepository
```

- `monitoring_configuration_scopes.configuration_id` is the primary key and FK to `monitoring_configurations.id`, `ON DELETE CASCADE` for physical deletion. The state is created lazily and uses a positive version.
- Group and repository rows have UUID primary keys, FK to scope state with `ON DELETE CASCADE`, and uniqueness constraints over `(configuration_id, instance_fingerprint, gitlab_group_id)` or `(configuration_id, instance_fingerprint, gitlab_project_id)` respectively.
- Provider entity IDs and metadata are instance-scoped. Names and paths can change and never serve as keys.
- Existing soft-retired configurations retain scope rows under Feature 002's lifecycle; scope is not coupled to Feature 003 credential deletion. Scope API operations still require an active configuration for discovery/editing.
- No hierarchy cache or descendant repository snapshot is written to PostgreSQL.

## Validation and transitions

1. Missing scope state reads as empty with ETag version 0. First save creates the state row and explicit rule rows atomically.
2. Every successful replacement advances the scope version once, even if the submitted explicit rule set is empty. A failed provider validation, database error, or stale ETag leaves the committed rule set/version unchanged.
3. A new rule must resolve by stable ID through the active configuration's GitLab URL and saved credential. Existing rule IDs can be round-tripped to retain unavailable or stale entries; their provider ID/type cannot change.
4. Existing IDs omitted from a successful full replacement are removed because the user removed them from the editable summary. Stale selections included by their `selection_id` retain their old origin fingerprint; new rules bind to the current fingerprint.
5. Scope revision is independent from Monitoring Configuration revision. A current GitLab URL change does not mutate scope records or scope version; availability is derived as stale.
6. Credential replacement/removal does not mutate any group or repository row. A later reconciliation may return unavailable/unresolved without deleting it.
7. For effective coverage, selected groups represent rules, not saved repository expansions. Candidate repositories are deduplicated by `(instance fingerprint, project ID)` after testing direct selected-project and ancestor-group coverage. Only current-instance rules participate in current effective scope.

## Migration

Add Alembic revision `0003_gitlab_scope`, down-revision `0002_gitlab_credentials`, creating the scope state, group selection, and repository selection tables. Upgrade preserves all existing configurations as valid empty scopes; downgrade drops only these Feature 004 tables. Add positive version and provider ID constraints, fixed fingerprint length and allowed entity/model constraints where supported, UTC-aware timestamps, FKs, and uniqueness constraints.
