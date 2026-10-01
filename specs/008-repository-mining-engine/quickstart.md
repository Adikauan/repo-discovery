# Quickstart: Repository Mining Engine Validation

This guide validates Feature 008 against controlled GitLab responses and PostgreSQL where available. It does not require a live GitLab token for the normal suite. Contract and model details are in [repository-execution-api.md](contracts/repository-execution-api.md), [repository-dashboard.md](contracts/repository-dashboard.md), and [data-model.md](data-model.md).

## Prerequisites

- Python 3.13 or 3.14 and the backend development dependencies installed from `backend/pyproject.toml`.
- Node.js and dependencies installed from the project `package.json`.
- PostgreSQL and `TEST_DATABASE_URL` only for the database integration checks.
- Test provider calls use HTTPX mock transports; never place a real credential in fixtures.

## Backend checks

From `backend/`:

```powershell
python -m pytest tests/unit
python -m pytest tests/api
python -m pytest tests/integration
```

The unit/API suites verify snapshot-only scope, instance mismatch before provider calls, credentials redaction, selected-group resolution, deterministic deduplication, all rule/filter boundaries, repository failure isolation, empty scope, partial scope failures, counter reconciliation, and normalized API projections. Integration tests exercise the `0006_repository_executions` migration, uniqueness, historical retention, and independent worker transactions against PostgreSQL when configured. If PostgreSQL is unavailable, report those checks as blocked; do not substitute SQLite for PostgreSQL-specific claims.

Migration commands from `backend/`:

```powershell
alembic upgrade head
alembic current
```

Verify the migration head is `0006_repository_executions` and that the repository unique constraint and safe status/error constraints exist.

## Frontend checks

From the repository root:

```powershell
npm run test:run -- src/test/features/executions
npm run build
```

Dashboard tests cover list loading, empty states for completed empty scope and active/pre-processing failure, normalized API failure/retry, completed/failed/mixed repository rows, safe error rendering, zero finding counts, long-path wrapping, and accessibility semantics. Run the existing accessibility test convention with the executions suite; no new testing framework is introduced.

## Acceptance walkthrough

1. Create a manual execution using a snapshot containing selected repositories and/or groups in a mocked GitLab instance.
2. Verify the selected snapshot instance is validated before group/project requests and the live Monitoring Configuration scope is not queried.
3. Exercise overlapping group/direct scope; verify one row per unique project and deterministic list order.
4. Exercise zero selected entries and a valid empty group: successful completed status, all four execution counters zero, no repository rows.
5. Exercise an inaccessible selected scope entry alongside a valid repository: valid repository processes, scope failure is visible, final status is partial when the repository succeeds, `failed_repository_count` still equals failed repository rows.
6. Exercise a project with no default branch: safe failed row, no guessed branch, and remaining repositories continue.
7. Exercise a tree with more than one API page and a tree at the configured maximum; verify pagination exhausts correctly and an over-limit tree fails safely instead of returning a partial success.
8. Open `/executions/:id` > Repositories and verify all values come from persisted DTOs; Findings remains unavailable.
9. Run the PostgreSQL integration subset with `TEST_DATABASE_URL`; record environmental inability as blocked rather than claiming it passed.
