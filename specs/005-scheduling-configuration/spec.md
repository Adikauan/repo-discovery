# Feature Specification: Scheduling Configuration

**Feature Branch**: `005-scheduling-configuration`

**Created**: 2026-09-29

**Status**: Draft

**Input**: User description: "Allow users to define, persist, validate, and display optional daily, weekly, or monthly schedules for existing Monitoring Configurations, including timezone-aware next-occurrence previews, without introducing automatic execution or mining."

## Clarifications

### Session 2026-09-29

- Q: If two people edit the same schedule concurrently, how should the system handle a save based on stale data? → A: Reject the stale save with a conflict and require reload/review.

## User Scenarios & Testing

### User Story 1 - Configure a recurrence (Priority: P1)

As a user managing a Monitoring Configuration, I can create and save a daily, weekly, or monthly schedule with a local execution time and named timezone so the intended future cadence is recorded.

**Why this priority**: Persisting an explicit recurrence is the core user outcome and the prerequisite for understanding when it would next be eligible.

**Independent Test**: For an existing configuration, create and save one schedule of each recurrence type, reopen the configuration, and verify the selected recurrence, relevant fields, timezone, and schedule enabled state are restored without changing unrelated configuration data.

**Acceptance Scenarios**:

1. **Given** an existing Monitoring Configuration has no schedule, **When** the user opens scheduling configuration, **Then** the interface identifies that no schedule is configured and allows the user to create one.
2. **Given** the user chooses daily recurrence, **When** they provide an execution time and named timezone and save, **Then** the schedule is persisted with those values and no weekly or monthly recurrence field.
3. **Given** the user chooses weekly recurrence, **When** they provide one valid weekday, execution time, and named timezone and save, **Then** the schedule is persisted with those values and no monthly recurrence field.
4. **Given** the user chooses monthly recurrence, **When** they provide a day from 1 through 31, execution time, and named timezone and save, **Then** the schedule is persisted with those values and no weekly recurrence field.
5. **Given** a saved schedule, **When** the user changes its recurrence type, **Then** fields specific to the prior recurrence are cleared or ignored and cannot affect the saved schedule.
6. **Given** required schedule data is absent or invalid, **When** the user saves, **Then** clear field-level feedback is shown and the invalid schedule is not persisted.
7. **Given** a user edits schedule values, **When** they save successfully and reopen the configuration, **Then** the same recurrence intent and enabled state are restored.
8. **Given** another user has saved a newer schedule after this user's draft was loaded, **When** this user saves the stale draft, **Then** the system reports a conflict, preserves the newer persisted schedule, and keeps the stale draft available for review.

---

### User Story 2 - Understand the next scheduled occurrence (Priority: P1)

As a user, I can see a timezone-aware preview of the next calculated schedule occurrence so I can verify the cadence and local time I configured.

**Why this priority**: A recurrence is difficult to validate without a concrete next-occurrence preview, especially across month boundaries and daylight-saving transitions.

**Independent Test**: Supply fixed reference instants for daily, weekly, and monthly schedules across before-time, after-time, week/month rollover, leap-year, and daylight-saving cases; verify the exact next instant and its displayed local date/time and timezone.

**Acceptance Scenarios**:

1. **Given** an enabled daily schedule and a reference instant before its local execution time, **When** the preview is calculated, **Then** it identifies that day's occurrence.
2. **Given** an enabled daily schedule and a reference instant at or after its local execution time, **When** the preview is calculated, **Then** it identifies the next calendar day's occurrence.
3. **Given** an enabled weekly schedule and a reference instant before the configured weekday's execution time, **When** the preview is calculated, **Then** it identifies the upcoming occurrence in the current week; otherwise it identifies the next matching weekday.
4. **Given** an enabled monthly schedule whose configured day is beyond the final valid day of a month, **When** the preview is calculated for that month, **Then** it uses that month's final calendar day, including February's leap-year length.
5. **Given** the local execution time falls in a daylight-saving gap, **When** the occurrence is calculated, **Then** the time is moved forward by the size of the gap, preserving its position within that gap.
6. **Given** the local execution time occurs twice during a daylight-saving rollback, **When** the occurrence is calculated, **Then** the earlier instant is selected so that the schedule has one occurrence for that local calendar date.
7. **Given** a preview is shown for an enabled schedule, **When** the user views it, **Then** it is labeled as a calculated occurrence or preview and not as a guaranteed execution.
8. **Given** an explicit reference instant exactly equal to an occurrence, **When** the next occurrence is calculated, **Then** the result is strictly later than the reference instant.

---

### User Story 3 - Manage schedule lifecycle independently (Priority: P2)

As a user, I can disable, re-enable, or remove a schedule without changing whether the Monitoring Configuration itself is enabled or losing its GitLab connection and scope.

**Why this priority**: Schedule activation and configuration activation represent different user intent; conflating them could unexpectedly alter unrelated configuration behavior.

**Independent Test**: For configurations in both enabled states, disable and re-enable an existing schedule, then remove it; verify the recurrence remains while disabled, schedule absence is distinct from disabled, and the configuration, credential, scope, and enabled state remain unchanged.

**Acceptance Scenarios**:

1. **Given** a configured schedule, **When** the user disables it and saves, **Then** the recurrence, time, and timezone remain persisted while its status indicates that scheduling is disabled.
2. **Given** a disabled schedule, **When** the user re-enables it and saves, **Then** its recurrence is retained and the preview is available again.
3. **Given** a Monitoring Configuration whose enabled state differs from the schedule enabled state, **When** either state is edited, **Then** the other state remains unchanged.
4. **Given** a configured schedule, **When** the user removes it, **Then** the Monitoring Configuration remains and no schedule is reported; its enabled state, GitLab credential, and GitLab scope are preserved.
5. **Given** a configuration has no schedule, a disabled schedule, or an enabled schedule, **When** the user views its schedule status, **Then** these states are clearly distinguishable.

### Edge Cases

- A Monitoring Configuration may be enabled with no schedule, disabled with an enabled schedule, or enabled with a disabled schedule; schedule edits never alter configuration enabled state.
- A schedule is disabled while retaining all recurrence fields and has no next eligible occurrence preview until re-enabled.
- A monthly day such as 29, 30, or 31 is clamped to the final day of shorter months; the configured day itself remains unchanged for later months.
- A configured local wall-clock time falls into a daylight-saving gap or overlap; the deterministic resolution rules in FR-008 apply.
- A local occurrence equals the supplied reference instant; the next occurrence is strictly later, not equal.
- A user changes recurrence type without supplying the new recurrence's required fields; validation blocks saving and stale fields from the former type do not satisfy it.
- A timezone identifier is unknown, unsupported, or removed from the supported timezone catalogue; saving fails with actionable feedback and the prior schedule remains intact.
- A schedule save or removal fails; unsaved values remain available for correction or retry and persisted configuration data is unchanged.
- A schedule draft was loaded before another user saved a newer version; the stale save is rejected without replacing the newer schedule and remains available for review.
- A calculated occurrence crosses a UTC date boundary; it is displayed in the configured timezone with the corresponding instant preserved.
- Schedule preview data is refreshed after recurrence, time, timezone, enabled state, or reference instant changes and is not treated as stored authoritative schedule data.

## Requirements

### Functional Requirements

- **FR-001**: A Monitoring Configuration MAY have no schedule or one configured schedule. The system MUST distinguish no schedule from an existing disabled schedule.
- **FR-002**: A configured schedule MUST contain exactly one recurrence type: daily, weekly, or monthly; an enabled/disabled state; an execution time; and a named timezone.
- **FR-003**: A daily schedule MUST define one occurrence per local calendar day at its configured execution time in its configured timezone.
- **FR-004**: A weekly schedule MUST define exactly one valid day of week, execution time, and timezone. Day-of-week values MUST use ISO numbering, Monday=1 through Sunday=7.
- **FR-005**: A monthly schedule MUST define a day of month from 1 through 31, execution time, and timezone. When that day does not exist in a month, that month's occurrence MUST use its final valid calendar day without changing the configured day.
- **FR-006**: Execution time MUST be a valid local wall-clock time with minute precision. Timezone MUST be a supported IANA timezone identifier available through the backend's configured timezone database and explicitly selected or accepted by the user; the browser's current timezone MUST NOT be silently persisted. A valid supported identifier MUST be preserved as submitted, including an alias if the configured runtime database recognizes it; Feature 005 MUST NOT custom-canonicalize or manually map aliases. Unsupported identifiers MUST produce the standard validation error.
- **FR-007**: Timezone-aware occurrences MUST preserve the configured local wall-clock intent across daylight-saving changes except where the configured wall time is ambiguous or nonexistent.
- **FR-008**: For a nonexistent local time during a forward clock transition, the occurrence MUST move forward by the transition gap while preserving its relative position in that gap. For an ambiguous local time during a backward transition, the earlier corresponding instant MUST be selected. Each recurrence date MUST yield no more than one occurrence.
- **FR-009**: Next-occurrence calculation MUST use an explicit reference instant, and the returned occurrence MUST be strictly later than that instant. If today's or the selected recurrence date's occurrence is equal to or earlier than the reference instant, the next applicable calendar date, week, or month MUST be used.
- **FR-010**: The same deterministic recurrence and timezone rules MUST govern the user preview and future scheduling calculations. A preview MUST be identified as calculated/predicted and MUST NOT promise that an execution will occur.
- **FR-011**: The preview MUST be available for the currently edited schedule and for the persisted schedule when one exists. A disabled schedule or absent schedule MUST NOT be presented as having a next eligible occurrence.
- **FR-012**: Users MUST be able to create, retrieve, replace/update, enable, disable, and remove a schedule. Removal MUST result in no schedule configured rather than a disabled schedule.
- **FR-013**: Changing recurrence type MUST remove or ignore recurrence-specific values that do not apply to the selected type. Persisted schedule data MUST NOT contain ambiguous active recurrence fields.
- **FR-014**: Disabling a schedule MUST preserve its recurrence, execution time, and timezone for later re-enabling. Schedule enabled state MUST remain independent from `MonitoringConfiguration.enabled`.
- **FR-015**: Creating, editing, enabling, disabling, or removing a schedule MUST NOT automatically change `MonitoringConfiguration.enabled`.
- **FR-016**: Removing a schedule MUST preserve the Monitoring Configuration, its GitLab credential, its GitLab scope, and all unrelated configuration data.
- **FR-017**: Schedule validation MUST provide clear feedback for missing or invalid execution time, timezone, weekly day, and monthly day. Invalid schedule data MUST NOT replace a previously valid persisted schedule.
- **FR-018**: Users MUST explicitly save schedule changes. The interface MUST distinguish unsaved schedule edits from persisted values and retain the draft after a failed save.
- **FR-019**: The schedule MUST be persisted as schedule intent, separate from transient presentation state. Formatted preview strings and transient checkbox/display state MUST NOT be authoritative persisted schedule data.
- **FR-020**: The schedule experience MUST identify no schedule, enabled schedule, and disabled schedule distinctly. Any configuration summary or detail status MUST not imply guaranteed execution.
- **FR-021**: The system MUST provide explicit, versionable operations to retrieve, create or replace, update, and remove a schedule, and to calculate its next-occurrence preview. Validation failures MUST be reported without replacing the prior valid schedule or mutating unrelated configuration state. A schedule update rejected because its version/precondition is stale MUST return HTTP 412 Precondition Failed using the project's normalized safe error contract; the winning persisted schedule MUST remain unchanged, the rejected update MUST NOT overwrite it, and the rejected draft MUST remain available for review. The response MUST NOT expose raw database errors or internal concurrency details.
- **FR-022**: Automated next-occurrence tests MUST use explicit fixed reference instants and cover daily, weekly, monthly, leap-year, timezone conversion, daylight-saving gap, and daylight-saving overlap behavior without depending on the machine clock.
- **FR-023**: This feature MUST NOT introduce a background scheduler, create a MiningExecution, determine actual execution eligibility, or perform repository mining, cloning, commit processing, findings creation, or execution-history processing. Future eligibility MUST account for both Monitoring Configuration enabled state and schedule enabled state, but that future behavior is not implemented here.
- **FR-024**: Scheduling controls MUST be keyboard operable, have programmatically associated labels and required/selected/enabled states, and expose validation and asynchronous feedback accessibly. Validation messages MUST be associated with their fields and MUST NOT rely only on color. Preview loading/success/error and stale-update conflict feedback MUST be programmatically available. Visible focus MUST be preserved, and destructive confirmation dialogs MUST manage focus according to existing application patterns.
- **FR-025**: The global API error handler MUST return responses compatible with the existing RFC 9457 Problem Details contract and MUST provide a deterministic, safe top-level error code for relevant statuses: HTTP 400=`invalid_request`, 404=`not_found`, 409=`conflict` where applicable, 412=`stale_update`, 422=`validation_error`, and 500=`unexpected_error`. Existing project conventions for additional statuses such as 428=`invalid_precondition` and 503=`unexpected_error` remain compatible. Safe field-level validation codes MAY further distinguish scheduling errors such as `invalid_schedule` and `invalid_timezone`; they do not replace the required top-level status code. Unexpected failures MUST return HTTP 500 with generic safe content. API responses MUST NOT expose raw exception text, stack traces, database details, timezone-library internals, provider/runtime response bodies, low-level parsing errors, or request-sensitive values. Internal exceptions may be logged only under the existing safe logging policy.

### Key Entities

- **Schedule**: Optional recurrence intent belonging to one Monitoring Configuration, with enabled state, recurrence type, local execution time, named timezone, and the applicable recurrence-specific value.
- **Daily recurrence**: One local calendar-day occurrence at the configured wall-clock time.
- **Weekly recurrence**: One selected ISO weekday occurrence per week at the configured wall-clock time.
- **Monthly recurrence**: One selected day-of-month occurrence per month, clamped to the month's final day when necessary.
- **Next-occurrence preview**: A calculated future instant and its local display in the schedule timezone, based on an explicit reference instant; it is not an execution record or guarantee.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A user can create, save, reopen, edit, and remove a schedule using visible application controls; an integration-style frontend test covers each recurrence type and verifies that unrelated configuration values remain unchanged.
- **SC-002**: For 100% of fixed reference-time test cases, daily and weekly previews select the first applicable recurrence strictly after the reference instant.
- **SC-003**: For 100% of tested monthly dates, the preview uses the configured day when it exists and the final day of the month otherwise, including leap and non-leap February.
- **SC-004**: For 100% of specified daylight-saving gap and overlap test cases, the calculated instant follows the documented deterministic resolution and displays the intended timezone.
- **SC-005**: In 100% of lifecycle tests, creating, editing, toggling, or removing a schedule leaves Monitoring Configuration enabled state, GitLab credential, GitLab scope, and unrelated configuration fields unchanged.
- **SC-006**: In 100% of schedule state tests, no schedule, disabled schedule, and enabled schedule are distinguishable, and no preview is described as a guaranteed execution.
- **SC-007**: No test or user workflow in this feature creates an execution or starts mining, cloning, or commit processing.
- **SC-008**: In 100% of concurrent stale-save tests, the outdated save is rejected, the newer schedule remains persisted, and the rejected draft remains available for review.
- **SC-009**: All scheduling controls are reachable and operable by keyboard; their names, required/selected/enabled states, associated validation messages, preview states, and stale-conflict feedback are programmatically exposed. Automated accessibility checks cover programmatic requirements, and any focus-indicator/dialog-focus checks not supported by automation are recorded as explicit manual inspection criteria.
- **SC-010**: For every documented scheduling API error category, responses use the normalized safe contract and contain none of the prohibited raw exception, stack, database, timezone-library, provider/runtime-body, or low-level parser details.

## Assumptions

- Named timezones use the IANA Time Zone Database identifiers; the supported list and update policy are implementation-plan decisions.
- A newly created schedule is enabled by default because creating it is an explicit request to configure future automatic scheduling; the user can disable it before or after saving.
- Time input has minute precision and uses a 24-hour local wall-clock representation.
- A next occurrence is strictly after the supplied reference instant; equality means that occurrence is no longer upcoming.
- A nonexistent local time is shifted forward by the daylight-saving gap; an ambiguous local time resolves to its earlier instant.
- Feature 009 will own actual scheduling/execution eligibility and may reuse the deterministic schedule calculation introduced here.
- Monitoring Configuration lifecycle, credential persistence, scope persistence, and enabled state are supplied by the preceding features and remain independently managed.
