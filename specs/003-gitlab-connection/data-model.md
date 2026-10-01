# Data Model: GitLab Connection

## Existing aggregate

`MonitoringConfiguration` remains the owning business concept from Feature 002 and retains its id, name, description, GitLab instance URL, enabled flag, timestamps, revision and retirement state. This feature does not add the token to the aggregate or change its public response model.

## GitLab Credential (infrastructure persistence)

One credential may exist per active Monitoring Configuration.

| Field | Type / constraint | Meaning |
|---|---|---|
| `monitoring_configuration_id` | UUID, primary key, FK to configuration | One-to-one owner; never returned as secret metadata beyond existing configuration id. |
| `encrypted_token` | binary, non-null | Fernet authenticated ciphertext only. Raw/decrypted values must not be stored. |
| `credential_revision` | integer, positive, default 1 | Incremented atomically on replacement; fences stale validation writes. |
| `created_at` | UTC timestamp | Credential row creation time; unchanged on replacement. |
| `updated_at` | UTC timestamp | Latest credential creation/replacement time. |
| `last_validation_result` | bounded string/enum, nullable | Safe normalized category for latest validation of the saved credential; candidate validations do not modify it. |
| `last_validated_at` | UTC timestamp, nullable | Time of latest completed validation of the saved credential. |
| `last_successful_validation_at` | UTC timestamp, nullable | Latest successful validation time. A later failed validation of the same saved credential preserves this timestamp; credential replacement/removal or URL change invalidates it for the current connection. |
| `validated_url_fingerprint` | fixed-length digest, nullable | Non-secret fingerprint of normalized URL checked; mismatch invalidates previous result when configuration URL changes. |

The status `not_configured` is derived from absence of a row. `configured_not_validated` is derived when a row exists but no current successful validation applies, including a credential revision change or URL fingerprint mismatch. `validated` and `failed` represent the latest saved-credential check; `failed` may coexist with a retained `last_successful_validation_at` for the same credential revision and URL. `validating` is transient frontend state, not persisted business state.

Do not retain validation attempt history, GitLab profile/group data, upstream bodies, HTTP headers, raw URLs in validation logs, tokens, or encryption keys in this table.

## Transient values

- `SubmittedGitLabToken`: opaque transient request/use-case value; preferably secret-wrapped so its representation is redacted. Never part of domain entities, response DTOs, logs or persistence model.
- `ConnectionValidationAttempt`: configuration id, URL snapshot, token source (saved/candidate), saved credential revision when applicable, and result category. Must not retain token after the request completes.
- `GitLabConnectionStatus`: response-safe state, `credential_configured`, safe result category/message, and timestamps only.

## Relationships and lifecycle

`MonitoringConfiguration` 1 — 0..1 `GitLabCredential`. Encrypt a replacement token before changing persistence; replace ciphertext and increment revision atomically so encryption or transaction failure leaves the previous credential usable. Successful replacement resets credential-specific validation metadata and success time. Explicit removal deletes the row and all its validation metadata and is idempotent. Feature 002 retirement is soft-delete; the retirement use case deletes the credential in the same transaction. Future physical configuration deletion is protected by the FK cascade, but no history cascade is introduced.

## Consistency rules

1. Credential persistence requires successful Fernet encryption; no plaintext fallback.
2. A candidate validation never creates/updates a credential row or saved-credential status.
3. A saved validation can write result metadata only when both revision and normalized-URL fingerprint still match the values read before the GitLab call.
4. URL mismatch makes prior status stale without changing credential ciphertext or unrelated configuration values.
5. All persisted dates are UTC-aware; API timestamps use ISO 8601 UTC.
