# GitLab Scope API Contract (v1)

Base route: `/api/v1/monitoring-configurations/{configuration_id}/gitlab-scope`. All routes use existing RFC 9457 `ProblemDetails` errors and the current active-configuration rule. Discovery and adding new selections require a configured GitLab URL and credential. Saved scope can be read and removed while a credential is absent; replacement requests that only retain recognized selection IDs or clear the scope do not require a credential. No route accepts or returns a credential.

The API returns only normalized hierarchy or persisted rule fields. It never returns provider payloads, encrypted/decrypted credentials, raw connection internals, or the internal GitLab instance fingerprint. An `ETag` represents only the persisted scope version.

## Hierarchy node

```json
{
  "id": 17,
  "type": "group",
  "name": "Platform",
  "full_path": "engineering/platform",
  "parent_group_id": 4,
  "expandable": true
}
```

`type` is `group` or `repository`. `parent_group_id` is omitted for root groups or unknown ownership; repositories are not expandable. Every group is expandable, including an empty group, so expanding it can return an explicit empty state. Provider attributes outside this normalized schema are discarded.

## List root groups

`GET /api/v1/monitoring-configurations/{configuration_id}/gitlab-scope/root`

- `200 OK`: `{ "nodes": [<group node>, ...] }`, containing the complete paginated set of visible top-level groups.
- `404 Not Found`: unknown or retired configuration.
- `409 Conflict`: no saved GitLab credential (`gitlab_credential_required`).
- `422 Unprocessable Content`: configured GitLab URL is invalid.
- `502 Bad Gateway`: normalized discovery/authentication/response failure, with stable safe category.
- `503 Service Unavailable`: GitLab rate limit or provider unavailable.
- `504 Gateway Timeout`: GitLab request timed out.

The server lists top-level groups only; it does not fetch subgroups or projects for this request.

## List direct children of a group

`GET /api/v1/monitoring-configurations/{configuration_id}/gitlab-scope/groups/{group_id}/children`

- `200 OK`: `{ "nodes": [<direct subgroup and directly-owned project nodes>, ...] }`, fully paginated and stably ordered.
- An empty list means the group has no visible direct subgroups or directly-owned projects.
- `404 Not Found`: configuration unavailable, or the requested group cannot be accessed in the current hierarchy. The error is safe and does not distinguish existence/access where doing so could enumerate resources.
- `409`, `422`, `502`, `503`, `504`: same meanings as root discovery.

Subgroups are `type: "group"` and can be expanded through the same endpoint. The result excludes projects shared into the group and excludes descendant projects; descendant groups/projects are discovered by expansion. A page failure returns a safe error, not a partial success list.

## Read persisted scope

`GET /api/v1/monitoring-configurations/{configuration_id}/gitlab-scope`

Response:

```json
{
  "groups": [
    {
      "selection_id": "97fd847e-81ab-4e6d-bb20-c4ed2c0b2e5c",
      "gitlab_id": 17,
      "name": "Platform",
      "full_path": "engineering/platform",
      "parent_group_id": 4,
      "availability": "available"
    }
  ],
  "repositories": [],
  "stale": false
}
```

`availability` is `available | unavailable | unresolved | stale`. The response-level `stale` is true if one or more entries belong to another instance; per-entry availability remains authoritative when stale and current entries coexist. For stale entries, no lookup is sent to the current GitLab instance. A missing scope-state row returns empty arrays with `ETag: "0"`. A saved scope is returned even when no credential is configured; current-origin entries are `unresolved` because reconciliation cannot run. `ETag` is the current opaque decimal version in quotes and follows Feature 002's scope-independent `If-Match` convention.

## Replace persisted scope

`PUT /api/v1/monitoring-configurations/{configuration_id}/gitlab-scope`

Required: `If-Match: "<ETag from the latest GET>"`.

```json
{
  "groups": [
    { "selection_id": "97fd847e-81ab-4e6d-bb20-c4ed2c0b2e5c", "gitlab_id": 17 },
    { "gitlab_id": 22 }
  ],
  "repositories": [
    { "selection_id": "31662eb2-4a6a-42e0-a11f-c420420aa456", "gitlab_id": 918 }
  ]
}
```

Each array is the full desired explicit selection set. A new selection omits `selection_id` and is verified against the current GitLab instance/credential; its safe metadata is obtained from GitLab and it is bound to that instance. An existing selection includes its `selection_id`; the server verifies it belongs to this configuration and entity type, and that its `gitlab_id` is unchanged. Round-tripping a stale selection preserves its original instance association without querying the new instance. Omitting an old selection is the user's explicit removal action. A request containing only recognized existing selection IDs, including an empty set, can be saved without a credential so users can retain or remove prior selections. Duplicate provider IDs for one origin/type are rejected with a safe 422 field error.

- `200 OK`: saved scope representation plus advanced `ETag`.
- `404 Not Found`: unknown or retired configuration.
- `409 Conflict`: no credential for new IDs, or connection changed during provider validation.
- `412 Precondition Failed`: stale `If-Match`; no partial write. Draft remains available to reload/reapply.
- `422 Unprocessable Content`: malformed IDs, duplicate/inconsistent rule IDs, or invalid payload; no partial write.
- `428 Precondition Required`: missing `If-Match`.
- `502`, `503`, `504`: normalized safe provider failures during validation of new IDs; previous persisted rules remain intact.

An empty body `{ "groups": [], "repositories": [] }` is valid and persists an empty scope. Saving never enables/disables the configuration or triggers mining.

## Error envelope

Use the current RFC 9457 `ProblemDetails` response. `detail` and `errors[].message` are safe user-facing text; provider body/headers, exception text, token, ciphertext, URL fingerprint and credential revision are omitted. Examples of stable codes include `gitlab_credential_required`, `gitlab_connection_changed`, `gitlab_invalid_url`, `gitlab_authentication_failed`, `gitlab_forbidden`, `gitlab_group_unavailable`, `gitlab_repository_unavailable`, `gitlab_rate_limited`, `gitlab_timeout`, `gitlab_unreachable`, `gitlab_provider_unavailable`, `gitlab_invalid_response`, and `scope_version_conflict`.

## Compatibility and security

All routes are additive under `/api/v1`; adding optional response metadata is compatible. Discovery results use explicit response DTOs and never return ORM objects or raw provider JSON. GitLab IDs are meaningful together with server-stored origin identity; clients only receive stale/availability states and opaque `selection_id` values, not instance fingerprints.
