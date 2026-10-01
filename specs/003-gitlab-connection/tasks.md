---

description: "Implementation tasks for GitLab Connection"
---

# Tasks: GitLab Connection

**Input**: Design documents from `/specs/003-gitlab-connection/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/api-v1.md`, `quickstart.md`

**Tests**: Automated tests are required by the specification and constitution. Write each listed test before its implementation and confirm it fails for the intended reason.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested as an independent increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it changes different files and has no dependency on another incomplete task in the same phase
- **[Story]**: Maps the task to a user story from `spec.md`
- Every task names the exact file or directory it changes

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add dependencies, secure configuration placeholders, and package structure used by all stories.

- [X] T001 Add `cryptography>=46,<47` and promote `httpx>=0.27,<1` from dev-only to runtime dependencies in `backend/pyproject.toml`
- [X] T002 [P] Add placeholder-only `GITLAB_CREDENTIAL_ENCRYPTION_KEYS` plus configurable `GITLAB_CONNECT_TIMEOUT_SECONDS=5`, `GITLAB_READ_TIMEOUT_SECONDS=10`, `GITLAB_WRITE_TIMEOUT_SECONDS=5`, and `GITLAB_POOL_TIMEOUT_SECONDS=5` wiring in `.env.example` and `compose.yaml`; parse positive finite timeout settings in `backend/app/config.py`; and add deterministic tests rejecting zero, negative, NaN, positive infinity, and negative infinity with a safe configuration/startup error, no unsafe fallback, no secret exposure, and no unrelated mutation in `backend/tests/unit/test_config.py`
- [X] T003 [P] Create GitLab connection package initializers in `backend/app/domain/entities/__init__.py`, `backend/app/domain/value_objects/__init__.py`, `backend/app/domain/ports/__init__.py`, `backend/app/infrastructure/crypto/__init__.py`, and `backend/app/infrastructure/gitlab/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish shared safe types, ports, persistence schema, and test substitutes before any user story work.

**CRITICAL**: Complete this phase before starting a user story.

- [X] T004 [P] Define public safe connection states/results and separate internal snapshot metadata so credential revision and normalized-URL fingerprint remain limited to application/repository internals in `backend/app/domain/entities/gitlab_connection_status.py` and `backend/app/domain/value_objects/connection_validation_result.py`
- [X] T005 [P] Define an explicit application-owned `CredentialCipher` port with only `encrypt`/`decrypt`, plus credential repository and GitLab validation interfaces without HTTP, ORM, or encryption-library types in `backend/app/domain/ports/credential_cipher.py`, `backend/app/domain/ports/gitlab_credential_repository.py`, and `backend/app/domain/ports/gitlab_connection_client.py`
- [X] T006 [P] Add explicit token-write, safe status, validation request/response, and redacted validation-error DTOs matching `contracts/api-v1.md`, enforcing the 2048 UTF-8 byte boundary and excluding credential revision and URL fingerprint from public schemas in `backend/app/api/v1/schemas.py`
- [X] T007 Implement `GitLabCredentialRecord` in `backend/app/infrastructure/database/models.py` with these data-model constraints verbatim: `monitoring_configuration_id`: "UUID, primary key, FK to configuration"; `encrypted_token`: "binary, non-null"; `credential_revision`: "integer, positive, default 1"; `created_at`: "UTC timestamp"; `updated_at`: "UTC timestamp"; `last_validation_result`: "bounded string/enum, nullable"; `last_validated_at`: "UTC timestamp, nullable"; `last_successful_validation_at`: "UTC timestamp, nullable"; `validated_url_fingerprint`: "fixed-length digest, nullable"
- [X] T008 Create a reversible `gitlab_credentials` Alembic migration with one-to-one ownership, positive revision check, bounded validation result, and `ON DELETE CASCADE` in `backend/alembic/versions/0002_gitlab_credentials.py`
- [X] T009 Implement internal snapshot reads and optimistic compare-and-swap replacement against the captured expected revision so two operations at N yield one N+1 commit and one normalized conflict, plus idempotent deletion and revision-plus-URL-fingerprint conditional metadata writes in `backend/app/infrastructure/database/sqlalchemy_gitlab_credential_repository.py` and expose the repository through `backend/app/infrastructure/database/unit_of_work.py`
- [X] T010 [P] Add redacting credential/cipher/client/repository fakes and deterministic clock helpers for ordinary tests without PostgreSQL or live GitLab in `backend/tests/fakes.py`

**Checkpoint**: Shared types, contracts, persistence boundaries, and test doubles are ready.

---

## Phase 3: User Story 1 - Configure GitLab Credentials (Priority: P1) MVP

**Goal**: Save, replace, inspect, and explicitly remove an encrypted credential without exposing it or changing the Monitoring Configuration; blank replacement UI state preserves an existing credential only by making no credential request.

**Independent Test**: Save and replace a sentinel token, verify storage contains only ciphertext and reads expose only configured status; prove missing, empty, and whitespace-only credential PUTs return 422 without mutation; prove exactly 2048 UTF-8 bytes is accepted while oversized multibyte input is rejected before encryption/persistence; verify a blank replacement during unrelated editing causes no credential request; prove two operations capturing N yield one N+1 commit and one safe 409, a delayed N commit cannot overwrite N+1, pre-commit failure changes nothing, and an authoritative commit survives an uncertain client response while a later PUT is a new replacement; then remove the credential and confirm all unrelated fields remain unchanged.

### Tests for User Story 1

- [X] T011 [P] [US1] Add Fernet/MultiFernet encryption, rotation-read, malformed/missing-key, and no-plaintext-fallback tests in `backend/tests/unit/crypto/test_fernet_credential_cipher.py`
- [X] T012 [P] [US1] Add use-case tests for create, replacement revision/reset, idempotent removal, missing/retired configuration, failure atomicity, and normalized conflict mapping when an operation's captured internal revision is stale, proving rejected input never invokes cipher/repository operations and conflict results expose no credential or revision metadata in `backend/tests/unit/application/test_gitlab_credential_management.py`
- [X] T013 [P] [US1] Add API contract tests proving missing, empty, and whitespace-only credential PUTs return safe 422; exactly 2048 UTF-8 bytes is accepted; oversized and multibyte byte-count inputs are rejected before encryption/persistence; every rejection leaves the existing credential unchanged and echoes no token substring; stale in-flight replacement conflicts return safe 409; and status/PUT/DELETE/404/409/503 responses, logs, and available telemetry disclose no secrets, revisions, fingerprints, or ciphertext in `backend/tests/api/test_gitlab_credential_management.py`
- [X] T014 [P] [US1] Add deterministic PostgreSQL tests proving: two replacements capturing N produce one N+1 commit and one 409 conflict; pre-commit persistence failure leaves credential/revision unchanged; a successful server commit survives uncertain client response and a subsequent PUT is a new replacement; a delayed N operation conflicts after N+1; one row remains active; and no credential/revision metadata is disclosed, alongside upgrade/downgrade, encrypted round-trip, one-to-one/FK, UTC timestamp, and rollback coverage in `backend/tests/integration/test_gitlab_credential_persistence.py` and `backend/tests/integration/test_migrations.py`
- [X] T015 [P] [US1] Add UI tests for configured/not-configured states, masked entry, save/replace/remove, safe feedback, blank replacement causing no credential API call during unrelated edits, and clearing on success, failure, cancel, navigation, and unmount in `src/test/features/monitoring-configurations/gitlab-credential-management.test.tsx`

### Implementation for User Story 1

- [X] T016 [P] [US1] Parse and validate the ordered encryption key ring without breaking unrelated routes in `backend/app/config.py` and implement the `CredentialCipher` port with authenticated Fernet/MultiFernet encrypt/decrypt and redacted failures in `backend/app/infrastructure/crypto/fernet_credential_cipher.py`
- [X] T017 [US1] Implement configuration existence checks, encrypt-before-mutate replacement for API-validated commands, internal expected-revision capture and compare-and-swap orchestration, safe status derivation, and idempotent removal—never interpreting blank input as preserve—in `backend/app/application/use_cases/save_gitlab_credential.py`, `backend/app/application/use_cases/get_gitlab_connection_status.py`, and `backend/app/application/use_cases/remove_gitlab_credential.py`
- [X] T018 [US1] Implement GET status, PUT credential, and DELETE credential routes with stable safe error mapping, including HTTP 409 `credential_replacement_conflict` without credential/revision disclosure for stale in-flight commits, in `backend/app/api/v1/gitlab_connections.py` and register them in `backend/app/api/main.py`
- [X] T019 [US1] Wire the cipher, credential repository, unit of work, and US1 use cases through request-scoped dependencies in `backend/app/api/dependencies.py`
- [X] T020 [P] [US1] Define frontend response types containing only approved safe metadata—never token, ciphertext, credential revision, or URL fingerprint—and status/save/replace/remove API calls with blank replacement causing no credential PUT, no secret caching, and no automatic secret-bearing retries in `src/features/monitoring-configurations/types/gitlabConnection.ts` and `src/features/monitoring-configurations/api/gitlabConnectionApi.ts`
- [X] T021 [US1] Implement transient credential state, request cancellation, input clearing, and refresh behavior in `src/features/monitoring-configurations/hooks/useGitLabConnection.ts` and `src/features/monitoring-configurations/components/GitLabCredentialForm.tsx`
- [X] T022 [US1] Render credential status and explicit removal with existing shared feedback/status/confirmation patterns in `src/features/monitoring-configurations/components/GitLabConnectionPanel.tsx` and compose it into `src/features/monitoring-configurations/pages/MonitoringConfigurationDetailsPage.tsx`

**Checkpoint**: User Story 1 is independently usable and verifiably keeps token material out of reads, logs, telemetry, and browser storage.

---

## Phase 4: User Story 2 - Validate GitLab Connection (Priority: P1)

**Goal**: Explicitly validate a saved or one-request candidate token with a bounded `GET /api/v4/user` call and report safe, current results.

**Independent Test**: Exercise saved and candidate validation against controlled success and every required failure category; verify only `GET /api/v4/user` is called, candidate state is not persisted, failed saved checks retain the credential and prior success time, and stale URL/revision results are rejected.

### Tests for User Story 2

- [X] T023 [P] [US2] Add HTTPX MockTransport tests for self-managed base paths, `PRIVATE-TOKEN`, TLS/default redirects disabled, configured connect/read/write/pool values passed as finite timeouts with 5/10/5/5-second defaults, no automatic retry, minimum response shape, and success/401/403/429/5xx/DNS-connect-TLS/timeout/invalid-response normalization in `backend/tests/unit/infrastructure/gitlab/test_http_gitlab_connection_client.py`
- [X] T024 [P] [US2] Add saved/candidate validation use-case tests for no credential, URL normalization/fingerprinting, metadata isolation, retained failed credential and last-success time, and stale credential-revision/URL races with no open transaction during HTTP I/O in `backend/tests/unit/application/test_validate_gitlab_connection.py`
- [X] T025 [P] [US2] Add validation contract tests for saved/candidate sources, candidate exact-2048-byte acceptance and empty/whitespace-only/oversized/multibyte safe-422 rejection before provider access, 200 categorized outcomes, distinct 409 conflicts, safe 422 invalid URLs, and response/log/available-telemetry absence of token, header, ciphertext, internal revision/fingerprint, provider body, exception, and stack trace in `backend/tests/api/test_gitlab_connection_validation.py`
- [X] T026 [P] [US2] Add UI tests for validating/duplicate-submit prevention, success, invalid credential, forbidden, unreachable, timeout, unexpected response, distinct invalid URL feedback, retained configured/enablement/last-success state after failure, and candidate-versus-saved isolation in `src/test/features/monitoring-configurations/gitlab-connection-validation.test.tsx`

### Implementation for User Story 2

- [X] T027 [P] [US2] Implement safe base-URL construction preserving self-managed paths and the single no-retry, no-redirect `GET /api/v4/user` adapter using configured positive finite connect/read/write/pool timeouts and typed outcomes in `backend/app/infrastructure/gitlab/http_gitlab_connection_client.py`
- [X] T028 [US2] Implement saved snapshot decrypt/validate/conditional-write and non-persisting candidate validation outside database transactions in `backend/app/application/use_cases/validate_gitlab_connection.py`
- [X] T029 [US2] Add POST validation route behavior, credential-source-specific response mapping, and stable safe 409/422/provider outcome handling in `backend/app/api/v1/gitlab_connections.py`, `backend/app/api/v1/schemas.py`, and `backend/app/api/errors.py`
- [X] T030 [US2] Add saved and candidate validation actions, transient validating state, duplicate-action guards, categorized feedback, last-success labeling, and sensitive-input clearing in `src/features/monitoring-configurations/hooks/useGitLabConnection.ts`, `src/features/monitoring-configurations/components/GitLabCredentialForm.tsx`, and `src/features/monitoring-configurations/components/GitLabConnectionPanel.tsx`

**Checkpoint**: User Story 2 validates only basic authenticated access and remains independently testable without live GitLab.

---

## Phase 5: User Story 3 - Preserve Configuration Lifecycle and Scope (Priority: P2)

**Goal**: Keep credential operations independent from enablement and unrelated configuration data, remove secrets on retirement, and perform no discovery or mining work.

**Independent Test**: Run credential actions on enabled and disabled configurations, verify all unrelated fields stay unchanged and no discovery endpoint is called or rendered, then retire a configuration and verify its credential is removed atomically.

### Tests for User Story 3

- [X] T031 [P] [US3] Add application tests proving save/replace/remove/validate never change identifier, name, description, URL, enabled state, or invoke discovery/mining behavior in `backend/tests/unit/application/test_gitlab_connection_scope.py`
- [X] T032 [P] [US3] Add PostgreSQL integration tests proving retirement atomically deletes the active credential while retaining the soft-deleted configuration and rolling back both changes on failure in `backend/tests/integration/test_configuration_retirement.py`
- [X] T033 [P] [US3] Add UI tests proving credential actions preserve enabled and unrelated fields and neither request nor imply group/project/repository discovery in `src/test/features/monitoring-configurations/gitlab-connection-scope.test.tsx`

### Implementation for User Story 3

- [X] T034 [US3] Extend retirement orchestration to delete the active credential in the same application transaction without retaining it as history in `backend/app/application/use_cases/retire_monitoring_configuration.py`
- [X] T035 [US3] Make Monitoring Configuration retirement and credential deletion commit or roll back atomically through shared transaction ownership in `backend/app/infrastructure/database/unit_of_work.py` and `backend/app/infrastructure/database/sqlalchemy_repositories.py`
- [X] T036 [US3] Keep the connection panel scoped to credential status/actions and preserve existing lifecycle controls and copy without discovery implications in `src/features/monitoring-configurations/pages/MonitoringConfigurationDetailsPage.tsx` and `src/features/monitoring-configurations/components/GitLabConnectionPanel.tsx`

**Checkpoint**: All three stories work independently and the feature remains within connection-setup scope.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify the complete security, accessibility, migration, and operational story.

- [ ] T037 [P] Execute `python -m pytest tests/unit tests/api` from `backend/` and `npm test -- --run src/test/features/monitoring-configurations/gitlab-credential-management.test.tsx src/test/features/monitoring-configurations/gitlab-connection-validation.test.tsx` from the repository root, with deterministic assertions in `backend/tests/api/test_gitlab_credential_management.py`, `backend/tests/api/test_gitlab_connection_validation.py`, and `src/test/features/monitoring-configurations/gitlab-credential-management.test.tsx` proving API responses exclude raw token, decrypted token, ciphertext, credential revision, and URL fingerprint; backend logs and existing telemetry exclude raw/decrypted/encrypted credential values; frontend storage excludes tokens; and frontend status models contain only approved safe metadata
- [ ] T038 [P] Run the frontend suite/build and add keyboard, accessible-name, responsive-layout, and token-absence regressions in `src/test/features/monitoring-configurations/gitlab-connection-accessibility.test.tsx`
- [X] T039 Run Alembic upgrade/downgrade and PostgreSQL credential lifecycle checks against an isolated PostgreSQL database, recording environment-specific results in `specs/003-gitlab-connection/validation.md`
- [X] T040 Document encryption-key generation, separate backup, ordered rotation/re-encryption, 2048 UTF-8 byte token boundary, 5/10/5/5-second configurable timeout defaults, least-privilege `read_user`, validation limits, and manual quickstart verification without changing `.env.example` in `README.md` and `specs/003-gitlab-connection/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies.
- **Phase 2 (Foundational)**: Depends on Phase 1 and blocks all user stories.
- **Phase 3 (US1)**: Depends on Phase 2 and supplies persisted credentials/status used by saved validation.
- **Phase 4 (US2)**: Depends on Phase 2 and the timeout configuration completed in Setup task T002; candidate validation can otherwise be built independently, while saved-credential validation integrates with US1 repository behavior.
- **Phase 5 (US3)**: Depends on US1 credential lifecycle; its no-side-effect tests also cover US2 validation when that story is included.
- **Phase 6 (Polish)**: Depends on all stories selected for delivery.

### User Story Dependency Graph

```text
Setup -> Foundation -> US1 (credential lifecycle) -> US3 (retirement cleanup)
                    \-> US2 (candidate validation)
                     -> US1 -> US2 (saved validation)
```

- **US1 (P1)**: First MVP increment after Foundation; no dependency on another story.
- **US2 (P1)**: Candidate path can proceed after Setup T002 and Foundation; saved path additionally consumes US1's repository/status boundary.
- **US3 (P2)**: Retirement cleanup depends on US1 persistence but is otherwise isolated from validation implementation.

### Within Each User Story

- Write the story's tests first and verify they fail for the intended missing behavior.
- Implement inner-layer types/ports before adapters and use cases before API/UI integration.
- Keep network validation outside a database transaction; conditionally persist its result afterward.
- Finish the independent test before treating a story as complete.

## Parallel Execution Examples

### User Story 1

```text
T011 crypto tests | T012 use-case tests | T013 API tests | T014 PostgreSQL tests | T015 UI tests
T016 cipher/config | T020 frontend types/API (after shared contracts are settled)
```

### User Story 2

```text
T023 adapter tests | T024 use-case tests | T025 API tests | T026 UI tests
T027 HTTP adapter can proceed independently while T028 use-case behavior is developed against the fake port
```

### User Story 3

```text
T031 scope tests | T032 retirement integration tests | T033 UI scope tests
```

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational phases.
2. Complete US1, including encryption, persistence, API, frontend, and its independent test.
3. Stop and validate that a user can securely manage credentials without disclosure or lifecycle side effects.

### Incremental Delivery

1. Deliver US1 as the credential-management MVP.
2. Add US2 candidate validation, then integrate saved validation with US1's versioned credential snapshot.
3. Add US3 retirement cleanup and explicit scope/no-side-effect verification.
4. Complete cross-cutting verification and operational documentation.

### Parallel Team Strategy

After Foundation, separate owners can work on backend tests/adapters and frontend tests/components. Candidate validation can advance alongside US1, but saved-token validation must integrate only after US1's repository contract is stable.

## Notes

- `[P]` means different files and no dependency on another incomplete task in the phase.
- Tokens are opaque and transient; never add them to domain entities, read DTOs, logs, telemetry, URLs, browser storage, fixtures, or committed configuration.
- Ordinary automated tests use fakes and HTTPX MockTransport without live PostgreSQL or GitLab; PostgreSQL migration checks remain a separately reported gate and must never use SQLite as a substitute.
- Do not add discovery, repository selection, scheduling, mining, execution history, findings, analytics, authentication, authorization, KMS, or automated key rotation.
