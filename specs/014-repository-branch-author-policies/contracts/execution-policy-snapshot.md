# Execution Policy Snapshot Contract

## Compatibility

- Historical snapshot payloads with `schema_version: 1` remain readable and retain their `allowed_author_emails` semantics.
- New MiningExecutions capture an immutable V2 snapshot. Existing snapshots are never migrated or rewritten.
- Internal author policy context is persistence/application input and is not added to the public execution snapshot response by default.

## V2 author policy fields

```json
{
  "schema_version": 2,
  "author_policy_mode": "legacy",
  "legacy_allowed_author_emails": ["alice@example.com"],
  "group_author_policies": [
    {"gitlab_group_id": 8, "instance_fingerprint": "...", "full_path": "engineering/platform", "allowed_author_emails": ["alice@example.com"]}
  ],
  "repository_group_coverage": [
    {"gitlab_project_id": 42, "selected_group_id": 8, "distance_to_repository": 1}
  ],
  "repository_branch_author_policies": [
    {"gitlab_project_id": 42, "instance_fingerprint": "...", "full_path": "backend/api-gateway", "branch": "main", "allowed_author_emails": []}
  ]
}
```

The example omits unrelated existing snapshot fields. Arrays are deterministically ordered by scope type, stable provider identity, branch, then email. Emails are normalized and sorted. The legacy array is captured only if legacy fallback is active; a missing/empty policy row is never synthesized from an empty array. A policy row with an empty author array is preserved as an explicit policy.

## Resolver input/output

Resolver inputs are immutable snapshot context (including repository-to-selected-Group coverage and hierarchy distance), actual stable project ID, and actual processed branch. It returns one of:

- `matched` plus normalized allowed email identities and source scope;
- `disabled` when no policy matches in scope-aware mode;
- `matched_legacy` plus legacy allowlist when no scoped policy matches in legacy mode.

Resolution order is deterministic: (1) exact repository + actual processed branch; (2) among applicable selected Group policies, the closest selected ancestor Group, determined by the snapshotted `distance_to_repository` (smallest distance wins); (3) legacy fallback when mode is `legacy`; otherwise `disabled`. Group lists are never unioned or intersected. The snapshot's repository-to-selected-Group coverage and distance values are captured from the resolved dynamic scope so the resolver requires no live GitLab hierarchy lookup. If multiple applicable Group policies have equal minimum distance and no deterministic ancestor relationship is present in the snapshot, return a safe `author_policy_ambiguous` resolution error; do not choose arbitrarily. A matched policy with zero authors is still `matched` and makes all valid commit emails unauthorized. The resolver performs no GitLab or database calls. This resolver receives only the branch already selected by existing mining semantics; it cannot choose or expand the mining branch.

No credential, access token, authorization header, raw provider DTO, or decrypted value is valid in this contract.
