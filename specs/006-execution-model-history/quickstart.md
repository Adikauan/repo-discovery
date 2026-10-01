# Feature 006 Validation Quickstart

This is a validation guide for the implementation produced from the plan and tasks. PostgreSQL is required for migration and concurrency validation; SQLite is not a substitute.

## Preconditions

- Start a dedicated PostgreSQL test database and set `TEST_DATABASE_URL` in the backend environment. The existing integration fixture upgrades Alembic to head and tears it back down; do not point it at a database containing user data.
- Install backend development dependencies according to `backend/pyproject.toml` and frontend dependencies according to the repository `package.json`.
- Apply the Feature 006 Alembic migration to the intended local development database before starting the API.

## Backend unit and API verification

From `backend/` in PowerShell:

```powershell
python -m pytest tests/unit tests/api -q
```

Expected coverage includes lifecycle and timestamp invariants, the internal `pending → running → completed` sequence, fixed-clock manual orchestration, disabled configuration eligibility, retired configuration rejection, controlled failure finalization, and request-time stale reconciliation: fresh active conflict; stale pending and running reconciliation; safe `execution_interrupted`; preserved snapshot/counters; replacement creation; and invalid staleness settings rejected. PostgreSQL concurrency tests verify competing requests do not reconcile/create duplicate active executions. Also verify zero counters/no fabricated mining records, secret-safe snapshots and DTOs, filters, stable ordering, pagination, error normalization, idempotency replay, and API loading/error outcomes.

## PostgreSQL persistence and concurrency verification

From `backend/` in PowerShell, with `TEST_DATABASE_URL` configured to a dedicated PostgreSQL test database:

```powershell
python -m pytest tests/integration -q
```

Expected outcomes include migration application, execution create/list/detail, immutable history after configuration/scope changes and retirement, same-key replay, active partial-unique-index behavior, synchronized concurrent manual requests in which exactly one request proceeds while the first execution is committed as active, and failed-execution release permitting a subsequent request. If PostgreSQL is unavailable, report this suite as not executed; do not claim its concurrency guarantee was runtime-tested.

## Frontend journeys and accessibility

From the repository root:

```powershell
npm test -- --run
npm run build
```

Expected user journeys cover global execution history, configuration-specific history, manual request success and active conflict, opening detail, snapshot/counter rendering, empty/loading/error states, keyboard-accessible navigation/actions, and status text. Completed details must clearly communicate that Feature 006 orchestration completed without repository mining; failed details show only normalized safe error information.

## End-to-end smoke scenario

1. Create a Monitoring Configuration with a recognizable name, GitLab URL, selected scope, and `enabled=false`; no GitLab credential is needed by execution creation.
2. Request a manual execution from its details page.
3. Verify creation feedback and open the created execution.
4. Confirm the status is completed, trigger is manual, timestamps are ordered, scope/configuration values reflect their creation-time snapshot, and all four counters are zero.
5. Confirm the page states that repository mining did not occur and shows no fabricated repository/finding data.
6. Edit the configuration name, GitLab URL, or scope and reload the execution. Its historical snapshot must remain unchanged.
7. With a test-controlled non-stale active execution, submit a second request and verify a safe conflict without a second active row. After the first execution completes, a distinct new request may create a new execution.
8. Repeat a successful request with the same `Idempotency-Key`; verify the same execution is returned and no duplicate history entry is added.
9. In a controlled application test, inject an orchestration failure after creation; verify the HTTP 201 resource is `failed` with `completedAt`, safe error fields, zero counters, no mining records, and that another manual request is subsequently accepted.
10. With a fixed reference time, submit a new manual request while an active execution is older than the configured five-minute default; verify the old execution is finalized as `failed` with `execution_interrupted` and the new request proceeds. Repeat with an active execution below threshold and verify a safe conflict. In PostgreSQL, race two requests against one stale record and verify only one replacement is active.

For the exact persisted fields, public projections, lifecycle rules, and endpoint formats see [data-model.md](data-model.md) and [contracts/api-v1.md](contracts/api-v1.md).

## Validation record (2026-09-29)

- Backend unit and API suite: 171 passed.
- Frontend suite: 124 passed across 36 files, including Feature 006 journey and accessibility checks. The focused Feature 006 suite passed 18 tests across 4 files. The runner used `--pool=vmThreads --maxWorkers=1 --no-file-parallelism` to keep the Windows worker count bounded.
- Frontend production build: passed. Vite reported a non-blocking large-chunk warning.
- Backend startup: `create_app()` and `/health` passed. A live Uvicorn instance also started against the dedicated PostgreSQL test database and served the Feature 006 smoke scenario on localhost:8001.
- Migration validation: `0005_mining_executions` is the Alembic head. Real PostgreSQL upgrade and downgrade passed, including checks for the execution table and active partial unique index.
- PostgreSQL integration and concurrency suite: **23 passed** against the dedicated `repo_miner_f006_validation_20260929` database on localhost:5433. No SQLite substitute was used. The local root `.env` now has a working `TEST_DATABASE_URL` for this database; load that entry into the test process before invoking pytest from `backend/`.
- Convergence task T037: the snapshot-retention test passed against PostgreSQL. It verified the 64-character instance fingerprint, an actual credential replacement after execution creation, unchanged historical snapshot after configuration/scope/schedule changes and retirement, and restricted physical deletion.
- Live end-to-end smoke scenario: passed over real HTTP against the PostgreSQL-backed API. A disabled configuration with persisted group/repository intent and a credential created a completed manual execution with zero counters; same-key replay returned the same record, a distinct request produced a second completed record, global/scoped history was ordered and readable, and the first snapshot stayed unchanged after configuration, scope, and credential changes and retirement. Responses omitted ciphertext, fingerprints, credential revision, and snapshot schema version. Controlled-failure and stale/concurrent reconciliation paths passed in the backend API and PostgreSQL integration suites.
