---
description: "Dependency-ordered implementation tasks for Monitoring Configuration CRUD"
---

# Tasks: Feature 002 - Monitoring Configuration CRUD

**Input**: Design documents from `specs/002-monitoring-configuration-crud/`

**Prerequisites**: `plan.md`, `spec.md`; design details in `research.md`, `data-model.md`, and `contracts/api-v1.md`.

**Tests**: Included because the specification and constitution explicitly require domain, application, persistence, API, and critical frontend tests.

**Organization**: Tasks are grouped by the three prioritized user stories in `spec.md`. All tasks use repository-root-relative paths.

## Phase 1: Setup

**Purpose**: Establish the backend package and frontend integration conventions without changing Feature 001's shell.

- [X] T001 Create the Python package, development/test dependency groups, and pytest configuration in `backend/pyproject.toml`.
- [X] T002 Create backend package entry points for `backend/app/__init__.py`, `backend/app/domain/__init__.py`, `backend/app/application/__init__.py`, `backend/app/infrastructure/__init__.py`, and `backend/app/api/__init__.py`.
- [X] T003 [P] Create the backend testing directory structure and shared pytest fixtures in `backend/tests/conftest.py`, `backend/tests/unit/domain/`, `backend/tests/unit/application/`, `backend/tests/integration/`, and `backend/tests/api/`.
- [X] T004 [P] Add the Vite API base URL example and environment typing in `.env.example` and `src/vite-env.d.ts`; document that no secrets or credentials belong in these files.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Provide database, migration, session, API, and safe-error infrastructure required by all stories.

**⚠️ CRITICAL**: Complete this phase before implementing user-story behavior.

- [X] T005 Configure typed application settings for database URL and explicit CORS origins in `backend/app/config.py`, loading values from environment and failing safely when required settings are missing.
- [X] T006 Implement request-scoped synchronous SQLAlchemy 2 session and declarative metadata boundary in `backend/app/infrastructure/database/session.py` and `backend/app/infrastructure/database/base.py`.
- [X] T007 Configure Alembic to load application metadata and the database URL from settings in `backend/alembic.ini`, `backend/alembic/env.py`, and `backend/alembic/script.py.mako`; prohibit application-startup schema creation.
- [X] T008 Implement FastAPI application construction, `/api/v1` router mounting, explicit-origin CORS, and safe generic error handling in `backend/app/api/main.py`, `backend/app/api/errors.py`, and `backend/app/api/dependencies.py`.
- [X] T009 Define the shared frontend API transport and Problem Details parsing without feature business rules in `src/shared/utils/apiClient.ts` and `src/shared/types/problemDetails.ts`.

**Checkpoint**: Backend starts from environment configuration, Alembic is ready for reviewed migrations, and frontend requests can use a configured API base URL with safe error parsing.

---

## Phase 3: User Story 1 - Create and Find a Monitoring Configuration (Priority: P1) 🎯 MVP

**Goal**: Create disabled-by-default configurations, persist them, and list/search/open them through the existing application shell.

**Independent Test**: With a migrated database, create a valid configuration through the UI/API without supplying a resource ID; verify the response contains the backend-generated ID, normalized fields, timestamps, `enabled=false`, and appearance in list/search/details; verify invalid input creates no record and, when an optional idempotency key is used, a same-key retry does not duplicate it.

### Tests for User Story 1

- [X] T010 [P] [US1] Add domain tests for name trimming/non-empty validation, optional-description normalization, absolute HTTP(S) URL validation, and factory-enforced `enabled=false` in `backend/tests/unit/domain/test_monitoring_configuration.py`.
- [X] T011 [P] [US1] Add application tests for create/list/search/get and optional idempotency-key replay, same-key/different-payload conflict, distinct-key intents, and normal create without a key; search tests must cover normal substring, case-insensitive matching, trimmed query, empty query, whitespace-only query, literal `%`, literal `_`, literal `*`, and relevant special characters in `backend/tests/unit/application/test_create_and_find_configuration.py`.
- [X] T012 [P] [US1] Add PostgreSQL repository and migration tests for backend-generated UUID/timestamp persistence, active listing/search, and atomic create-receipt behavior when an optional key is supplied; verify SQL `LIKE`/`ILIKE` escaping for literal `%`, `_`, `*`, backslash, and relevant bracket characters in `backend/tests/integration/test_configuration_persistence.py` and `backend/tests/integration/test_migrations.py`.
- [X] T013 [P] [US1] Add API contract tests for POST without an idempotency key, generated response `id`, rejection of a client-provided create `id`, optional-key format validation, keyed replay/conflict, GET collection/item, normalized field validation, response schemas, and safe errors in `backend/tests/api/test_configuration_create_and_read.py`.
- [X] T014 [P] [US1] Add frontend behavior tests for listing loading/empty/error/populated states and search by normal substring, case-insensitive match, trimmed query, empty query, whitespace-only query, literal `%`, literal `_`, `*`, and other relevant special characters; include an independent complete create-to-details flow that submits valid name, description, and GitLab URL values, verifies successful creation and navigation to that created configuration, then asserts the details page shows matching name, description, GitLab URL, disabled status, and creation/last-update dates when available in the UI. Reuse shared test helpers or fixtures where useful; write the test in `src/test/features/monitoring-configurations/create-and-list.test.tsx`.

### Implementation for User Story 1

- [X] T015 [US1] Implement the framework-independent configuration entity and validation/normalization rules in `backend/app/domain/monitoring_configuration.py` and domain errors in `backend/app/domain/errors.py`; preserve these constraints verbatim: `name` is required, trimmed, and rejected when empty; `description` is optional and missing/blank normalizes to absent; `gitlab_url` is required, trimmed, absolute HTTP or HTTPS with a host; `enabled` is always false on creation; `created_at` and `updated_at` are UTC-aware; `id` is stable, backend-generated, and immutable.
- [X] T016 [US1] Define repository and create-request-receipt ports for create, list/search, get, and atomic idempotency operations in `backend/app/application/ports/monitoring_configuration_repository.py` and `backend/app/application/ports/create_request_store.py`.
- [X] T017 [US1] Add SQLAlchemy mappings for configuration and immutable create receipt records in `backend/app/infrastructure/database/models.py`, including `enabled NOT NULL DEFAULT FALSE`, positive internal revision, nullable retirement time, UUID identity, unique request key, normalized request fingerprint, and response snapshot.
- [X] T018 [US1] Implement SQLAlchemy persistence for backend-generated configuration IDs in `backend/app/infrastructure/database/sqlalchemy_repositories.py`; create a request receipt atomically only when an optional idempotency key is supplied, and ensure ordinary reads exclude retired records.
- [X] T019 [US1] Create and review `backend/alembic/versions/0001_create_monitoring_configurations.py` for `monitoring_configurations` and `create_request_receipts`; include reversible upgrade/downgrade operations and no cascade deletion.
- [X] T020 [US1] Implement create, list/search, and retrieve application use cases in `backend/app/application/use_cases/create_monitoring_configuration.py`, `backend/app/application/use_cases/list_monitoring_configurations.py`, and `backend/app/application/use_cases/get_monitoring_configuration.py`; generate the configuration ID in the backend; when a key is supplied, the same key and normalized payload replay the original result while a different payload conflicts.
- [X] T021 [US1] Define explicit create/list/item Pydantic contracts and POST/GET collection/GET item routes in `backend/app/api/v1/schemas.py` and `backend/app/api/v1/monitoring_configurations.py`; create accepts only `name`, optional `description`, and `gitlab_url`, rejects a client-provided `id`, accepts an optional valid `Idempotency-Key`, and returns the generated backend `id` with `enabled=false` on success.
- [X] T022 [US1] Implement the feature API adapter and TypeScript request/response types in `src/features/monitoring-configurations/api/monitoringConfigurationsApi.ts` and `src/features/monitoring-configurations/model/monitoringConfiguration.ts`; never ask for or send a Monitoring Configuration ID during create, and keep any optional retry idempotency key in transient request state only.
- [X] T023 [US1] Implement the API-backed listing page with trimmed, case-insensitive literal substring search; empty and whitespace-only queries apply no filter, wildcard-like characters remain literal, and loading/error/empty states are retryable where appropriate; add table fields and create/details destinations in `src/features/monitoring-configurations/pages/MonitoringConfigurationsPage.tsx` and feature-local listing components under `src/features/monitoring-configurations/components/`.
- [X] T024 [US1] Implement the single-step general-information create form with name, optional description, GitLab URL, field feedback, and no enabled-status control in `src/features/monitoring-configurations/components/MonitoringConfigurationForm.tsx` and `src/features/monitoring-configurations/pages/NewMonitoringConfigurationPage.tsx`.
- [X] T025 [US1] Implement persisted configuration details and success/unavailable states in `src/features/monitoring-configurations/pages/MonitoringConfigurationDetailsPage.tsx`.
- [X] T026 [US1] Wire listing, creation, and item-detail pages to the existing centralized router and established Feature 001 shell in `src/app/routes/routeConfig.tsx`; do not redesign the shell or enable unfinished future wizard steps.

**Checkpoint**: User Story 1 can create, find, and open a persisted disabled configuration independently.

---

## Phase 4: User Story 2 - Review and Update a Monitoring Configuration (Priority: P2)

**Goal**: Edit configuration identity fields and explicitly enable/disable an active configuration without losing newer changes or starting mining.

**Independent Test**: Seed or create an active configuration, view all defined fields, edit each supported field, and verify id/created date remain stable; verify actual changes update timestamp/version, no-op updates do not, stale edits conflict, and enable/disable only changes availability.

### Tests for User Story 2

- [X] T027 [P] [US2] Add domain/application tests for atomic edits, immutable id/created date, update timestamp and revision no-op semantics, enabled transitions, and stale revision conflicts in `backend/tests/unit/domain/test_configuration_updates.py` and `backend/tests/unit/application/test_update_configuration.py`.
- [X] T028 [P] [US2] Add PostgreSQL concurrency tests proving a stale update cannot overwrite a newer saved version in `backend/tests/integration/test_configuration_concurrency.py`.
- [X] T029 [P] [US2] Add API tests for PUT validation, required `If-Match`, ETag/version advancement, 412 stale conflicts, 404 unavailable resources, and safe no-op status changes in `backend/tests/api/test_configuration_update.py`.
- [X] T030 [P] [US2] Add frontend behavior tests for details fields, edit validation/success/conflict recovery, and enable/disable feedback in `src/test/features/monitoring-configurations/update-and-lifecycle.test.tsx`.

### Implementation for User Story 2

- [X] T031 [US2] Implement atomic domain update and explicit post-creation enable/disable operations in `backend/app/domain/monitoring_configuration.py`; preserve the specification's field validation rules and do not start mining on status changes.
- [X] T032 [US2] Implement update application orchestration with optimistic concurrency and no-op timestamp/version preservation in `backend/app/application/use_cases/update_monitoring_configuration.py` and update the repository port in `backend/app/application/ports/monitoring_configuration_repository.py`.
- [X] T033 [US2] Add SQLAlchemy version checking and conditional update persistence in `backend/app/infrastructure/database/sqlalchemy_repositories.py`; map stale writes to the application conflict result without committing partial changes.
- [X] T034 [US2] Define the full replacement update schema and PUT route with ETag/If-Match handling and documented 200/404/412/422/428 outcomes in `backend/app/api/v1/schemas.py` and `backend/app/api/v1/monitoring_configurations.py`.
- [X] T035 [US2] Add feature API update support, including transient ETag retention and If-Match requests, in `src/features/monitoring-configurations/api/monitoringConfigurationsApi.ts`.
- [X] T036 [US2] Implement the edit page and reusable form mode, preserving current user edits on stale conflict and presenting reload/reapply guidance, in `src/features/monitoring-configurations/pages/EditMonitoringConfigurationPage.tsx` and `src/features/monitoring-configurations/components/MonitoringConfigurationForm.tsx`.
- [X] T037 [US2] Add explicit enable/disable controls and action feedback to configuration details in `src/features/monitoring-configurations/pages/MonitoringConfigurationDetailsPage.tsx`.
- [X] T038 [US2] Add `/monitoring-configurations/:id/edit` to centralized route configuration in `src/app/routes/routeConfig.tsx` and ensure breadcrumbs remain within Feature 001 navigation patterns.

**Checkpoint**: User Story 2 supports conflict-safe editing and explicit availability changes without mining side effects.

---

## Phase 5: User Story 3 - Delete a Monitoring Configuration Safely (Priority: P3)

**Goal**: Require confirmation and retire a configuration from active management while preserving its retained identity and values.

**Independent Test**: Seed an active configuration, request deletion and cancel to ensure it remains; confirm deletion and ensure it leaves active listing/detail/edit while its retained row remains; verify errors do not remove it or affect unrelated data.

### Tests for User Story 3

- [X] T039 [P] [US3] Add application and PostgreSQL tests for logical retirement, retained identity/values, repeated/unknown deletion outcomes, and no cascade effects in `backend/tests/unit/application/test_retire_configuration.py` and `backend/tests/integration/test_configuration_retirement.py`.
- [X] T040 [P] [US3] Add API tests for confirmed DELETE behavior, 204 success, unknown/already-retired 404 behavior, and no response body in `backend/tests/api/test_configuration_delete.py`.
- [X] T041 [P] [US3] Add frontend behavior tests for confirmation identity, cancel, success, delete failure, and unavailable detail handling in `src/test/features/monitoring-configurations/delete-configuration.test.tsx`.

### Implementation for User Story 3

- [X] T042 [US3] Implement the retirement application use case and active-record not-found semantics in `backend/app/application/use_cases/retire_monitoring_configuration.py` and update `backend/app/application/ports/monitoring_configuration_repository.py`.
- [X] T043 [US3] Implement soft retirement persistence with retained configuration values and no cascade behavior in `backend/app/infrastructure/database/sqlalchemy_repositories.py`.
- [X] T044 [US3] Add DELETE route returning 204 only for an active configuration and safe 404 Problem Details otherwise in `backend/app/api/v1/monitoring_configurations.py`.
- [X] T045 [US3] Add delete API client operation in `src/features/monitoring-configurations/api/monitoringConfigurationsApi.ts`.
- [X] T046 [US3] Implement the reusable explicit confirmation dialog and delete failure/success feedback in `src/features/monitoring-configurations/components/DeleteConfigurationDialog.tsx` and wire it to `src/features/monitoring-configurations/pages/MonitoringConfigurationDetailsPage.tsx`.
- [X] T047 [US3] Ensure successful retirement returns users to the active listing and retired records are consistently unavailable in `src/features/monitoring-configurations/pages/MonitoringConfigurationsPage.tsx` and `src/features/monitoring-configurations/pages/MonitoringConfigurationDetailsPage.tsx`.

**Checkpoint**: User Story 3 removes a configuration from active management only after confirmation and preserves retained history context.

---

## Phase 6: Polish and Cross-Cutting Validation

**Purpose**: Validate the complete feature against its contract, architecture, scope, and run guide.

- [X] T048 [P] Review backend boundaries and remove framework/database imports from domain modules in `backend/app/domain/`; verify use cases own rules and transaction orchestration rather than API handlers.
- [X] T049 [P] Review frontend presentation reuse, accessible labels/focus, responsive behavior, and all loading/empty/error/disabled/success states in `src/features/monitoring-configurations/` without changing the Feature 001 shell design.
- [X] T050 Run the complete backend test suite, Alembic upgrade/downgrade and drift checks, and fix implementation-related failures in `backend/tests/` and `backend/alembic/versions/`.
  - Run note: PostgreSQL integration tests and live Alembic drift checks are authored but could not run here because PostgreSQL and the Docker daemon are unavailable; offline Alembic upgrade/downgrade SQL generation succeeded.
- [X] T051 Run the complete frontend test suite and production build; fix regressions in `src/test/`, `src/features/monitoring-configurations/`, and `src/app/routes/routeConfig.tsx`.
- [X] T052 Execute and update the end-to-end setup/CRUD/idempotency/concurrency/retirement instructions in `specs/002-monitoring-configuration-crud/quickstart.md`.
- [X] T053 Review delivered routes, contracts, and UI against `specs/002-monitoring-configuration-crud/spec.md`; document any non-blocking issue and remove any out-of-scope GitLab, scheduling, mining, execution-history processing, analytics, authentication, or authorization behavior.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; establishes package and environment conventions.
- **Foundational (Phase 2)**: Depends on Setup; blocks all user-story implementation.
- **US1 (Phase 3)**: Depends on Phase 2; provides persisted create/list/details foundation and create idempotency.
- **US2 (Phase 4)**: Depends on the configuration domain, repository, API, and frontend details established by US1; adds editing and status changes.
- **US3 (Phase 5)**: Depends on the active configuration lookup and details/list pages from US1 and the API/repository contracts from prior phases; adds retirement.
- **Polish (Phase 6)**: Depends on all three stories selected for delivery.

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2 and is the MVP; it is independently verifiable using an empty database and the create/list/details flow.
- **US2 (P2)**: Builds on US1's persisted entity and details page; cannot be independently delivered before the shared configuration resource exists.
- **US3 (P3)**: Builds on US1's active listing/details and persistence; logically retires the shared resource and can be independently tested with a seeded configuration.

### Parallel Opportunities

- T003 and T004 can run alongside each other after initial repository setup.
- In US1, T010–T014 are separate test files and can be authored in parallel; T022–T026 can be split across frontend files after API contract shapes are agreed.
- In US2, T027–T030 are separable test files; backend update work (T031–T034) and frontend update work (T035–T038) can proceed in parallel once US1 contracts stabilize.
- In US3, T039–T041 can proceed in parallel; backend retirement (T042–T044) and frontend confirmation (T045–T047) can proceed in parallel once the delete contract is agreed.
- Phases are intentionally sequential because US2/US3 extend the US1 configuration resource; separate contributors may parallelize backend/frontend tasks within a phase.

### Dependency Graph

```text
Setup T001-T004
  -> Foundation T005-T009
      -> US1 T010-T026
          -> US2 T027-T038
          -> US3 T039-T047
              -> Polish T048-T053
```

## Parallel Example: User Story 1

```text
Task: T010 Domain tests in backend/tests/unit/domain/test_monitoring_configuration.py
Task: T013 API contract tests in backend/tests/api/test_configuration_create_and_read.py
Task: T014 Frontend behavior tests in src/test/features/monitoring-configurations/create-and-list.test.tsx
```

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Setup and Foundational phases.
2. Complete US1 to deliver disabled-by-default create, persisted listing/search, details, validation, and idempotent create.
3. Validate US1 independently using its tests and database migration.
4. Continue with US2 and US3 in priority order; neither adds future GitLab or mining behavior.

### Incremental Delivery

1. Setup + Foundation establish a deployable API/database and frontend integration path.
2. US1 delivers create/find/open as the MVP.
3. US2 adds review/edit and explicit enable/disable.
4. US3 adds confirmed logical retirement.
5. Polish validates the complete Feature 002 scope and Feature 001 regression suite.

## Notes

- Implementation tasks use sequential IDs, completion checkboxes, and repository-relative file paths.
- `[P]` is used only for tasks in independent files with no incomplete prerequisite; `[US1]`, `[US2]`, and `[US3]` identify story-owned tasks.
- New configurations must always persist with `enabled=false`; no create request or form may override that default.
- No task adds GitLab integration, credentials, repository selection, scheduling, mining, executions, findings, analytics, authentication, or authorization.

## Phase 7: Convergence

- [X] T054 Reject GitLab instance URLs containing username/password user-info and verify those sensitive values are never persisted or returned through the API, per Constitution V and FR-008 (contradicts).
- [X] T055 Map Problem Details field errors to the corresponding create/edit form controls instead of showing backend field-validation failures only in a form-level alert; add behavior tests, per FR-010, FR-019, and the plan's Frontend Integration Strategy (partial).
- [X] T056 Add accessible listing-row enable/disable and confirmed-delete actions with outcome feedback, reusing the existing API and confirmation UI; cover success/failure behavior, per the plan's Frontend Integration Strategy (partial).
- [X] T057 Abort superseded Monitoring Configuration list/search requests and verify that aborts do not surface as user-facing errors, per the plan's Frontend Integration Strategy (partial).
- [ ] T058 Run the PostgreSQL persistence, literal-search, idempotency, concurrency, retirement, Alembic upgrade/downgrade, and drift checks against a dedicated PostgreSQL database; record results and update the validation note, per the plan's Validation Strategy and Constitution IX/X (partial; live checks blocked because the Docker service is inaccessible and localhost:5432 is unavailable; offline upgrade/downgrade SQL generation succeeded).
