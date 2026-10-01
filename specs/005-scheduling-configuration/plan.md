# Implementation Plan: Feature 005 — Scheduling Configuration

**Branch**: `005-scheduling-configuration` | **Date**: 2026-09-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification in `specs/005-scheduling-configuration/spec.md`.

## Summary

Add an optional, independently enabled schedule to each Monitoring Configuration. Persist daily, weekly, or monthly recurrence as local wall-clock time plus an IANA timezone. A single backend calculator provides strict-future next-occurrence previews for saved and unsaved candidates. Full-replacement writes use schedule-specific optimistic concurrency. The UI supports editing, preview, explicit save, and removal. No scheduler, execution, or mining behavior is added.

## Technical Context

**Language/Version**: Python 3.13; TypeScript (project-pinned version).

**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy, Alembic; React, TypeScript, Vite, Material UI, React Router; Python `datetime`/`zoneinfo` plus first-party `tzdata` runtime package.

**Storage**: PostgreSQL. Schema changes are delivered through Alembic; no SQLite substitution.

**Testing**: pytest for domain/application/API/persistence, Vitest and Testing Library for frontend; PostgreSQL integration tests run against PostgreSQL when available.

**Target Platform**: Existing web application and Python API deployment, including local Windows development and the existing Linux container image.

**Project Type**: Full-stack web application.

**Performance Goals**: Schedule reads and writes calculate one next occurrence without materializing execution data. Timezone catalogue generation may be cached per process. No formal throughput target is introduced.

**Constraints**: Recurrence logic has exactly one authoritative backend implementation; use an explicit reference instant; named timezone data must be available consistently; do not alter unrelated configuration state; preserve the approved DST gap/fold semantics; no scheduler or MiningExecution.

**Scale/Scope**: Zero or one schedule-state row per Monitoring Configuration; daily/weekly/monthly recurrence; scope limited to configuration UI/API/domain/persistence/tests.

## Constitution Check

### Before design

- Clean Architecture and inward dependencies: **PASS** — recurrence calculation belongs in the domain; use cases orchestrate persistence and clock/reference handling; API and SQLAlchemy remain adapters.
- One authoritative business-rule implementation: **PASS** — one backend calculation service; frontend only renders its response.
- Explicit, versionable contracts: **PASS** — versioned REST routes, typed schedule DTOs, RFC 9457 validation errors, and conditional updates.
- Secure boundaries: **PASS** — scheduling contains no GitLab credential values and adds no secret-bearing telemetry.
- Migration-managed persistence: **PASS** — one Alembic migration with relational constraints.
- Risk-based verification: **PASS** — deterministic fixed-instant unit tests, API/application tests, PostgreSQL concurrency/migration tests, and UI lifecycle tests.
- Deliberate UX: **PASS** — no-schedule, disabled, enabled, loading, validation, conflict, and removal states are explicit; unsaved edits are retained on failure.
- Incremental simplicity: **PASS** — standard library timezone calculation with a justified `tzdata` package; no scheduler framework or distributed lock.

### After design

All gates remain **PASS**. The schedule version/tombstone addresses stale updates without coupling to general configuration revision or introducing distributed locking. Timezone data availability is made explicit for Windows and container runtime. No Feature 009 behavior is brought forward.

## Design Decisions

### Domain and recurrence calculation

- Model `MonitoringSchedule` as optional recurrence intent, separate from `MonitoringConfiguration.enabled`.
- Enforce exact recurrence invariants: daily has neither recurrence-specific field; weekly has ISO `day_of_week` 1–7 and no month day; monthly has `day_of_month` 1–31 and no weekday. Full-replacement input rejects non-null irrelevant fields rather than silently accepting ambiguous payloads.
- Store `execution_time` as a naive SQL `TIME` with minute precision, interpreted only in its selected IANA timezone. Never persist the recurring wall time as a fixed UTC time.
- Implement one pure calculation service taking a complete schedule and an aware reference instant. Convert the reference to schedule-local time, enumerate candidate recurrence dates, resolve the candidate wall time, convert to UTC, and select the earliest instant strictly greater than the reference. Equality is not upcoming.
- Monthly candidate day is `min(configured_day_of_month, last_day_of_target_month)`; keep the configured value unchanged.
- Resolve DST explicitly by making both `fold` candidates and round-tripping via UTC. For normal times, deduplicate equal instants. For overlaps, choose the earliest UTC instant. For gaps, choose the forward round-trip projection, preserving the candidate's relative offset within the gap (e.g. 02:30 → 03:30 for a one-hour gap). This is the approved specification behavior.
- Use `zoneinfo.ZoneInfo`; package first-party `tzdata` and configure backend/test processes with `PYTHONTZPATH=""` so Windows and Linux use a deliberate, consistent IANA data source. Accept only identifiers available from that configured supported database. Preserve a valid submitted identifier exactly, including runtime-recognized aliases; do not canonicalize or manually map aliases. Unsupported identifiers are validation errors; absent/corrupt runtime timezone data is a safe startup/service configuration failure and must not silently fall back.
- Add/update `tzdata` in `backend/pyproject.toml` and the lock/install metadata if present; set `PYTHONTZPATH` in the backend runtime/test configuration (including the existing container configuration) before `zoneinfo` is initialized.

### Persistence and concurrency

- Add one `MonitoringSchedule` state row per configuration, with a `configured` discriminator, monotonic `version`, nullable recurrence fields when unconfigured, and timestamps. Initial no-row state is virtual version 0.
- Create/replace and delete are compare-and-swap mutations. Require `If-Match`; missing precondition is HTTP 428, and an update rejected because its version/precondition is stale returns HTTP 412 Precondition Failed. The winning schedule remains unchanged, the stale mutation cannot overwrite it, and the frontend retains the rejected draft for review. Return only the project's normalized safe error contract; do not expose raw database errors or internal concurrency details. Database conditional update/insert is transactional and uses existing PostgreSQL/application concurrency controls; no distributed locks.
- Keep an unconfigured version tombstone after removal and increment the version. This prevents stale clients from resurrecting deleted state through an ABA sequence. Deleting an already-absent schedule with the current ETag is an idempotent no-op.
- Schedule versioning is independent of Monitoring Configuration versioning, so unrelated configuration edits do not conflict with schedule editing. An unchanged replacement may be a no-op and does not increment the schedule version.
- Existing soft retirement semantics remain unchanged: retirement retains the associated schedule row; schedule endpoints on inactive/retired configurations return the existing safe 404 outcome.

### API and preview

- Use schedule-specific routes under `/api/v1/monitoring-configurations/{id}/schedule`: GET, full-replacement PUT, conditional DELETE, and POST `/preview` for unsaved candidates. Add read-only `GET /api/v1/schedule-timezones` for identifiers available through the backend's supported IANA timezone database. Preserve accepted identifiers exactly; do not claim alias canonicalization.
- GET returns `{schedule: null | ScheduleDto, nextOccurrence: null | NextOccurrenceDto}` and ETag. PUT returns the saved schedule, calculated preview, and new ETag. DELETE clears only schedule configuration. Disabled/absent schedules return a null next occurrence.
- Candidate preview validates a complete candidate and returns only a calculated next occurrence. Optional `referenceInstant` supports deterministic clients/tests; otherwise the application supplies an injected current UTC instant. Preview is never persisted and never creates an execution.
- API weekday values are ISO 1–7. Time is `HH:mm`; timezone is a supported IANA timezone identifier, returned exactly as persisted. The reusable global FastAPI error handler in `backend/app/api/errors.py` owns deterministic top-level Problem Details codes: 400=`invalid_request`, 404=`not_found`, 409=`conflict` where applicable, 412=`stale_update`, 422=`validation_error`, and 500=`unexpected_error`; preserve existing 428=`invalid_precondition` and 503=`unexpected_error` conventions. Safe field-level validation codes may distinguish `invalid_schedule` and `invalid_timezone`. Controllers must not duplicate generic exception mapping. Unexpected errors return HTTP 500 with generic safe content, never raw exception text, stack traces, database details, timezone-library internals, provider/runtime response bodies, low-level parsing errors, or request-sensitive values. Internal logging follows existing safe logging policy.
- The UI obtains timezone choices from the backend, uses the preview endpoint for current unsaved values, and formats returned instants only. It does not reimplement recurrence arithmetic.

### Frontend behavior

- Extend the Monitoring Configuration detail/edit flow with a feature-specific schedule section/form, recurrence selector, timezone selector, recurrence-specific fields, next-occurrence preview, save, and confirmed removal.
- Keep draft form state distinct from persisted schedule and transient preview. Switching recurrence type clears the no-longer-applicable field. The form clearly distinguishes “Monitoring Configuration enabled” from “Automatic scheduling”.
- Preserve local draft values after network, validation, or 412 conflict failures. For stale writes, show a conflict and offer reload/review; do not silently replace the draft or overwrite the newer server state.
- Meet FR-024 for keyboard operation, accessible labels/states/errors, preview/conflict announcements, visible focus, and destructive-dialog focus handling. Reuse existing frontend accessibility tooling; record manual focus checks only where automation cannot verify them.
- On removal, preserve all unrelated configuration fields, GitLab credential, GitLab scope, and configuration enabled state. Warn about navigation with dirty form state according to existing form conventions.

## Project Structure

### Documentation (this feature)

```text
specs/005-scheduling-configuration/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    └── api-v1.md
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── domain/
│   │   ├── entities/monitoring_schedule.py
│   │   └── services/schedule_calculator.py
│   ├── application/
│   │   ├── ports/monitoring_schedule_repository.py
│   │   └── use_cases/
│   │       ├── get_monitoring_schedule.py
│   │       ├── replace_monitoring_schedule.py
│   │       ├── remove_monitoring_schedule.py
│   │       ├── preview_monitoring_schedule.py
│   │       └── list_schedule_timezones.py
│   ├── infrastructure/
│   │   └── database/ (SQLAlchemy schedule mapping, repository/UoW integration)
│   └── api/v1/monitoring_schedules.py
├── alembic/versions/0004_monitoring_schedule.py
└── tests/
    ├── unit/domain/test_schedule_calculator.py
    ├── unit/application/test_monitoring_schedule_use_cases.py
    ├── api/test_monitoring_schedule.py
    └── integration/test_monitoring_schedule_persistence.py

src/features/monitoring-configurations/
├── api/scheduleApi.ts
├── hooks/useMonitoringSchedule.ts
├── types/schedule.ts
├── components/ (schedule section, form, recurrence fields, timezone selector, preview)
└── pages/ (existing configuration detail flow integration)

src/test/features/monitoring-configurations/
└── schedule-*.test.tsx
```

**Structure Decision**: Extend the existing backend Clean Architecture and frontend Monitoring Configuration feature module. The listed names identify planned touchpoints; implementation must follow existing local naming and dependency conventions rather than create parallel framework layers.

## Verification Strategy and Traceability

- **Recurrence and DST**: fixed-instant pure service tests verify daily before/after/equality, every ISO weekday, weekly rollovers, month/year/leap boundaries, UTC conversion, São Paulo, New York gaps/folds, and a non-hour Lord Howe gap. Trace: FR-002–FR-010, FR-022; SC-002–SC-004.
- **Validation and DTOs**: domain/API tests cover required/invalid time, supported timezone identifiers and aliases, weekday, month-day, stale recurrence fields, disabled/absent preview, normalized status-to-top-level-code mappings (400/`invalid_request`, 404/`not_found`, 409/`conflict` where applicable, 412/`stale_update`, 422/`validation_error`, 500/`unexpected_error`, plus existing 428 and 503 conventions), safe field-level validation codes, and redaction of prohibited error details including unexpected-error internals. Trace: FR-006, FR-011–FR-013, FR-017, FR-021, FR-025; SC-010.
- **Use cases and data safety**: application tests prove preview does not persist, invalid input leaves old values untouched, schedule lifecycle leaves configuration/credential/scope unchanged, and soft retirement follows Feature 002. Trace: FR-012, FR-014–FR-019, FR-023; SC-005–SC-007.
- **Concurrency and persistence**: PostgreSQL-backed tests execute competing If-Match updates/removal, assert exactly one stale write receives 412, preserve the winner, verify monotonic ETag/tombstone behavior, constraints, and migration up/down. Trace: FR-021; SC-008. These tests are explicitly reported as not executed if PostgreSQL is unavailable.
- **API contract**: exercise GET/PUT/DELETE/preview/timezone routes, ETag/If-Match semantics, 400/404/409/412/422/500 mappings plus 428/503 conventions, normalized safe Problem Details codes/messages, and prohibited-detail redaction (including raw exception/stack/database/timezone/request-sensitive values); ensure preview writes no rows. Trace: FR-017–FR-021, FR-025; SC-010.
- **Frontend**: component and integration-style tests cover no schedule, each daily/weekly/monthly complete workflow, recurrence-specific controls and field clearing, timezone selection, server preview rendering, save/edit/remove, dirty-state retention, stale 412 draft preservation/conflict feedback, and independent Monitoring Configuration status. Accessibility checks cover keyboard interaction, labels/states, associated errors, announcements, and dialog focus. Trace: US1–US3, FR-014–FR-020, FR-024; SC-001, SC-005–SC-009.
- **Scope guard**: tests/review verify there is no scheduler, job polling, MiningExecution, repository mining, cloning, findings, or execution history introduced. Trace: FR-023; SC-007.

## Deferred to Feature 009+

Actual eligibility evaluation, scheduler polling, queue/job dispatch, execution creation, catch-up/misfire policy, distributed execution coordination, and any repository mining are explicitly deferred. Feature 009 may reuse the backend calculation service and must evaluate configuration enabled state and schedule existence/enabled state together.

## Complexity Tracking

No constitution violations or exceptions are proposed. `tzdata` is justified because Python deployments include Windows development and a slim Linux image that cannot be assumed to provide IANA data; a pinned package source makes named-timezone validation reproducible. No other new runtime dependency or distributed coordination mechanism is planned.
