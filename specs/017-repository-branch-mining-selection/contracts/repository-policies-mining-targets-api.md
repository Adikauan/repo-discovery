# Repository Policies and Mining Target Contracts

The Monitoring Configuration's selected Scope (direct repositories plus dynamic Groups) is resolved server-side. Scope has no branch fields. All operations derive GitLab URL and credentials from the configuration; clients never submit provider credentials.

## Effective repositories and policies

`GET /api/v1/monitoring-configurations/{configuration_id}/author-policies`

Returns the current effective repository projection and active Repository + Branch policies, for example:

```json
{
  "configurationId": "...",
  "revision": 12,
  "repositories": [
    {"gitlabProjectId": 42, "fullPath": "backend/api-a", "scopeSource": "group", "status": "configured",
     "policies": [{"branch": "dev-larah", "allowedAuthors": ["user@example.com"]}]},
    {"gitlabProjectId": 43, "fullPath": "backend/api-c", "scopeSource": "group", "status": "policy_required", "policies": []}
  ]
}
```

Repositories are deduplicated by stable GitLab project ID. Current descendants of selected Groups appear dynamically. Legacy branchless Group Policies are not returned as active/editable Policies and are excluded from new execution snapshots.

## Mutate repository policies

`PUT /api/v1/monitoring-configurations/{configuration_id}/author-policies`

Atomically replaces the submitted Repository + Branch policy collection using the existing revision/CAS convention. Every repository ID must belong to the current effective Scope, every branch must be valid and discovered through the scoped provider flow, duplicate `(repository ID, branch)` identities are rejected, and allowed authors use existing normalization. This request does not accept Group policies, Scope branch data, GitLab URL, or credentials.

Deleting a policy uses the existing policy mutation convention. A configuration with any effective repository left without a branch Policy becomes ineligible for new execution.

## Discover branches

Reuse the existing branch discovery endpoint scoped by configuration ID and repository ID. The server verifies current effective Scope membership, including repositories covered by selected Groups, then uses the configuration's protected GitLab connection.

## Execution eligibility and target resolution

Manual and scheduled execution creation invoke one server-side resolver:

1. Resolve direct repositories and current descendants of selected Groups.
2. Deduplicate by stable repository ID.
3. Match active Repository + Branch Policies.
4. Reject the entire execution with standard Problem Details / HTTP 422 if any effective repository has no Policy.
5. Snapshot the concrete Repository + Branch targets and each target's normalized allowed authors.

No partial execution, default-branch fallback, or Scope target-branch endpoint is supported. A newly discovered Group repository is returned as `policy_required` until configured; it blocks manual and scheduled execution.

## Errors and concurrency

- `404`: configuration or repository outside effective Scope not found
- `409`: stale revision according to existing Problem Details convention
- `422`: incomplete Policy coverage, duplicate identity, invalid branch, or invalid mutation
- safe provider Problem Details for unavailable effective repositories or GitLab failures

Errors never contain credentials or provider secrets. Group author-policy writes are rejected/unsupported for future execution; retained legacy rows do not affect new runs.

## Snapshot

New snapshot V4 stores the effective repositories and concrete Repository + Branch targets used by the run, including normalized allowed authors. V1–V3 remain readable as history. V3 Scope target rules cannot resume new mining and must fail safely if pending. No credentials or legacy branchless Group author Policies enter V4.
