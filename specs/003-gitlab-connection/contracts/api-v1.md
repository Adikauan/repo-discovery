# GitLab Connection API Contract (v1)

Base path: `/api/v1/monitoring-configurations/{configuration_id}/gitlab-connection`. Routes below are relative to that base. All examples are illustrative. `configuration_id` is the existing UUID. Contracts expose no persistence-specific fields, ciphertext, encryption keys or token values on reads. Credential revision and normalized-URL fingerprint are internal-only concurrency metadata and must never appear in public API DTOs, frontend response contracts, logs, or user-visible payloads.

## Shared status representation

```json
{
  "configuration_id": "<uuid>",
  "credential_configured": true,
  "state": "configured_not_validated",
  "latest_result": null,
  "last_validation_at": null,
  "last_successful_validation_at": null
}
```

`state`: `not_configured | configured_not_validated | validated | failed`. `validating` is a frontend-only transient state. `latest_result` is a safe enum, never provider response text.

## Retrieve status

`GET /`

- `200`: status object above. An absent credential returns `credential_configured: false`, `state: not_configured`.
- `404`: configuration unavailable/retired, using the existing API error envelope.
- Must never return any token, ciphertext, URL fingerprint or encryption metadata.

## Save or replace credential

`PUT /credential`

Request:

```json
{ "token": "<new-token>" }
```

This is the authoritative dedicated credential-write operation. `token` is required and must be non-empty, not whitespace-only, and no greater than 2048 UTF-8 bytes. Treat an accepted token as opaque: do not trim, semantically parse, or impose a GitLab-specific token format. A token exactly 2048 UTF-8 bytes is valid; byte length, not Unicode character count, controls the limit.

Missing, empty, whitespace-only, and greater-than-2048-byte tokens return HTTP 422 through the standard validation error envelope. Validation occurs at the API/request boundary before encryption or persistence. The response must not echo the token or any substring of it, and rejection must leave an existing credential unchanged. A blank PUT never means “preserve.” Blank preservation exists only when unrelated Monitoring Configuration fields are edited without a credential operation, or when the frontend leaves the replacement field blank and therefore does not call this endpoint. Only `DELETE /credential` removes a credential.

- `200`: status object with configured=true, state=`configured_not_validated`, prior validation metadata cleared.
- `404`: configuration missing/retired.
- `409`: the in-flight replacement lost an internal optimistic-concurrency race; the newer credential remains active and the safe error contains no credential or revision metadata.
- `422`: missing, empty, whitespace-only, greater-than-2048-UTF-8-byte token, or malformed request; safe field error omits the input value.
- `503`: encryption configuration/storage unavailable; generic safe error, no internals.

The service encrypts the new token before mutating persistence, captures the current internal credential revision when the operation starts, and atomically replaces ciphertext through compare-and-swap against that expected revision. If encryption or persistence fails before commit, the prior credential and revision remain unchanged. A successful replacement increments the internal revision and resets saved validation status and prior last-success time; it does not alter configuration fields or enabled state. Revision is never exposed in this request or any public response.

If a competing replacement commits after an operation captured its expected revision but before that operation commits, the stale in-flight operation returns `409 credential_replacement_conflict`; it does not overwrite the winner or disclose raw, decrypted, or encrypted credential material. A completely new PUT arriving after a successful replacement is a new intentional replacement, not a stale retry, because the public contract exposes no revision/precondition and adds no implicit deduplication. If the server commits but the client receives an uncertain network response, that commit remains authoritative; a later PUT is again a new replacement.

## Remove credential

`DELETE /credential`

- `204`: credential and its validation metadata removed; repeated removal is idempotent. A subsequent status read returns `credential_configured: false`, `state: not_configured`, with validation timestamps absent.
- `404`: configuration missing/retired.
- Does not delete or update the Monitoring Configuration. No token appears in response.

## Validate connection

`POST /validate`

For persisted credential validation, use an empty JSON object or no body. For candidate-only validation:

```json
{ "token": "<candidate-token>" }
```

Candidate tokens follow the same opaque-token request boundary as credential writes: non-empty, not whitespace-only, and at most 2048 UTF-8 bytes, with an exact-limit token accepted and any invalid value rejected safely before the GitLab adapter is called. No validation error echoes token content.

If a nonempty candidate is supplied, it is used only for this attempt and is never persisted; candidate failure does not change a saved credential or its metadata. If token is omitted, use the saved encrypted credential. If neither exists, return `409 credential_not_configured`. Validation responses identify `credential_source` as `saved_credential` or `candidate_token`. A candidate-token response reports only that attempt's outcome and omits saved-credential status/timestamps; use `GET /` to read the unchanged saved status.

Response `200` for a completed provider check:

```json
{
  "configuration_id": "<uuid>",
  "credential_source": "saved_credential",
  "state": "validated",
  "result": "success",
  "message": "GitLab connection validated.",
  "checked_at": "2026-09-28T12:00:00Z",
  "last_successful_validation_at": "2026-09-28T12:00:00Z"
}
```

Normalized validation outcomes include `success`, `invalid_url`, `invalid_credentials` (HTTP 401), `forbidden` (HTTP 403), `unreachable` (DNS/connect/TLS failure), `timeout`, `invalid_response`, `rate_limited` (HTTP 429), and `provider_unavailable` (HTTP 5xx). Malformed URLs, unsupported schemes, and URLs that cannot produce a valid GitLab API base URL return a safe `422 invalid_url`, distinct from an unreachable valid URL. A categorized provider failure is a completed validation and can return `200` with state `failed`; API-level request/configuration errors use non-2xx statuses. Successful `/user` validation confirms only that the instance is reachable, the token is accepted, and this authenticated endpoint succeeds; it does not certify permissions for Feature 004 discovery.

- `404`: configuration missing/retired.
- `409`: no saved credential for an omitted-token request, or saved configuration/credential changed during check (stale outcome not applied).
- `422`: empty, whitespace-only, or greater-than-2048-UTF-8-byte candidate token, or invalid configured URL; safe detail only and no submitted token content.
- `200`: safe categorized outcome; never contains provider bodies, headers, tokens, ciphertext, stack traces or raw exception strings.

The saved-credential path records latest result/time and successful time conditionally against the read credential revision and URL fingerprint. A failed revalidation using a saved credential (including invalid/expired token, forbidden validation endpoint, timeout, unreachable instance, or unexpected response) never removes or overwrites the credential: configured remains true, the configuration's enabled status is unchanged, and `last_successful_validation_at` remains the prior successful time (or null if there was none). The user may retry, replace, or explicitly remove the credential. Replacement or URL change invalidates the success state for the current connection. Candidate path does not update persisted validation metadata and its response omits saved-credential status fields. Both paths do no discovery.

## Error envelope

Use the existing API error envelope and stable machine-readable code, e.g.:

```json
{
  "error": {
    "code": "gitlab_validation_failed",
    "message": "The GitLab connection could not be validated.",
    "details": [{ "field": "token", "code": "required", "message": "Provide a GitLab access token." }]
  }
}
```

Exact safe user messages may be localized/presented by the frontend. Never echo credential input, auth headers, encrypted values, upstream response body, internal URL if inappropriate, or stack traces.

## Idempotency and concurrency

Removal and status reads are idempotent. Validation does not modify the credential itself. Replacement uses internal optimistic compare-and-swap: two operations capturing N yield one N+1 commit and one safe 409; a delayed N operation cannot overwrite N+1; and a pre-commit persistence failure changes neither credential nor revision. A successful server commit is not rolled back by an uncertain client response. A later PUT begins a new operation against the current internal revision and is treated as intentional replacement, not stale retry or implicit duplicate. Revision and URL fingerprint remain internal and no raw, decrypted, or encrypted credential material appears in concurrency conflicts or diagnostics. A stale saved-validation result is rejected instead of overwriting newer URL/credential metadata. Do not add distributed locking or generic idempotency-key storage for secrets; do not persist request bodies or secret-bearing response snapshots.
