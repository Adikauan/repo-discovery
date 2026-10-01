# Phase 1 Quickstart: Validate Monitoring Configuration CRUD

## Prerequisites

- Node.js/npm and the existing Feature 001 frontend dependencies.
- Python 3.13 or 3.14 and pip.
- A local PostgreSQL 16+ server and a dedicated development database plus a separate test database.
- No GitLab account, token, GitLab API, scheduler, or mining process is required.

## Configure and start the backend

### Docker Compose (recommended local setup)

Copy `.env.example` to `.env`, then set `POSTGRES_PASSWORD` to a locally generated random
hexadecimal value. `.env` is ignored by Git; never commit it. If host port 5432 is already in use,
set `POSTGRES_PORT=5433` (or another free local port) in `.env`. From the repository root run:

```powershell
docker compose up --build -d
docker compose ps
```

Compose starts PostgreSQL 16 with a persistent named volume, waits for its health check, applies
Alembic migrations, and then starts the API. The API is available at `http://localhost:8000` and
its health endpoint at `http://localhost:8000/health`. Start the frontend separately with
`npm run dev`; its default `http://localhost:5173` origin is allowed by the API. Stop the services
with `docker compose down`; this preserves database data in the named volume.

### Run the backend directly on the host

From PowerShell at the repository root, configure `DATABASE_URL` and CORS origins for the local
frontend. Use local-only credentials and never commit real secrets.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
$env:DATABASE_URL = "postgresql+psycopg://<local-user>:<local-password>@localhost:5432/repo_miner_dev"
$env:CORS_ORIGINS = "http://localhost:5173"
alembic upgrade head
uvicorn app.api.main:app --reload --port 8000
```

Verify the versioned OpenAPI document at `/openapi.json` or the development API docs.
Application startup must fail clearly when required configuration is absent; it must never create
tables automatically.

## Configure and start the frontend

In a second shell at the repository root:

```powershell
$env:VITE_API_BASE_URL = "http://localhost:8000/api/v1"
npm run dev
```

Open the Vite URL and use Monitoring Configurations. CORS must allow this explicit origin and
expose `ETag` and `Location` to the frontend.

## End-to-end workflow

1. Open the Monitoring Configurations listing and verify loading, retryable error, empty, and
   populated states.
2. Create a configuration with a valid name and HTTP or HTTPS GitLab instance URL without sending
   a resource identifier. Verify the backend-generated ID is returned, it is saved disabled, and it
   appears in the listing and details view.
3. Try a blank name, blank URL, relative URL, and unsupported scheme. Verify field-associated
   feedback and no persisted invalid change.
4. Search by a trimmed, case-insensitive substring; verify empty and whitespace-only queries show
   all active configurations and `%`, `_`, `*`, and other relevant special characters are matched
   literally. Clear the search to restore all active configurations.
5. Edit the name/description/URL and verify identifier and creation date remain stable while the
   update date and version change. Submit a stale version and verify a conflict with reload/reapply
   guidance.
6. Explicitly enable, then disable the configuration. Verify status and update date; no mining
   starts.
7. Request deletion and cancel; verify the record remains. Confirm deletion; verify it disappears
   from active list/detail and the underlying record remains retired, without cascade deletion.
8. Optionally retry a create that included an `Idempotency-Key` using the same key and values; verify
   the original outcome and generated ID are returned once. Reuse the key with different values;
   verify conflict. Use a new key with identical values; verify a distinct configuration is created.

## Automated validation

From repository root:

```powershell
cd backend
$env:TEST_DATABASE_URL = "postgresql+psycopg://<local-user>:<local-password>@localhost:5432/repo_miner_test"
alembic upgrade head
pytest
alembic check
```

Then from repository root:

```powershell
npm test -- --run
npm run build
```

Expected outcomes: domain/application tests pass without external services; PostgreSQL integration
tests exercise migration, transaction, idempotency, and concurrency behavior; API tests verify
contracts and error codes; frontend tests cover CRUD states and actions; the Feature 001 route,
responsive, and accessibility tests remain passing; the production build succeeds.

## Migration review

Run Alembic upgrade against a fresh disposable database and a database at the prior revision. Test
the downgrade on a disposable database. Review every generated migration manually; production schema
changes are never made outside reviewed Alembic revisions.

## Latest implementation validation

The latest local validation completed 42 backend unit/API tests and 81 frontend tests; the frontend
production build succeeded (with the existing Vite large-chunk advisory). The six PostgreSQL
integration tests, live migration upgrade/downgrade, and database drift check remain unverified.
Offline Alembic SQL generation succeeded for both upgrade and downgrade directions, but this does
not replace execution against PostgreSQL. The local database could not be started because the
Docker service is inaccessible:
`TEST_DATABASE_URL` is not configured, the local Docker service is stopped, and localhost:5432 is
not accepting connections. Re-run the PostgreSQL commands above against a dedicated disposable
test database before treating persistence/migration validation as complete.

## Scope guard

Inspect browser network requests and backend routes. Only configuration CRUD requests are present.
There must be no GitLab calls, credentials, browser storage, schedule operations, mining/execution
processing, findings, dashboards, authentication, or authorization behavior. Newly created records
must be disabled until a separate user action enables them.
