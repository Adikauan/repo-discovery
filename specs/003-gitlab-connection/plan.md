# Implementation Plan: GitLab Connection

**Branch**: `003-gitlab-connection` | **Date**: 2026-09-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-gitlab-connection/spec.md`

## Summary

Extend the existing Monitoring Configuration details experience with secure credential save, replacement, removal, status and explicit connection validation. Keep raw token handling at request boundaries and in short-lived application memory, encrypt credentials through a dedicated infrastructure adapter, and validate through an application-owned GitLab port. Validation makes one bounded, read-only authenticated-user API call and stores safe metadata against the exact saved credential revision and URL that were checked. It does not certify permissions required by future discovery.

## Technical Context

**Language/Version**: Python 3.13+ (<3.15) backend; TypeScript frontend
**Primary Dependencies**: Existing FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, PostgreSQL, React, Vite, Material UI, React Router; add `cryptography` for authenticated encryption and promote existing HTTPX to a runtime dependency for the GitLab adapter.
**Storage**: Existing PostgreSQL database; new one-to-one credential table, changed only through Alembic migration.
**Testing**: pytest and TestClient for backend; Vitest and Testing Library for frontend; PostgreSQL migration/integration checks; HTTPX MockTransport for provider behavior.
**Target Platform**: Existing web application deployment and local Compose environment; GitLab SaaS or compatible self-managed GitLab instance.
**Project Type**: Web application with separate frontend and Clean Architecture backend.
**Performance Goals**: No formal performance benchmark in this feature. GitLab checks have finite connect/read timeouts and make only the minimum bounded requests required by the specification.
**Constraints**: No plaintext credential persistence or disclosure; no redirects while sending credentials; no discovery results; no automatic enablement; no open database transaction during network validation; backend remains authoritative for configuration existence and credential state. Credential-write and candidate-validation request tokens are opaque nonblank values limited to 2048 UTF-8 bytes; invalid values receive a safe 422 before encryption, persistence, or provider access. Backend and frontend tests must run without live PostgreSQL; PostgreSQL-specific migration/integration validation is separate when unavailable, and SQLite must not substitute for PostgreSQL.
**Scale/Scope**: One active credential and current validation metadata per Monitoring Configuration; no validation-attempt history, group/repository discovery, KMS integration, automated key-rotation service, or authentication/authorization.

## Constitution Check

| Principle | Gate | Design evidence |
|---|---|---|
| Clean Architecture and responsibility separation | PASS | Domain contains no HTTP, ORM, encryption, or UI types; application use cases coordinate ports; infrastructure implements adapters; API and React remain presentation layers. |
| Domain independence | PASS | GitLab and credential behavior are expressed through application-owned types/ports; cryptographic and HTTP details stay in infrastructure. |
| Explicit/versionable API contracts | PASS | New versioned REST routes use dedicated Pydantic request/response DTOs; token is accepted only on write/validate requests and never returned. |
| Incremental feature boundaries | PASS | Feature adds connection setup only; discovery and mining remain deferred. |
| Business rules in domain/application | PASS | The frontend sends no credential request for blank replacement UI state; API/request validation enforces presence, nonblank content and the UTF-8 byte limit; application use cases receive only valid mutation commands and never interpret blank as preserve; domain/application logic owns replacement and optimistic-concurrency semantics, candidate isolation, state invalidation and retirement cleanup. |
| External integration abstraction | PASS | GitLab validation depends on a port, implemented by an HTTPX adapter. |
| Secrets protected end-to-end | PASS | Fernet ciphertext at rest; secure external key configuration; masked short-lived frontend input; response/log redaction tests. |
| Historical executions reproducible | PASS | No execution data exists here; credential remains configuration state, and is deleted on configuration retirement rather than attached to history. |
| Common pipeline / concurrency safety | PASS | No mining pipeline is introduced. Version-checked status updates prevent stale validation from overwriting state after URL/token changes. |
| Idempotency where appropriate | PASS | Credential removal and status retrieval are naturally repeatable; replacement writes are atomic and validation does not mutate credentials. |
| Migration-managed schema | PASS | Dedicated Alembic migration adds/removes the credential table. |
| Automated coverage | PASS | Unit, use-case, adapter, API, persistence, security and UI tests are planned. |
| Usable consistent UX | PASS | Existing shell and shared loading/error/feedback/status components are reused; explicit status and safe failure messages are planned. |
| Maintainability/dependencies | PASS | Two justified runtime dependencies only; no KMS, state-management library, or broad abstraction framework. |
| Spec/plan/task traceability | PASS | Contracts and test matrix map to FR/SC requirements; tasks are generated from these artifacts. |

**Pre-design gate**: PASS. The specification is implementable; provider endpoint, encryption, storage, and UI integration decisions are documented in `research.md`.

## Architecture and Project Structure

### Backend

Extend the current `backend/app` layout without moving Feature 002 code:

```text
backend/app/
  domain/
    entities/gitlab_connection_status.py
    value_objects/connection_validation_result.py
    ports/gitlab_connection_client.py
    ports/credential_cipher.py
    ports/gitlab_credential_repository.py
  application/use_cases/
    save_gitlab_credential.py
    remove_gitlab_credential.py
    get_gitlab_connection_status.py
    validate_gitlab_connection.py
  infrastructure/
    crypto/fernet_credential_cipher.py
    gitlab/http_gitlab_connection_client.py
    database/models.py                         # GitLabCredentialRecord
    database/sqlalchemy_gitlab_credential_repository.py
    database/unit_of_work.py                   # include credential repository/atomic retire cleanup
  api/v1/
    gitlab_connections.py
    schemas.py                                  # safe status and write/validation DTOs
    errors.py                                   # stable safe connection error mapping if needed
  config.py                                    # encryption key-ring and GitLab timeout settings
backend/alembic/versions/<revision>_gitlab_credentials.py
backend/tests/
  unit/crypto/; unit/application/; unit/infrastructure/gitlab/
  integration/api/; integration/database/
```

Keep the existing MonitoringConfiguration domain/entity and Feature 002 API response free of credential values. Extend the existing configuration-retirement use case so credential removal and retirement are atomic. Configuration URL updates do not require a cross-feature write hook: status retrieval compares a stored non-secret URL fingerprint with the current normalized URL and derives `configured_not_validated` on mismatch; validation status is written only if both URL fingerprint and credential revision still match.

### Frontend

```text
src/features/monitoring-configurations/
  api/gitlabConnectionApi.ts
  components/GitLabConnectionPanel.tsx
  components/GitLabCredentialForm.tsx
  hooks/useGitLabConnection.ts
  types/gitlabConnection.ts
  pages/MonitoringConfigurationDetailsPage.tsx  # compose panel using existing shell
src/test/features/monitoring-configurations/gitlab-connection*.test.tsx
```

Use the established Feature 001/002 shell, theme, `ContentCard`, status, alert, and loading/error patterns. Avoid a shell redesign or new global state. The token input is password-masked, is never hydrated from API data or written to browser storage, and is cleared after completion, cancellation, or unmount. The client retains it only in the active submission flow and does not cache it in a query cache. Removal is a deliberate user action; use the existing confirmation-dialog pattern if confirmation is included. After removal, status is `not_configured` and credential-specific validation metadata is removed with the credential.

## Domain and Application Boundaries

- `GitLabCredential` is infrastructure persistence state, not a field on the MonitoringConfiguration domain entity. The raw token is transient input to a use case; ciphertext is repository-only data.
- Public `GitLabConnectionStatus` contains only credential presence, safe current result category/state, last attempt time if useful, and last successful validation time. Credential revision and normalized-URL fingerprint are internal-only metadata permitted in persistence models, repository snapshots, and application-internal snapshot types; they never enter public API DTOs, frontend TypeScript response contracts, logs, or user-visible status payloads. Never include token or encrypted-token material in either status type.
- Application use cases depend on an explicit `CredentialCipher` port exposing only `encrypt` and `decrypt`; the Fernet/MultiFernet implementation remains in infrastructure and encryption is not hidden inside the credential repository.
- Use cases: save/replace credential, remove credential, retrieve status, validate persisted or candidate token. Existing configuration retirement also removes the credential in the same unit of work.
- The dedicated credential PUT accepts an opaque token only when it is non-empty, not whitespace-only, and at most 2048 UTF-8 bytes. Missing, empty, whitespace-only, and oversized values are rejected at the API/request boundary with the standard safe 422 before a cipher or repository call. A token exactly at the byte limit is accepted, including opaque multibyte content. The frontend sends no credential request when an unrelated edit leaves replacement blank; application use cases receive only valid mutation commands and never interpret blank as preserve. A valid save atomically replaces ciphertext through internal optimistic concurrency, increments revision and resets saved-connection result to configured/not validated. Removal is idempotent for an active configuration.
- Validation does network I/O outside a database transaction. For a saved token, read/decrypt a versioned snapshot, call GitLab, then conditionally write metadata only if credential revision and URL fingerprint are unchanged. A stale result is not applied and returns a safe conflict outcome. Candidate validation does not persist the candidate or modify saved metadata.
- No connection action changes `enabled`, other configuration fields, or invokes discovery/mining.

## Persistence and Encryption

Add `gitlab_credentials` with `monitoring_configuration_id` as primary key and FK to `monitoring_configurations.id`, `ON DELETE CASCADE` only for eventual physical deletion, non-null encrypted token bytes, UTC `created_at`/`updated_at`, positive credential revision, safe latest validation result/time, `last_successful_validation_at`, and nullable fingerprint of the normalized GitLab URL used for the latest saved-token validation. Do not duplicate the GitLab URL. The current Feature 002 retirement is soft-delete, so its application use case must explicitly remove the credential in the same transaction. Do not persist a validation-attempt history.

Use optimistic concurrency compatible with the existing SQLAlchemy/PostgreSQL unit of work. Each operation reads an internal credential snapshot and captures expected revision N before persistence; its update succeeds only when the stored revision still equals N. With two operations starting at N, the first commit writes N+1 and the second compare-and-swap affects no row, producing a normalized conflict mapped to HTTP 409 without credential material. A delayed in-flight N operation behaves identically after N+1 commits. Persistence failure before commit leaves the credential and revision unchanged. If a commit succeeds but the client receives an uncertain response, the committed value remains authoritative; a later PUT starts from the then-current revision and is a new intentional replacement, not an implicit deduplicated or stale request. Revision remains internal to persistence/repository/application snapshots and is never added to public request or response DTOs. Do not introduce distributed locking or a new idempotency subsystem.

Use UTC-aware timestamps and portable SQLAlchemy types. Apply an Alembic migration with reversible upgrade/downgrade and test it against the project's PostgreSQL baseline. API serializers must use explicit DTO mapping, never ORM entity serialization.

The migration adds only the optional credential table; it does not alter, backfill, or require credentials for existing Monitoring Configurations. Existing configurations remain valid with no credential row. Tests that need only unit/API behavior use repository fakes; migration and PostgreSQL behavior are validated against PostgreSQL when available, never SQLite.

Use `cryptography` Fernet/MultiFernet as the initial authenticated-encryption mechanism. Supply an ordered key ring via secret configuration (for example, `GITLAB_CREDENTIAL_ENCRYPTION_KEYS`, first key encrypts and all configured keys decrypt during rotation). Document the variable in deployment configuration and `.env.example` using a placeholder only; never commit a real key. If configuration is absent/malformed, credential save/replace must fail safely with a generic service error; the existing application may continue serving unrelated Feature 002 routes. Never fall back to plaintext. Keep keys outside database and source control. Operators must back up keys separately; before retiring an old key, re-encrypt data with the new first key. Automated rotation/KMS are deferred.

## GitLab Adapter and Validation Protocol

Application use cases call a `GitLabConnectionClient` port. The HTTPX implementation:

1. Uses the existing GitLab instance URL, preserves self-managed base paths, normalizes trailing slashes and duplicate separators, and appends `/api/v4`.
2. Sends the token only in `PRIVATE-TOKEN`; does not include it in URLs, bodies, errors, or logs.
3. Uses TLS verification, `follow_redirects=False`, and explicit configurable HTTPX defaults: connect timeout 5 seconds, read timeout 10 seconds, write timeout 5 seconds, and pool timeout 5 seconds. Environment-backed application settings may override each value, but parsing rejects zero, negative, NaN, positive infinity and negative infinity with a safe configuration/startup error; it never silently substitutes an unsafe value, exposes secrets, or mutates unrelated behavior. Do not add automatic retries.
4. Calls only `GET /user` to verify reachability, token acceptance, and success of this authenticated validation endpoint. It discards the response body after status/basic-shape checks; success does not certify permissions for Feature 004 group, subgroup, project, or repository discovery.
5. Returns normalized typed outcomes rather than raw HTTP responses or exception-string parsing: `success`, `invalid_url`, `invalid_credentials` (401), `forbidden` (403), `unreachable` (DNS/connect/TLS), `timeout`, `invalid_response`, and safe `rate_limited`/`provider_unavailable` categories. Malformed URLs, unsupported schemes, and URLs that cannot produce a valid API base URL map to `invalid_url`, separately from network failures. Safe user messages omit upstream response bodies, headers and exception strings.

Recommend the narrowest token permission supporting `GET /user` (commonly `read_user`); `read_api` also works but is not needed for this feature's validation call. Do not parse token text or require one particular token type; observed endpoint access determines success. Avoid redirects because they could forward credentials to another origin. Feature 004 will define any additional permissions needed for discovery.

## API Contract Strategy

Publish explicit OpenAPI/Pydantic schemas for these final routes: `GET /api/v1/monitoring-configurations/{id}/gitlab-connection`, `PUT /api/v1/monitoring-configurations/{id}/gitlab-connection/credential`, `DELETE /api/v1/monitoring-configurations/{id}/gitlab-connection/credential`, and `POST /api/v1/monitoring-configurations/{id}/gitlab-connection/validate`. Exact payloads, normalized result enums, status codes, idempotency and failure shapes are specified in [contracts/api-v1.md](contracts/api-v1.md). Credential reads return only presence/status/timestamps. `PUT` atomically replaces; `DELETE` removes. Validation can use the saved credential or accept a one-request candidate token, which is never stored. A 409 safely indicates that the saved URL/credential changed during validation; configuration-not-found uses 404; validation without any credential uses 409. Error responses never include encrypted values, key configuration, upstream body or stack trace.

The dedicated credential endpoint is the only credential-write operation. It rejects missing, empty, whitespace-only, and greater-than-2048-UTF-8-byte tokens with the standard safe 422 before encryption or persistence and accepts opaque nonblank tokens through exactly 2048 UTF-8 bytes without format parsing. The existing Monitoring Configuration update contract carries no credential fields; blank replacement UI state preserves a credential by making no credential request. A blank credential PUT is never a preserve operation. Removal uses explicit DELETE.

## Frontend Integration and UX

Add a GitLab Connection panel to existing configuration details. It must distinguish not configured, configured-not-validated, transient validating, validated, and failed. Display only safe state and last successful time. Provide separate save/replace, explicit remove, validate-saved and validate-candidate actions. Saving is independent of validation; candidate validation does not save. All actions leave configuration enablement unchanged. Use a password field with appropriate autocomplete behavior and explicit clearing on success, failure, cancel/navigation and unmount. Do not persist form state or request body in local/session storage, URL, logs, or a frontend cache. Handle backend-unavailable, not-found, validation, conflict, and categorized provider feedback using shared components.

## Test Strategy and Traceability

| Requirement group | Verification |
|---|---|
| FR-001–008, FR-027–028; SC-001, SC-002, SC-005, SC-009 | Use-case/API/security tests prove write/read behavior, encrypted-only storage, no response/log/storage leakage, mask/clear behavior and blank-preserve semantics. |
| FR-009–016, FR-019, FR-023–024, FR-029; SC-003–006, SC-010–011 | Port unit tests with HTTPX MockTransport cover the authenticated-user endpoint, base path, header use, success, malformed/unsupported/unusable API URLs, DNS/connect/TLS/timeout, 401/403/429/5xx and malformed response. Application/API/UI tests prove failed saved-credential validation never removes or overwrites the credential, keeps configured=true and enabled unchanged, preserves the last-success timestamp (or null), and allows later retry/replace/remove. Concurrency tests cover stale revision/URL and candidate metadata isolation. |
| FR-017–018, FR-022, FR-026; SC-007–008 | Application and API tests assert enabled/unrelated fields unchanged, no discovery operation exists, and retirement atomically removes active credential. |
| FR-020–021, FR-025; all relevant SC | OpenAPI/contract and frontend behavior tests cover status, save/replace/remove/validate, safe errors, no duplicate in-flight submission, route integration and shared visual patterns. |
| FR-002–003, FR-021, FR-028; SC-001, SC-012–013 | Boundary tests cover missing/empty/whitespace-only 422 responses, exact and excessive 2048-byte limits including multibyte input, no cipher/repository call or disclosure on rejection, and deterministic internal compare-and-swap outcomes: one N+1 winner plus safe 409 loser, unchanged state on pre-commit failure, authoritative commit after uncertain response, new subsequent PUT semantics, and delayed-N conflict. |
| Schema | Upgrade/downgrade migration tests on PostgreSQL; ciphertext-at-rest and repository round-trip tests. |

Backend layers: domain/application unit tests; adapter tests use injected fake transport; API tests use TestClient and controlled ports; PostgreSQL integration tests run migrations when PostgreSQL is available. Keep ordinary backend and frontend tests independent of a live database; do not substitute SQLite. Report PostgreSQL migration/integration validation separately when the local service is unavailable. Add sentinel-token assertions to API response serialization and captured logs on success and failure. Verify secret absence in telemetry mechanisms already present in the project, where applicable: logs, HTTP error output, exception messages, traces, metrics labels/attributes, and telemetry events. Record nonexistent telemetry categories as not applicable; do not introduce telemetry infrastructure. Assertions cover raw/decrypted tokens, authorization headers, and ciphertext. Frontend Vitest tests assert no token appears in response-derived status, browser storage, DOM after completion, or retained component state. No real GitLab credentials are required by automated tests.

Minimum backend cases: Fernet encryption before persistence and intended-service-only decryption; create/replace/remove/status; missing/empty/whitespace-only credential PUT rejection; exact-2048-byte acceptance and oversized/multibyte byte-count rejection before cipher/repository calls; failed encryption or persistence preserves prior ciphertext; deterministic two-operation N/N concurrency with one N+1 commit and one safe 409, unchanged state on pre-commit failure, authoritative server commit after uncertain client response, later PUT as a new replacement, and delayed-N conflict; retired/missing configuration; validation without a credential; success; invalid credentials; forbidden; unreachable; timeout; invalid response; malformed URL; unsupported URL scheme; URL that cannot produce a valid GitLab API base URL; configured finite HTTPX timeout propagation; rejection of zero, negative, NaN, positive-infinity and negative-infinity timeout settings without secret exposure, unsafe fallback or unrelated mutation; safe API response/log/available-telemetry redaction including internal revision/fingerprint absence; candidate validation does not mutate saved credentials or metadata; each failed saved-credential outcome retains the exact stored credential, configured=true, enabled status, and prior last-success timestamp (or null); URL/credential revision races do not write stale results. All HTTP calls use mocked transport.

Minimum frontend cases: not-configured and configured states; token save/replacement with no persisted-token display; clearing sensitive input; remove action; validation loading/success/invalid-credential/forbidden/unavailable/timeout/unexpected feedback; failed saved validation leaves configured status and enablement intact and preserves the prior last-success time; candidate result distinct from saved status; malformed/unsupported/unusable GitLab URL feedback distinct from reachability failures; errors and unavailable configuration; no local/session storage or URL/query-string token persistence.

## Operational and Security Considerations

- Add encryption configuration and positive finite GitLab connect/read/write/pool timeout settings to application configuration and deployment/Compose wiring through environment injection; defaults are 5/10/5/5 seconds respectively. T002 owns adding placeholder/default names to `.env.example`, never a usable encryption key. T040 is documentation-only and must not modify `.env.example`.
- Generate a Fernet key for local use through `cryptography.fernet.Fernet.generate_key()` and place it only in ignored `.env` or a deployment secret manager. Do not print it in logs or commit it.
- Do not log request/response objects, token-bearing schemas, decrypted values, cryptographic exception details, or HTTPX errors that may retain request context. Log only configuration id, safe outcome category, and timing where useful.
- Retain default TLS certificate verification. HTTP GitLab URLs remain governed by existing Feature 002 URL acceptance; deployments should use HTTPS for non-local instances.
- Key loss makes encrypted credentials unrecoverable. Document separate backup and rotation responsibility; do not silently clear/decrypt-fail as if no credential existed.

## Deferred Functionality

Explicitly excluded: group/subgroup/project/repository discovery, repository tree/selection, scheduling, mining, execution pipeline/history, findings/dashboard, authentication/authorization, full audit history, KMS/HSM service, automated key rotation, and unrelated shell redesign.

## Post-design Constitution Check

| Gate | Result | Evidence |
|---|---|---|
| Domain/infrastructure separation | PASS | Secret cipher, ORM and HTTPX remain adapters behind ports. |
| No credential disclosure | PASS | Read DTOs are status-only; no raw token in logs/frontend persistence; encryption key external to DB. |
| API contract and business-rule ownership | PASS | Explicit versioned DTOs; use cases own preservation/replacement/invalidation/concurrency rules. |
| Persistence and migration discipline | PASS | New table only through Alembic; retirement cleanup is transactional. |
| Test coverage | PASS | Traceability matrix maps security, domain, API, adapter, migration and UI tests to FR/SC. |
| Scope/maintainability | PASS | Only credential lifecycle and validation are implemented; two dependencies have direct need. |

**Complexity Tracking**: None. No constitution violations or unjustified abstractions are introduced.
