# Feature 003 Validation Record

## Automated validation

- Backend unit, API, and integration suite: **67 passed** against an isolated PostgreSQL database on 2026-09-28.
- Provider behavior uses HTTPX `MockTransport`.
- Frontend TypeScript project compilation: **passed** (`node node_modules/typescript/bin/tsc -b --force --pretty false`).
- Frontend production build: **passed** (`npm run build`); Vite emitted only its existing large-chunk advisory.
- Frontend Vitest execution is environment-blocked: Vitest 5.0.2 times out waiting for its worker to respond before collecting any tests. The same failure reproduces with an existing non-Feature-003 test, in an ASCII-only temporary copy, with thread/VM-thread pools, and with isolated Node 22 as well as the installed Node 26 runtime. Feature tests therefore remain implemented and type-checked but not runtime-verified in this host environment.
- PostgreSQL migration, CAS, and retirement tests require `TEST_DATABASE_URL`; when absent they are reported as skipped and SQLite is not substituted.

## PostgreSQL gate

Run from `backend/` against an isolated database:

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://..."
.venv\Scripts\python.exe -m pytest tests/integration/test_migrations.py tests/integration/test_gitlab_credential_persistence.py tests/integration/test_configuration_retirement.py
```

The isolated PostgreSQL gate passed, including Alembic upgrade/downgrade, credential lifecycle, compare-and-swap concurrency, and atomic retirement coverage.
