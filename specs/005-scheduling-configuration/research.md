# Feature 005 Research

## Timezone and recurrence calculation

**Decision**: Use Python's standard-library `datetime` and `zoneinfo.ZoneInfo` for IANA timezone validation and all recurrence calculations. Keep one pure backend domain service that accepts a complete schedule and an explicit aware reference instant, and returns the first matching UTC instant strictly after the reference. Application/API use cases provide the current UTC instant for ordinary reads/writes; tests pass fixed instants.

**Rationale**: Python 3.13 is the backend runtime and `zoneinfo` implements IANA rules with the `fold` distinction. The configured recurrence is local wall-clock time plus a named timezone, so each candidate must be built in local calendar terms and then converted to UTC. The frontend receives the authoritative instant and only formats it in the schedule timezone.

**Alternatives considered**: Storing a recurring UTC time was rejected because it would change the user's intended wall-clock time when UTC offset changes. Implementing recurrence separately in TypeScript was rejected because preview and future execution could diverge. A third-party datetime library was rejected because the required IANA and fold handling are already available in the standard library.

**DST resolution**: For each candidate local date/time, create `fold=0` and `fold=1` interpretations and round-trip each through UTC back to the named timezone. If the original wall time round-trips, it is valid; deduplicate identical instants for ordinary times. If both distinct candidates round-trip to the same wall time, it is ambiguous and the earlier UTC instant is selected. If neither round-trips, it is nonexistent; select the forward projection, which moves the occurrence by the transition gap while preserving its relative position (for example, `02:30` becomes `03:30` for a one-hour gap). Keep the recurrence's original local calendar date when evaluating whether the occurrence is strictly after the reference.

**Deterministic examples**:

- `America/New_York`, `2024-03-10 02:30` -> `2024-03-10T07:30:00Z` (03:30 local after a one-hour gap).
- `America/New_York`, `2024-11-03 01:30` -> `2024-11-03T05:30:00Z` (the first 01:30; do not use the second occurrence).
- `Australia/Lord_Howe`, `2024-10-06 02:15` -> `2024-10-05T15:45:00Z` (02:45 local after a 30-minute gap).
- Monthly day 31 -> April 30, February 28 in 2027, and February 29 in 2028; keep configured day 31 for following months.

## Timezone database availability and supported values

**Decision**: Declare the first-party `tzdata` Python package as a runtime dependency and set `PYTHONTZPATH=""` for the backend service/test process so `zoneinfo` reads the packaged IANA dataset consistently rather than silently preferring a host-specific database. Accept only identifiers available through that configured supported IANA timezone database and expose those identifiers through a read-only schedule-timezone catalogue endpoint. Preserve a valid submitted identifier exactly, including an alias if the runtime database recognizes it; do not implement custom alias canonicalization or manual alias mappings. Store and return the accepted identifier, never a display label or fixed offset. Update the package through ordinary dependency maintenance so political timezone changes are deliberate and testable.

**Rationale**: The application stack includes a Python backend on `python:3.13-slim` and local Windows development. Python's official `zoneinfo` documentation says the module uses system data first and then the first-party `tzdata` package; systems without either source raise `ZoneInfoNotFoundError`, and Windows commonly lacks an IANA database. The dependency is therefore justified for portable named-timezone support. Selecting from a backend-provided list keeps UI values aligned with the server's validator. The list is the runtime's supported identifier set, not a promise that aliases are canonicalized.

**Alternatives considered**: Relying only on the Linux image's system database was rejected because it would not make local Windows development reliable and could produce different results across environments. Using only the browser's timezone catalogue was rejected because the frontend must not define accepted schedule semantics. A fixed project list or a hand-maintained alias/canonicalization table was rejected because it would create a second source of accepted timezone semantics and require manual mapping.

## Persistence and concurrency

**Decision**: Store the schedule as one configuration-owned state row with a monotonic version and an explicit configured/no-schedule state. A configured row contains exactly one recurrence's fields; removal clears the schedule fields but retains a version tombstone. Use `If-Match`/ETag compare-and-swap for full replacement and removal.

**Rationale**: Existing configurations must not require schedules, while the API must distinguish no schedule from disabled. Retaining a tombstone after removal prevents an old editor holding an earlier ETag from recreating or overwriting a schedule after another editor has removed/recreated it (the ABA case). Versioning remains independent of Monitoring Configuration edits, and the database update is transactional without distributed locks.

**Alternatives considered**: Reusing the Monitoring Configuration revision was rejected because unrelated configuration edits would conflict with schedule drafts. Deleting all schedule/version state on removal was rejected because an old absent-schedule ETag could become current again after create/remove. Last-write-wins updates were rejected because the accepted clarification requires stale schedule edits to return a conflict and preserve the newer version.

## API and frontend preview

**Decision**: Provide schedule GET, full-replacement PUT, conditional DELETE, an unsaved-candidate preview POST, and a read-only timezone catalogue. GET and PUT responses include the backend-calculated next occurrence for an enabled schedule. Preview accepts a validated full candidate and an optional reference instant; when omitted, the application supplies its current UTC clock value. All preview results are transient.

**Rationale**: Persisted schedule reads need a convenient preview, and a candidate endpoint lets users review valid unsaved values without saving or mutating the current schedule. The same calculation service serves both paths. Existing API contracts use RFC 9457 Problem Details and ETags/If-Match; stale update preconditions use HTTP 412 Precondition Failed, and missing preconditions use 428. Schedule errors use normalized safe codes/messages and never expose raw exceptions, stack traces, database/timezone internals, provider/runtime response bodies, or low-level parsing errors.

**Alternatives considered**: Frontend-only preview was rejected because recurrence semantics must be authoritative on the backend. Saving intermediate candidate state was rejected because invalid or unsaved edits must not mutate the current schedule. PATCH was rejected in favor of a complete replacement payload that cannot leave recurrence-specific fields ambiguous.

## Lifecycle and execution boundary

**Decision**: Soft-retiring a Monitoring Configuration leaves its schedule state in place under Feature 002's existing retention behavior; schedule endpoints treat the retired configuration as not found. A schedule-specific DELETE removes only the configured schedule fields/state and never changes configuration enabled state, GitLab credentials, or scope. No job, scheduler, execution, or eligibility query is introduced.

**Rationale**: Feature 005 only records scheduling intent. The later Feature 009 execution path can reuse the pure calculation contract and will independently require configuration enabled, a configured schedule, and schedule enabled.

## Sources

- Python 3.13 `zoneinfo` documentation: [https://docs.python.org/3.13/library/zoneinfo.html](https://docs.python.org/3.13/library/zoneinfo.html) — IANA support, system/package search order, `PYTHONTZPATH`, and missing-data behavior.
- PEP 495: [https://peps.python.org/pep-0495/](https://peps.python.org/pep-0495/) — `fold=0` denotes the earlier reading; gap/fold concepts and offset behavior.
- Python 3.13 `datetime` documentation: [https://docs.python.org/3.13/library/datetime.html](https://docs.python.org/3.13/library/datetime.html) — aware datetime operations and timezone conversion.
- Existing project patterns: Feature 002 API contract and update routes (ETag/If-Match, 428/412, soft retirement); Feature 004 scope repository and SQLAlchemy compare-and-swap patterns; backend runtime in `backend/pyproject.toml` and `backend/Dockerfile`.
