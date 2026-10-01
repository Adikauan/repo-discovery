# Author Policies API Contract

Base prefix: `/api/v1/monitoring-configurations/{configuration_id}`. JSON names follow existing API conventions: existing configuration schemas remain snake_case; new policy contracts use snake_case unless the implementation's established alias model requires camelCase consistently. All endpoints require the existing application authentication/session context.

## Read policies

`GET /author-policies`

Returns selected-scope policies plus retained inactive policies. It never returns credentials.

```json
{
  "mode": "legacy",
  "legacy_fallback": {"active": true, "allowed_author_emails": ["alice@example.com"]},
  "policies": [
    {
      "id": "uuid",
      "scope_type": "repository_branch",
      "active": true,
      "gitlab_instance_fingerprint": "sha256-hex",
      "gitlab_project_id": 42,
      "scope_name": "api-gateway",
      "scope_path": "backend/api-gateway",
      "branch": "main",
      "allowed_author_emails": ["alice@example.com"]
    },
    {
      "id": "uuid",
      "scope_type": "group",
      "active": false,
      "gitlab_instance_fingerprint": "sha256-hex",
      "gitlab_group_id": 8,
      "scope_name": "platform",
      "scope_path": "engineering/platform",
      "branch": null,
      "allowed_author_emails": []
    }
  ]
}
```

`active` is a derived presentation projection against the persisted scope and current instance identity; it is not new authoritative policy state. An empty policy appears as an existing policy row with an empty email array. Absence of a row means no policy. The API does not expose execution-internal snapshots.

## Upsert a Group policy

`PUT /author-policies/groups/{gitlab_group_id}`

Headers: `If-Match: "{configuration_revision}"`.

```json
{"allowed_author_emails": [" Alice@Example.com ", "alice@example.com"]}
```

The server confirms the exact group ID and current instance fingerprint belong to the configuration's selected scope before writing. The response contains the canonical deduplicated emails, resulting policy ID, active flag, and new configuration version. The branch attribute is always null/absent for this type.

## Upsert a repository branch policy

`PUT /author-policies/repositories/{gitlab_project_id}/branches`

Headers: `If-Match: "{configuration_revision}"`.

```json
{"branch": "release/2026-q4", "allowed_author_emails": ["alice@example.com"]}
```

The branch is in the body so slash-containing branch names are not treated as route segments. The server confirms that the project is an explicitly selected repository under the current GitLab instance and verifies the branch exists using the configured connection before saving. A group descendant not individually selected cannot be used to create a repository-branch policy; its selected group policy covers dynamic group scope.

## Delete a policy

`DELETE /author-policies/{policy_id}`

Headers: `If-Match: "{configuration_revision}"`. The policy must belong to the route configuration. Explicit deletion removes its author children atomically. Scope removal alone does not delete it.

## Explicit one-way migration

`POST /author-policies/migration`

Headers: `If-Match: "{configuration_revision}"`. Empty request body. Changes mode from `legacy` to `scope_aware`, increments the configuration revision, and leaves the old `allowed_author_emails` value stored but inactive for future snapshots. Repeated migration returns the current scope-aware representation without applying another transition. There is no automatic migration on policy upsert.

## Branch discovery

`GET /repositories/{gitlab_project_id}/branches`

Returns all pages of normalized branches for a directly selected repository:

```json
{"items": [{"name": "main", "commit_sha": "40-or-64-hex", "default": true}]}
```

The caller cannot supply GitLab URL, token, or credential. The use case checks active configuration, selected repository ownership, GitLab instance fingerprint, usable configured credential, and credential validation for the same instance before provider access. Empty `items` is a valid response. Errors use existing Problem Details envelopes with safe codes such as `scope_repository_not_selected`, `gitlab_credential_missing`, `gitlab_instance_mismatch`, `repository_not_found`, `repository_forbidden`, `repository_timeout`, and `repository_invalid_response`.

## Common validation and concurrency

- Emails are trimmed, validated using the current Feature 010 configuration validation contract, case-folded with the existing domain normalizer, deduplicated, and sorted before persistence. Empty entries are rejected/removed according to existing list normalization; an empty array is valid and represents an explicit empty policy.
- Policy mutation requests require current `If-Match`; stale writes use the existing stale configuration conflict Problem Details behavior. A rejected write changes neither policy nor configuration revision.
- Unknown or out-of-scope entity identifiers are rejected without issuing a branch/provider lookup.
- No route mutates GitLab scope, MiningExecution, RepositoryExecution, Findings, or checkpoints.

## Finding branch projection

Existing Finding read APIs may add nullable `branch`, derived through Finding → RepositoryExecution → `processed_branch`. The Execution Findings UI displays this historical response field next to repository/commit context and uses a safe unavailable label for legacy records with no branch. It must not query current GitLab state to render historical findings. Existing fields and meanings remain intact. No Finding write route or Finding schema migration is required for branch context.
