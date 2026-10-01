# Feature 005 Quickstart and Verification

## Runtime prerequisites

- PostgreSQL and the repository's normal backend environment.
- Python 3.13 dependencies, including `tzdata`.
- Node.js version required by the frontend package.
- Apply the new Alembic migration before using schedule endpoints.
- Run backend and tests with `PYTHONTZPATH=""` so Python uses the packaged IANA database consistently.

For local PowerShell sessions, set `$env:PYTHONTZPATH=""` before starting Python or pytest. Verify timezone data with `python -c "from zoneinfo import ZoneInfo; print(ZoneInfo('America/Sao_Paulo'))"` from `backend/`.

## Manual workflow

1. Open an existing active Monitoring Configuration and navigate to its scheduling section.
2. Confirm the initial state says no schedule is configured.
3. Choose daily, weekly, or monthly; enter local time and select a named timezone from the backend catalogue. Supply the ISO weekday for weekly or day 1–31 for monthly.
4. Confirm the UI labels schedule activation as “Automatic scheduling” and keeps it distinct from Monitoring Configuration enabled state.
5. Review the backend-calculated “Next scheduled occurrence” preview. The preview is informational and is not an execution.
6. Save, reload, and verify the same recurrence is restored. Edit/toggle and save; verify unrelated configuration, credential, and scope values remain unchanged.
7. Remove the schedule and verify the configuration remains with no schedule configured.
8. With two browser sessions, save in one and then attempt a stale save in the other. The stale request must receive 412, preserve the winner, and leave the draft available for review.

## Deterministic calculation verification

Use explicit reference instants in tests, never machine-clock expectations. Include normal local occurrences, exact-equality strict-future handling, recurrence rollover, monthly clamping, UTC conversion, DST gap/fold resolution, and runtime timezone data failure. Gap example: New York 2024-03-10 02:30 resolves to 03:30 local; fold example: New York 2024-11-03 01:30 selects its first instant.

## Test suites

- Backend unit: `pytest tests/unit/domain/test_schedule_calculator.py` (run from `backend/`)
- Backend application/API: `pytest tests/unit/application/test_monitoring_schedule_use_cases.py tests/api/test_monitoring_schedule.py` (run from `backend/`)
- PostgreSQL persistence/migration/concurrency: `pytest tests/integration/test_monitoring_schedule_persistence.py tests/integration/test_monitoring_schedule_concurrency.py` (run from `backend/` with `TEST_DATABASE_URL` set to a dedicated PostgreSQL database; do not report as passed if not run)
- Frontend: `npm test -- --run --pool=vmThreads --reporter=dot` (run from repository root; `vmThreads` is used for this Windows environment)
- Scheduling accessibility: `npm test -- --run src/test/features/monitoring-configurations/schedule-accessibility.test.tsx` (run from repository root; uses existing `axe-core` and Testing Library setup)
- Frontend production build: `npm run build`

No SQLite fallback is permitted for PostgreSQL-dependent verification.

## Validation record

Feature 005 status (2026-09-29): implementation complete; automated validation complete; manual visual validation pending (T045 only). The unsaved-draft indicator, explicit discard behavior, in-app navigation blocker, and browser-close protection are implemented and covered by five passing navigation tests. Do not interpret the automated focus/accessibility checks as completion of manual visual inspection.

Verified 2026-09-29:

- Backend full suite: `python -m pytest` from `backend/` using the project virtual environment — 126 passed, 15 PostgreSQL-dependent tests skipped because `TEST_DATABASE_URL` was not set for that full-suite invocation.
- Feature 005 PostgreSQL suites: `pytest tests/integration/test_monitoring_schedule_persistence.py tests/integration/test_monitoring_schedule_concurrency.py` against the dedicated PostgreSQL test database — 4 passed. No SQLite substitute was used.
- Frontend full suite: `npm test -- --run --pool=vmThreads --reporter=dot` — 31 test files and 101 tests passed.
- Frontend production build: `npm run build` — passed. Vite reported only its large-bundle advisory.
- Convergence draft-navigation suite: `npm test -- --run src/test/features/monitoring-configurations/schedule-dirty-navigation.test.tsx --pool=vmThreads --reporter=dot --testTimeout=10000` — 5 passed.
- Scheduling accessibility suite: `npm test -- --run src/test/features/monitoring-configurations/schedule-accessibility.test.tsx --pool=vmThreads --reporter=dot` — 1 passed (React `act(...)` warnings only).
- Backend startup/import: `python -c "from app.api.main import app; print(app.title)"` succeeded with non-production placeholder database and CORS settings; no database connection was attempted by this import check.
- Scheduling keyboard, accessible-name/state, error/preview/conflict, dialog-focus, and axe checks passed. Browser-only visual focus indication remains a manual inspection item because jsdom does not render focus-ring visuals.
- Dirty schedule drafts now have a visible unsaved-state message, explicit discard action, in-app route blocker, and browser `beforeunload` warning. `schedule-dirty-navigation.test.tsx` verifies clean navigation, dirty navigation (stay/leave), discard, save reset, and `beforeunload` behavior.

## Accessibility inspection

Automated scheduling accessibility coverage must assert keyboard focus order/operation, associated labels and states, field-linked errors, accessible preview/conflict feedback, axe findings, and confirmation-dialog focus movement. Manually inspect that focus indicators remain visibly distinguishable throughout the form and that any dialog-focus behavior not reliably asserted in automation follows the existing application confirmation-dialog pattern (including focus restoration when closed).

Manual visual focus inspection status (2026-09-29): not executed. Browser used: none; the configured Computer Use browser inventory returned no browsers (`cua.getState()` reported `browsers: []`), and both the in-app browser and Chrome browser bindings were unavailable. Controls not visually checked: recurrence selector, timezone selector, time input, Automatic scheduling switch, save/remove actions, and removal dialog. Outcome: no visual-focus result can be claimed; T045 remains open and blocked until an inspectable browser surface is available. Automated keyboard/focus and axe checks remain as reported above.

## Out of scope check

No scheduler service, poller, queue, MiningExecution creation, repository clone/mining, findings, or execution history should be present as a result of Feature 005.
