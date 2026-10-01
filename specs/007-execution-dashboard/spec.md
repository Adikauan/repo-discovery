# Feature Specification: Execution Dashboard

**Feature Branch**: `007-execution-dashboard`  
**Created**: 2026-09-29  
**Status**: Draft  
**Input**: User description: "Create Feature 007 - Execution Dashboard. Provide a structured dashboard for an individual Mining Execution using persisted Feature 006 data, with truthful lifecycle, snapshot, scope, counter, status, and safe error presentation; honest unavailable states for repository and finding details; and navigation from global and configuration histories. Do not implement mining, repository processing, findings generation, or scheduling."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Understand an execution (Priority: P1)

As a user, I can open an existing Mining Execution and understand what happened, when it happened, what configuration and scope were captured, and what persisted counts are available.

**Why this priority**: The dashboard's core value is making an individual historical execution understandable without rewriting or inventing its recorded facts.

**Independent Test**: Open persisted executions in each supported lifecycle state and verify that the displayed status, trigger, snapshot context, timestamps, duration, and counters match the retrieved execution data, including zero-valued counters.

**Acceptance Scenarios**:

1. **Given** an execution exists, **When** a user opens it, **Then** the dashboard displays its identifier, snapshot configuration name and GitLab URL, status, trigger, available lifecycle timestamps, calculable duration, and persisted counters.
2. **Given** the Monitoring Configuration has changed since execution creation, **When** its execution is opened, **Then** the dashboard shows the execution's captured name, URL, and scope rather than current configuration values.
3. **Given** Feature 006 orchestration completed without repository mining, **When** the dashboard is viewed, **Then** it explains that orchestration completed and repository mining was not performed.
4. **Given** the execution has zero counters, **When** the dashboard is viewed, **Then** zero is shown as persisted data and is not described as an error or missing value.

### User Story 2 - Navigate from execution history (Priority: P1)

As a user, I can reach an execution dashboard from global execution history or a Monitoring Configuration's execution history, then return to the relevant history context.

**Why this priority**: A useful execution view must be discoverable from both history journeys and preserve the user's navigation context.

**Independent Test**: Open an execution from each history view, verify the dashboard destination, and use its return navigation to reach the relevant history.

**Acceptance Scenarios**:

1. **Given** global execution history lists an execution, **When** the user opens it, **Then** the individual execution dashboard appears and offers a path back to global history.
2. **Given** a configuration-specific execution history lists an execution, **When** the user opens it, **Then** the dashboard appears and offers a path back to that configuration's execution history.
3. **Given** a user directly opens a valid dashboard destination, **When** it loads, **Then** it has a useful history navigation path even without prior in-app navigation.

### User Story 3 - Review unavailable details safely (Priority: P2)

As a user, I can see honest repository and findings states and review safe execution-level errors or status information without seeing internal or sensitive details.

**Why this priority**: Clearly distinguishing unavailable data from real zero counts preserves trust while repository mining and findings are not implemented.

**Independent Test**: Open an execution with no repository or finding records and an execution with safe error metadata; verify explicit unavailable states and safe error presentation.

**Acceptance Scenarios**:

1. **Given** an execution has no repository-level execution data, **When** the Repositories section is opened, **Then** it explains that repository processing information is unavailable and contains no fabricated rows.
2. **Given** findings are not available for an execution, **When** the Findings section is opened, **Then** it explains that findings are unavailable/not yet implemented and does not generate sample findings; the persisted finding count remains separately visible.
3. **Given** an execution has safe error metadata, **When** its details are shown, **Then** a safe error code and summary may appear while stack traces, raw exceptions, database details, provider response bodies, and credentials remain hidden.

### Edge Cases

- The execution identifier is unknown; the user receives normalized not-found feedback and a route back to execution history.
- Execution retrieval fails; a normalized error and retry action are available without exposing raw backend errors.
- A pending execution has only its creation timestamp; no start, completion, or duration is invented.
- A running execution has a start timestamp and no completion timestamp; duration is displayed only when it can be calculated safely and deterministically, without a live timer.
- A partially completed execution has summary counters but no repository detail; its state is shown without inferred repository outcomes.
- The snapshot contains no selected groups or repositories; both scope categories are represented accurately as empty selections.
- Scope labels or error summaries are long or contain unsafe values; content remains readable and unsafe internal data is not revealed.
- The dashboard is opened at a narrow viewport or operated by keyboard and assistive technology.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to open any persisted Mining Execution from global execution history and configuration-specific execution history.
- **FR-002**: The dashboard MUST represent persisted execution data and immutable Feature 006 snapshot data; it MUST NOT substitute current Monitoring Configuration values for historical snapshot values.
- **FR-003**: The dashboard header and Overview section, taken together, MUST present the execution identity, status, trigger type, snapshot Monitoring Configuration name, created timestamp, started timestamp when available, completed timestamp when available, and duration when calculable. The header MUST prioritize the execution identifier, snapshot Monitoring Configuration name, status, and trigger type. Overview MUST include created, started, and completed timestamps; duration; snapshot GitLab URL; completion meaning when available; persisted counters; safe error information when available; and scope summary. Fields MAY appear in both places where useful; duplication is not required.
- **FR-004**: The dashboard MUST support pending, running, completed, partially_completed, and failed statuses using readable status text and an accessible visual indicator. Status MUST NOT be communicated by color alone.
- **FR-005**: The dashboard MUST show persisted repository count, successful repository count, failed repository count, and finding count. It MUST present zero as valid recorded data and MUST NOT fabricate counter values.
- **FR-006**: When Feature 006 completion meaning is available, the dashboard MUST make clear that execution orchestration completed and repository mining was not performed. It MUST NOT imply that `completed` proves repositories were analyzed.
- **FR-007**: The overview MUST present the snapshot GitLab URL, selected group scope summary, and selected repository scope summary as separate categories using safe metadata captured at execution creation.
- **FR-008**: The dashboard MUST render historical context only from safe snapshot metadata returned by the execution detail API. It MUST NOT query current Monitoring Configuration state, substitute live configuration values for snapshot values, call GitLab, revalidate GitLab entities, or resolve selected groups into repositories.
- **FR-009**: The dashboard MUST provide Overview, Repositories, Findings, and execution details or status information sections. Overview MUST work with Feature 006 data alone. Repository and finding sections MUST show explicit empty or unavailable states when their corresponding records or capability are absent, without fabricated content.
- **FR-010**: The details section MAY show safe execution-level status and error information available from Feature 006. User-visible error content MUST exclude stack traces, raw exception text, database errors, provider response bodies, credentials, and authorization headers.
- **FR-011**: The dashboard MUST distinguish snapshot configuration information from current configuration state wherever both contexts are shown.
- **FR-012**: Users MUST have a useful path back to the relevant execution history from which they arrived; direct dashboard entry MUST also provide a useful execution-history navigation path.
- **FR-013**: The dashboard MUST provide loading feedback, normalized not-found behavior with a history path, and normalized retrieval-error feedback with retry. Users MUST be able to select any dashboard tab/section and manually refresh execution details through a controlled refetch. After refresh, the currently selected tab/section MUST remain active and display the refreshed execution data in that context; refresh MUST NOT reset the dashboard to Overview. This behavior MUST apply to all dashboard tabs/sections. Refresh MUST expose accessible loading and normalized failure feedback and MUST NOT query current Monitoring Configuration data or GitLab. The dashboard MUST NOT require polling or real-time updates.
- **FR-014**: The dashboard MUST support keyboard operation, semantic headings, accessible tabs or section navigation, accessible loading/error feedback, logical focus order, accessible metric labels, and status communication that does not rely on color alone.
- **FR-015**: The dashboard MUST remain usable at the representative narrow, medium, and wide viewport sizes established for the application, with metrics adapting to the available width and structured content remaining readable.
- **FR-016**: Any execution detail contract extension MUST expose only safe historical information already persisted for the execution and MUST NOT add a duplicated dashboard-specific persistence model.
- **FR-017**: This feature MUST NOT implement repository mining or execution processing, repository execution records, commit processing, findings generation, repository cloning, automatic scheduling, live progress streaming, or WebSockets.

### Key Entities *(include if feature involves data)*

- **Mining Execution**: A persisted execution with identifier, lifecycle status and timestamps, trigger, summary counters, safe error information, and a link to its immutable snapshot.
- **Execution Snapshot**: Historical configuration identity/name, GitLab URL, selected group and repository scope intent, and other safe context captured when the execution was created.
- **Execution Summary**: The persisted repository and finding counters used to summarize one Mining Execution.
- **Execution Dashboard**: A user-facing view of one Mining Execution, combining its persisted lifecycle, snapshot, summary, and safe status/error information with clearly labeled unavailable sections.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can open an existing execution from both global and configuration-specific history and return to the corresponding history context in acceptance testing.
- **SC-002**: For every supported execution status, displayed lifecycle information matches the persisted execution; absent timestamps and uncalculable durations are never shown as fabricated values.
- **SC-003**: All four displayed metrics match persisted execution counters, including executions whose counters are zero.
- **SC-004**: When configuration values change after execution creation, the displayed snapshot name, GitLab URL, and selected scope continue to match the values captured for that execution.
- **SC-005**: Users viewing a Feature 006 orchestration-only completion can correctly identify that orchestration completed and repository mining did not occur.
- **SC-006**: Missing repository and finding records are presented as explicit unavailable/empty states, with no fabricated repository rows or findings.
- **SC-007**: Unknown executions and retrieval failures provide understandable recovery paths and expose no raw backend or internal error details.
- **SC-008**: Keyboard and assistive-technology review confirms that status, metrics, sections, loading, and error feedback are perceivable and operable without relying on color or pointer input.
- **SC-009**: At the application's representative narrow, medium, and wide viewport sizes, dashboard content and navigation remain usable without unintended page-level horizontal scrolling.

## Assumptions

- Feature 006 execution detail retrieval is the authoritative source for lifecycle data, persisted counters, safe error metadata, completion meaning, and immutable snapshot values.
- Existing Feature 006 executions may have zero counters and no repository-level or finding-level records; these represent valid execution data and unavailable capabilities respectively.
- Duration is calculated from persisted timestamps; for a running execution, any displayed elapsed duration is a deterministic value calculated at retrieval/render time and does not update continuously.
- The dashboard uses existing application navigation and history destinations established by Features 001 and 006.
- Where Feature 006 does not expose safe snapshot fields already persisted, a contract extension may expose them; no current configuration lookup or duplicate dashboard read model is needed.
- This feature serves the existing general platform user and does not add authentication, authorization roles, mining processing, or scheduler behavior.

## Scope Boundaries

This feature implements the individual execution dashboard, overview, persisted metrics, historical snapshot and scope presentation, lifecycle/status and safe error presentation, honest repository and findings unavailable states, navigation from both history contexts, refresh/retry behavior, and frontend automated verification. A safe execution detail contract extension is in scope only when necessary to expose already persisted historical data.

This feature does not implement repository mining, repository-level execution processing or records, commit processing, findings generation, repository cloning, GitLab calls for display, group expansion, charts without meaningful persisted data, WebSockets, live progress streaming, or automatic scheduler execution.
