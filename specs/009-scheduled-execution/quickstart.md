# Feature 009 Quickstart Validation

This guide describes deterministic acceptance checks for scheduled execution. It does not require a live GitLab instance; Feature 008 provider interactions should be mocked in the standard suite.

## Prerequisites

- PostgreSQL test database configured through the existing `TEST_DATABASE_URL`.
- Backend test environment and dependencies installed using existing project instructions.
- Apply Alembic migrations to a disposable test database.
- Use injected/frozen UTC clock and mocked `ProcessMiningExecution`; never wait for wall-clock recurrence in tests.

## Validate recurrence semantics

Run the Feature 005 schedule calculator tests for daily, weekly, monthly, monthly day clamping, DST gap-forward, overlap-earlier-instant, and timezone handling. Feature 009 tests should demonstrate that due detection delegates to that calculator rather than asserting a competing implementation.

Expected: occurrence instants and local recurrence semantics match Feature 005 exactly.

## Validate dispatch and pipeline reuse

Create an enabled configuration and an enabled persisted schedule. Advance the fake scheduler clock across its next occurrence and capture the call into shared execution creation.

Expected:

- Exactly one MiningExecution is created with `trigger_type=scheduled`.
- Snapshot retains configuration/scope and schedule occurrence/version.
- The same Feature 008 mining pipeline is invoked once.
- Success, partial success, or failure is reflected by ordinary MiningExecution status and repository rows.

## Validate eligibility and mutation

Run deterministic cases for disabled configuration, disabled schedule, schedule update/version race, and schedule removal. Persist changes between candidate calculation and dispatch, including an edit whose recurrence time already passed before `updated_at`.

Expected: dispatch re-reads state; disabled/removed/stale-version candidates do not create executions; an edited schedule runs only future occurrences after its update time; history already created remains unchanged.

## Validate restart and offline policy

Run scheduler once with a fake startup baseline, stop it, then initialize a fresh runner with a later instant. Include one passed occurrence and one future occurrence.

Expected: prior missed occurrence has no MiningExecution; current future schedule is restored for its next due time. A pre-existing active scheduled MiningExecution does not invoke its pipeline again.

## Validate conflicts and idempotency with PostgreSQL

Apply the migration, then race manual creation and scheduled dispatch for the same configuration and send duplicate calls for the same occurrence from concurrent transactions.

Expected:

- At most one active MiningExecution exists.
- Only the active-execution winner starts mining.
- Manual loser gets the existing normalized conflict; scheduled loser is skipped.
- Unique occurrence index leaves at most one MiningExecution for the scheduled instant even after the winner finishes.

Also occupy every configured scheduled worker slot and advance another configuration to its due occurrence.

Expected: scheduler scans remain responsive, the saturated occurrence is skipped without a MiningExecution, and no delayed queue dispatch occurs after a worker frees.

Do not report this database validation as passed unless PostgreSQL is available and the test actually runs.

## Existing user-visible paths

Use current global execution history, configuration execution history, `/executions/:id`, and repository results to inspect a scheduled execution.

Expected: it behaves like an ordinary Feature 006/008 execution with trigger shown as scheduled; no new page or scheduler-specific result model appears.

## Implementation validation status (2026-09-30)

- Feature 009 targeted backend validation: 51 passed; all backend unit tests: 193 passed. Five PostgreSQL integration cases were skipped because `TEST_DATABASE_URL` was not configured.
- Migration chain validation: `alembic heads` reports `0007_sched_exec_idem` as the sole head. The Compose PostgreSQL database applied this migration successfully on backend startup; duplicate/concurrency integration validation still needs a dedicated `TEST_DATABASE_URL`.
- Frontend production build: passed (`tsc -b && vite build`). Vitest could not load `vite.config.ts` in this Windows environment because its `externalize-deps` plugin failed to spawn a child process with `EPERM`; the scheduled history regression test was added but could not be executed.
- Full backend suite did not complete in this environment; the focused Feature 009 test command completed successfully. PostgreSQL idempotency/concurrency validation remains pending until a disposable PostgreSQL `TEST_DATABASE_URL` is available.