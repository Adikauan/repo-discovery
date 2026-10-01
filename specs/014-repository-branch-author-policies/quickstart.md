# Feature 014 Validation Quickstart

This guide describes the validation flow after implementation. It uses mocked GitLab responses for normal tests and PostgreSQL for persistence/migration/concurrency validation.

## Prerequisites

- Python environment with backend dev dependencies installed.
- Node dependencies installed at repository root.
- PostgreSQL test database available through `TEST_DATABASE_URL` for migration, uniqueness, and optimistic concurrency tests.
- No live GitLab token is required for standard automated tests; GitLab provider behavior is mocked.

## Backend unit, application, API, and mocked GitLab tests

```powershell
Set-Location backend
python -m pytest
```

Expected: domain normalization/resolution, policy use cases, branch adapter pagination/error mapping, API ownership checks, execution snapshot compatibility, pipeline regression, and mocked provider tests pass.

## PostgreSQL migration and integration tests

Set `TEST_DATABASE_URL` to a disposable PostgreSQL database using the project's test configuration, then run:

```powershell
Set-Location backend
alembic upgrade head
python -m pytest tests/integration
```

Expected: the 0009 migration preserves existing legacy lists/executions/findings/checkpoints; policy partial-unique constraints and optimistic conflict handling are exercised against PostgreSQL. If PostgreSQL is unavailable, report these checks as pending; SQLite is not a substitute.

## Frontend and accessibility tests

From repository root:

```powershell
npm run test:run
```

Expected: Authors wizard tests cover selected-scope rendering, policy chips, branch discovery states, group branch N/A, scope-inactive policies, legacy migration confirmation, stale-write feedback, and keyboard/axe accessibility.

## Production build

```powershell
npm run build
```

Expected: TypeScript compilation and Vite production bundling complete successfully.

## End-to-end scenarios to demonstrate

1. Configure two different branch author lists for one selected repository; verify reopening restores each independently.
2. Configure a Group policy and verify it remains attached to the selected Group ID while a nested repository appears/disappears dynamically.
3. Confirm repository/branch policy precedence, missing-policy behavior, empty-policy behavior, legacy fallback, and scope migration follow [spec.md](spec.md) and the final resolved group-overlap semantics.
4. Remove a scope item and confirm its policy becomes inactive, remains stored, and never applies to another identity.
5. Delete/invalidate a saved branch; confirm it is shown unavailable. If the unavailable branch is not processed by existing mining semantics, execution is unaffected; if it is the branch selected for processing, confirm the RepositoryExecution fails safely and its checkpoint does not advance.
6. Run equivalent manual and scheduled executions; confirm the same pipeline uses captured policy context and existing Unauthorized Commit Author Findings retain repository, commit, author, and historical branch context.
7. Change a policy after an execution; confirm the prior snapshot/Finding remains unchanged and the checkpoint is not reset.

## Contract references

- [Author Policies API](contracts/author-policies-api.md)
- [Execution Policy Snapshot](contracts/execution-policy-snapshot.md)
- [Data model](data-model.md)

## Validation run (2026-09-30)

- Backend unit and API suite: **343 passed** (`SCHEDULER_ENABLED=false` for test-runner lifecycle isolation).
- Backend Feature 014 focused domain, snapshot, execution creation, repository pipeline, API, Finding projection, and mocked GitLab tests: **101 passed**.
- PostgreSQL integration suite: **35 passed** using `TEST_DATABASE_URL` loaded from the workspace `.env`; SQLite was not used. This includes Feature 014 policy persistence/history, upgrade/downgrade through Alembic, stale-write concurrency, Finding/checkpoint transaction rollback, and uniqueness checks.
- Alembic PostgreSQL offline SQL generation (`alembic upgrade head --sql`): **passed**, including revision `0009_author_policies`.
- Frontend full suite using Vitest native config loader and thread pool: **47 files / 198 tests passed**.
- Frontend production build (`npm run build`): **passed**; Vite emitted its existing large-chunk advisory.
- The backend unit/API suite requires `SCHEDULER_ENABLED=false` in this environment; with it set, the complete suite exited successfully.
- Manual comparison against the approved screenshots was not performed. The Windows computer-use runtime failed to initialize because its kernel asset path was unavailable; retain that task for browser-based review.
