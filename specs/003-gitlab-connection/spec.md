# Feature Specification: GitLab Connection

**Feature Branch**: `003-gitlab-connection`

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "Create Feature 003 - GitLab Connection. Extend Monitoring Configuration with secure GitLab access-token storage, credential replacement and removal, credential status, and explicit connection validation. Never disclose raw tokens; encrypt persisted credentials; validate reachability, authentication, and basic authenticated API access. Do not implement discovery, selection, scheduling, mining, executions, findings, analytics, authentication, or authorization."

## Clarifications

### Session 2026-09-28

- Q: If a saved credential validated successfully before, but a later validation fails, should the UI keep showing the time of the earlier successful validation alongside the latest failure? → A: Preserve the earlier successful validation time and show the latest attempt's failure separately, with clear labels.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure GitLab Credentials (Priority: P1)

As a platform user, I can save, replace, and remove a GitLab access token for a Monitoring Configuration without exposing its stored value, so that the application can securely use the credential for later GitLab operations.

**Why this priority**: Credential management is the foundation for a safe GitLab connection and for later repository discovery.

**Independent Test**: Save a token and verify only configured status is returned; reopen the page and verify the raw value is absent; replace it and verify the replacement is used. During an unrelated Monitoring Configuration edit, leave the replacement field blank and verify the frontend sends no credential PUT and the existing credential remains unchanged. Separately issue credential PUT requests with a missing, empty, and whitespace-only token and verify each returns HTTP 422 without changing the existing credential. Remove the credential and verify the configuration and its unrelated fields remain.

**Acceptance Scenarios**:

1. **Given** an active Monitoring Configuration has no credential, **When** the user submits a valid token for saving, **Then** the credential is persisted securely, the configuration reports that a credential is configured, the submitted value is cleared from the form after the request, and the configuration's enabled status is unchanged.
2. **Given** a credential is already configured, **When** the user opens or edits its connection settings, **Then** the existing token is not returned or rendered and the interface indicates that a credential is configured.
3. **Given** a credential is configured, **When** the user saves a non-empty replacement token, **Then** the replacement becomes the sole credential used by later validation and the previous credential is no longer used.
4. **Given** a credential is configured, **When** the user edits unrelated Monitoring Configuration fields while the replacement-token field is blank, **Then** the frontend does not call the dedicated credential endpoint and the existing credential is preserved. A direct blank credential write is invalid and never means preserve.
5. **Given** a credential is configured, **When** the user explicitly removes it, **Then** the connection becomes not configured while the Monitoring Configuration and its unrelated values remain.
6. **Given** a credential-save operation fails, **When** the API reports failure, **Then** no plaintext credential is persisted or returned and the user receives safe, understandable feedback.
7. **Given** the user is entering a token, **When** the token is typed or pasted, **Then** the form masks its characters and does not place it in browser storage.
8. **Given** a credential is configured, **When** the dedicated credential endpoint receives a missing, empty, or whitespace-only token, **Then** it returns HTTP 422 through the standard validation contract and leaves the existing credential unchanged because no mutation occurs, not because blank input is interpreted as a preserve command.

---

### User Story 2 - Validate GitLab Connection (Priority: P1)

As a platform user, I can explicitly test a Monitoring Configuration's GitLab connection, so that I know whether the instance is reachable, the token is accepted, and the basic authenticated validation endpoint succeeds.

**Why this priority**: A stored credential alone does not show whether the GitLab instance is reachable, the token is accepted, or the authenticated validation endpoint succeeds. This check does not establish permissions for future discovery.

**Independent Test**: Validate a saved credential against controlled GitLab responses and verify success only when the instance is reachable, the token is accepted, and the authenticated API endpoint used for validation succeeds. Exercise each failure category; confirm the result does not certify group/repository discovery permissions and that displayed outcomes contain no token, sensitive header, encrypted value, or stack trace.

**Acceptance Scenarios**:

1. **Given** a configuration has a saved credential, **When** the user explicitly validates the connection, **Then** the system uses that configuration's GitLab URL and saved token, reports progress, and presents the resulting outcome.
2. **Given** the user supplies a new token for an explicit validation without saving it, **When** validation completes, **Then** the system tests the supplied token without persisting or replacing the saved credential and discards the submitted value after the request completes.
3. **Given** the GitLab instance is reachable and the credential authenticates with basic API access, **When** validation succeeds, **Then** success is clearly reported and the last successful validation time is available where connection metadata is shown. This result does not certify the permissions required for future group or repository discovery.
4. **Given** the user has no saved credential and supplies no token for validation, **When** validation is requested, **Then** it is not sent and the user is told that a credential is required.
5. **Given** a token or GitLab URL has changed since a successful validation, **When** the saved connection is viewed, **Then** the former success is not presented as validation of the changed connection; it returns to configured but not yet validated until explicitly checked again.
6. **Given** a validation is in progress, **When** the result is pending, **Then** the interface shows a distinct in-progress state and prevents ambiguous duplicate submission for that same form action.
7. **Given** a validation fails, **When** the user sees the outcome, **Then** the message identifies an actionable category such as invalid URL, unreachable instance, timeout, token rejection, forbidden access to the validation endpoint, or unexpected response without disclosing sensitive values or internal diagnostics.
8. **Given** validation reports success, **When** the connection is viewed later, **Then** the displayed success represents the latest known validation only and does not claim that the token remains valid indefinitely.
9. **Given** a saved credential has a previous successful validation, **When** a later validation attempt fails, **Then** the current state shows the latest failure while the time of the earlier successful validation remains available and is clearly identified as the last successful validation.
10. **Given** a saved credential is used for validation and the attempt fails because the token is invalid or expired, the validation endpoint is forbidden, GitLab is unreachable, the request times out, or GitLab returns an unexpected response, **When** the result is recorded, **Then** the credential remains stored and configured, its value is not overwritten, the configuration's enabled status is unchanged, the latest validation status may be failed, and the last successful validation time remains unchanged (or absent if there was no prior success). The user can retry, replace the credential, or explicitly remove it.

---

### User Story 3 - Preserve Configuration Lifecycle and Scope (Priority: P2)

As a platform user, I can manage and validate GitLab connection settings without changing the Monitoring Configuration's independent lifecycle or triggering repository work, so that connection setup remains a safe, focused step.

**Why this priority**: GitLab access must be testable without unexpectedly enabling a configuration or starting functionality reserved for later features.

**Independent Test**: Save, replace, remove, and validate credentials on an enabled and disabled configuration; verify the enabled value and all unrelated configuration fields remain unchanged and no group or repository results are requested or displayed.

**Acceptance Scenarios**:

1. **Given** a configuration is disabled, **When** its credential is saved or its connection is validated successfully, **Then** it remains disabled.
2. **Given** a configuration's connection is changed, **When** that change is saved or removed, **Then** its name, description, identifier, and enabled status remain unchanged.
3. **Given** a connection validates successfully, **When** the result is displayed, **Then** no group, subgroup, project, or repository discovery is performed or implied.
4. **Given** a Monitoring Configuration is retired, **When** its associated credential is no longer needed for active management, **Then** the credential is removed and is not retained as historical execution data.

### Edge Cases

- A dedicated credential-write token is missing, empty, whitespace-only, exactly 2048 UTF-8 bytes, or exceeds 2048 UTF-8 bytes, including multibyte input whose character count differs from its byte count.
- Two credential replacements start from the same internal revision, one commits first, and the other later attempts to commit against its stale captured revision.
- A credential replacement commits but its client receives an uncertain network response; the server commit remains authoritative, and any later PUT is a new intentional replacement rather than a stale retry.
- A replacement credential is submitted while a prior credential exists, and validation of the replacement fails.
- A blank replacement is submitted when a credential exists versus when no credential exists.
- A removal is repeated, or removal is requested when no credential exists.
- The GitLab URL is malformed, changes while a request is in progress, or points to an instance that cannot be reached.
- DNS resolution fails, the request times out, the instance returns a server error, or it returns an unexpected response.
- A token is expired, revoked, or invalid, or the authenticated validation endpoint returns forbidden; validation does not test permissions for discovery endpoints.
- The user navigates away while a save or validation is in progress; no stale response may expose or restore the submitted token in the interface.
- A previous validation succeeded, but the token or URL changes, or the token is later revoked externally.
- Encryption configuration is absent or unusable when a credential is submitted; no plaintext fallback is permitted.
- The Monitoring Configuration becomes unavailable or is retired during credential or validation operations.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST associate a GitLab access credential with an existing Monitoring Configuration and MUST continue to use that configuration's existing GitLab instance URL.
- **FR-002**: `PUT /api/v1/monitoring-configurations/{id}/gitlab-connection/credential` is the authoritative dedicated credential-write operation. It MUST accept an opaque, non-empty token of at most 2048 UTF-8 bytes without GitLab-specific format parsing. A missing, empty, whitespace-only, or greater-than-2048-byte token MUST return HTTP 422 through the standard validation error contract without calling encryption or persistence, echoing any part of the token, or modifying an existing credential. A token exactly 2048 UTF-8 bytes MUST be accepted.
- **FR-003**: Blank-preserve behavior applies only when editing unrelated Monitoring Configuration fields or when the frontend elects not to call the dedicated credential endpoint because its replacement field is blank. Per FR-002, a blank credential PUT MUST return HTTP 422 and MUST NOT be interpreted as preservation.
- **FR-004**: Users MUST be able to explicitly remove a configured credential without deleting the Monitoring Configuration or changing its unrelated values.
- **FR-005**: The system MUST expose whether a credential is configured without returning its raw or decrypted value. The frontend MUST NOT require a persisted token value to render connection settings.
- **FR-006**: The system MUST encrypt each persisted raw token using a server-side encryption mechanism before storage. Raw tokens MUST NOT be stored as plaintext, and encryption keys MUST be provided through secure application configuration and kept separate from the encrypted credential record.
- **FR-007**: If secure encryption configuration is unavailable or unusable, credential persistence MUST fail safely; the system MUST NOT store plaintext or return encryption details to the user.
- **FR-008**: Raw tokens, decrypted tokens, encryption keys, sensitive authorization headers, and encrypted credential values MUST NOT appear in API responses, application logs, telemetry, browser storage, or error messages. A raw token may exist in frontend memory only as needed for its initial submission and MUST be cleared when that submission/validation flow completes or is abandoned.
- **FR-009**: Users MUST be able to explicitly validate a connection using the configured GitLab URL and either the saved credential or a token provided for that validation request.
- **FR-010**: A token provided only for validation MUST be opaque, non-empty, not whitespace-only, and at most 2048 UTF-8 bytes under the same byte-count and safe-422 boundary rules defined by FR-002. It MUST be used only for that validation attempt and MUST NOT be saved or replace a credential unless the user separately invokes the FR-002 credential-write operation. It MUST be cleared from the frontend when the validation request completes or is abandoned.
- **FR-011**: Validation MUST determine whether the GitLab instance is reachable, the token authenticates, and the authenticated account can access a basic authenticated API resource. Validation MUST NOT claim that the account has permissions required for future group or repository discovery. Validation MUST NOT enumerate, return, or persist group, subgroup, project, or repository discovery results.
- **FR-012**: A validation request MUST NOT be available when neither a saved credential nor a token for the current validation request is provided; the user MUST receive clear guidance to configure a credential first.
- **FR-013**: The system MUST provide user-facing states for not configured, configured but not yet validated, validation in progress, successfully validated, and validation failed.
- **FR-014**: A successful validation MUST record or expose the last successful validation time where connection metadata is presented. If a later validation of the same saved credential fails, the system MUST preserve that earlier successful-validation time while reporting the latest result as failed; the time MUST be clearly labeled so it is not mistaken for current success. A displayed success MUST be understood as the latest known validation result, not a guarantee of future token validity.
- **FR-015**: Replacing a credential or changing the GitLab URL MUST invalidate the prior success state for the current saved connection and return it to configured but not yet validated until a new explicit validation succeeds.
- **FR-016**: Validation of an unsaved candidate token MUST NOT change the saved credential's validation metadata. A failed candidate validation MUST NOT replace or remove a previously saved credential.
- **FR-017**: Saving, replacing, removing, or validating a credential MUST NOT automatically enable or disable the Monitoring Configuration, start repository discovery, or start mining.
- **FR-018**: Replacing or removing a credential MUST leave the Monitoring Configuration identifier, name, description, GitLab URL (unless separately changed), and enabled status unchanged.
- **FR-019**: The system MUST present understandable validation outcomes for malformed or unsupported GitLab URL, a URL that cannot produce a valid API base URL, unreachable instance, DNS or connection failure, timeout, invalid or expired token, authentication failure, forbidden access to the authenticated validation endpoint, and unexpected GitLab API response. URL construction failures MUST be normalized separately from network failures. Messages MUST not expose raw infrastructure exceptions or stack traces.
- **FR-020**: Connection save, removal, status retrieval, and validation MUST be available through explicit frontend/backend contracts with consistent success and error outcomes; response contracts MUST contain only credential presence and non-sensitive validation metadata, never token material.
- **FR-021**: Saving, replacing, removing, and validating credentials MUST be safe under repeated and concurrent requests where appropriate. Each replacement operation MUST internally capture the current credential revision when it starts and persist through compare-and-swap against that expected revision. If two operations capture revision N, the first successful commit creates N+1 and the second operation's commit against N MUST fail with a normalized HTTP 409 conflict; the N+1 credential remains active and no raw, decrypted, or encrypted credential material appears in the response. A persistence failure before commit MUST leave the current credential and revision unchanged. A delayed in-flight operation that captured N MUST likewise fail with 409 after another operation commits N+1. A server commit remains authoritative if the client receives an uncertain network response and MUST NOT be rolled back. A completely new PUT arriving after that commit is a new intentional replacement, not a stale retry, because no client-visible revision or precondition is exposed and no new idempotency mechanism is introduced. The one-row invariant and monotonically increasing internal revisions MUST be preserved using database/application optimistic concurrency; distributed locking is not required.
- **FR-022**: If a Monitoring Configuration is retired, its active GitLab credential MUST be removed; the retained configuration identity and any future execution history MUST NOT retain or expose the secret.
- **FR-023**: The GitLab integration MUST be replaceable behind an application-owned boundary so business rules do not depend on provider-specific HTTP details.
- **FR-024**: The GitLab integration MUST perform only the operations needed to validate reachability, authentication, and basic authenticated API access described in FR-011. Group, subgroup, project, and repository permission validation, discovery, and repository selection MUST remain out of scope and be addressed by the future discovery feature.
- **FR-025**: The frontend MUST extend the existing Monitoring Configuration interface and reuse its application shell, theme, feedback, and status presentation patterns without redesigning the shell.
- **FR-026**: The feature MUST NOT implement GitLab group or subgroup discovery, project or repository discovery, repository selection/tree, scheduling, mining, executions, execution history, findings, dashboard analytics, authentication, or authorization.
- **FR-027**: Credential entry controls MUST mask token characters and MUST NOT persist token values in browser storage. A token MUST be present in frontend memory only for the user action that submits it and MUST be cleared when that action completes or is abandoned.
- **FR-028**: GitLab access tokens MUST be treated as opaque credential values rather than interpreted as Monitoring Configuration identifiers or other application data. Credential-write requiredness, byte limits, and blank behavior are governed exclusively by FR-002 and FR-003; candidate-token persistence behavior is governed by FR-010.
- **FR-029**: A failed validation using an already persisted credential MUST NOT remove or overwrite that credential; credential configured status MUST remain true and the Monitoring Configuration enabled status MUST remain unchanged. The latest validation status MAY become failed, but the last successful validation timestamp MUST remain the time of the most recent successful attempt and MUST NOT be replaced by a failed attempt. The user MUST remain able to retry validation, replace the credential, or explicitly remove it.

### Key Entities *(include if feature involves data)*

- **GitLab Credential**: A sensitive access value associated with one Monitoring Configuration. Its raw form is submitted by the user; only encrypted form is retained by the system. The credential can be replaced or removed and is never returned in read contracts.
- **GitLab Connection Status**: Non-secret metadata that indicates whether a credential is configured and the latest known validation outcome, including the time of the last successful validation where available.
- **Connection Validation Attempt**: An explicit check of a GitLab URL and either a saved or request-provided token. It produces a success or categorized failure without storing the token in the result or performing discovery.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can save, replace, and explicitly remove a credential while unrelated Monitoring Configuration edits with a blank replacement field perform no credential request and leave the existing credential intact; direct missing, empty, whitespace-only, and oversized credential PUT requests return safe HTTP 422 responses without mutation.
- **SC-002**: Automated contract and security tests verify that a submitted token is absent from all credential status/read responses and that persisted token storage contains only encrypted credential material, not the raw token.
- **SC-003**: The connection interface can distinguish all five required user-facing states: not configured, configured but not yet validated, validation in progress, successfully validated, and validation failed.
- **SC-004**: Controlled integration tests verify that validation succeeds only when the instance is reachable, the token is accepted, and the authenticated endpoint used for validation succeeds; each required failure category produces safe, understandable feedback. Validation results do not certify future group/repository discovery permissions.
- **SC-005**: Automated checks verify tokens, authorization headers, encrypted values, and stack traces are not exposed in API responses, application logs, telemetry, or persisted frontend storage.
- **SC-006**: Replacing a token or changing the URL clears the former saved-connection success state; candidate-token validation does not replace saved credentials or their validation metadata.
- **SC-007**: Saving, replacing, removing, or successfully validating credentials leaves configuration enabled status unchanged and does not produce group, project, or repository discovery results.
- **SC-008**: A user can remove a credential while retaining the Monitoring Configuration, and retiring a configuration makes its credential unavailable without retaining it as historical execution data.
- **SC-009**: Inspection and automated UI checks verify token characters are masked during entry and no token is written to browser storage or retained in the form after submission completes.
- **SC-010**: Backend and frontend automated tests verify that failed validation of a saved credential leaves it configured and unchanged, does not change Monitoring Configuration enabled status, preserves the previous last-success timestamp (or null), and presents the failed latest result across invalid/expired token, forbidden validation endpoint, timeout, unreachable instance, and unexpected response outcomes.
- **SC-011**: Automated adapter, API, and frontend tests verify malformed URLs, unsupported schemes, and URLs that cannot produce a valid GitLab API base URL yield a normalized invalid-URL outcome distinct from network failures and without raw infrastructure exceptions.
- **SC-012**: Automated boundary tests accept opaque tokens exactly 2048 UTF-8 bytes, reject larger tokens by UTF-8 byte length before encryption or persistence, cover multibyte input, and prove validation errors disclose no submitted token content.
- **SC-013**: Deterministic application/PostgreSQL tests prove that two replacements capturing revision N produce one N+1 commit and one safe 409 conflict; a failed pre-commit persistence attempt leaves credential/revision unchanged; an uncertain client response cannot roll back a successful server commit; a subsequent PUT is treated as a new replacement; and a delayed N operation cannot overwrite N+1. All outcomes retain one active credential without credential disclosure or public revision exposure.

## Assumptions

- Feature 002's single-user Monitoring Configuration experience and existing GitLab instance URL remain the identity and ownership boundary; authentication and authorization are not introduced.
- Credential save is independent from connection validation: saving alone does not validate, and validation alone does not persist an unsaved candidate token.
- A user who wants to validate a newly saved credential saves it first and then explicitly validates the persisted credential. A user may also validate an unsaved candidate, whose result applies only to that attempt.
- The validation access check proves reachability, authentication, and basic authenticated API access only. It does not prove the permissions needed for future group or repository discovery; those permissions will be validated by the later discovery feature.
- Validation metadata is current status plus last successful validation time, not a complete history of attempts. Failure messages may state a safe category but do not persist provider response bodies or headers.
- Credential removal is idempotent. Removing a credential already absent leaves the configuration unchanged and reports the not-configured state.
- When a configuration is retired, its credential is removed because tokens are not required to preserve configuration context or future execution history.
- GitLab instances expose compatible API behavior for the connection checks required by the feature; compatibility details and timeout values are defined in the implementation plan.
- New configurations remain disabled by default as defined in Feature 002. Credential operations do not change that default or lifecycle.
- Encryption keys and database credentials are supplied through secure local/deployment configuration and are not source-controlled.
