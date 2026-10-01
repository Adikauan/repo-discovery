# Feature Specification: Scheduled Execution

**Feature Branch**: `009-scheduled-execution`  
**Created**: 2026-09-30  
**Status**: Draft  
**Input**: User description: “Create Feature 009 - Scheduled Execution. Automatically execute enabled Monitoring Configurations using Feature 005 schedules and the existing Feature 006/008 execution pipeline.”

## Clarifications

### Session 2026-09-30

- Q1: What should happen to occurrences missed while the application is offline, and how should startup restore schedules? → A: Skip offline occurrences without catch-up; on startup load current eligible schedules and establish a fresh baseline. The periodic runner calculates each schedule's next future occurrence and makes it eligible when due; no per-occurrence timer record is required.
- Q2: What should happen when manual and scheduled execution contend for one Monitoring Configuration? → A: Reuse Feature 006's atomic active-execution guard; the winner runs, a scheduled loser is skipped without queueing, and a manual loser receives the existing normalized conflict.
- Q3: What should happen to an already-running scheduled Mining Execution after a duplicate trigger or restart? → A: Do not invoke it again or create a replacement; leave its persisted state to existing Feature 006 stale-execution reconciliation.
- Q4: How should schedule changes or deletion interact with an already calculated occurrence? → A: Recheck persisted enabled state and version at dispatch; whichever edit/dispatch commits first defines the coherent captured version. A changed version may run only occurrences strictly after its persisted update time; deletion/disable cancels future dispatches without changing history.
- Q5: How should duplicate scheduler triggers and deployment topology be handled? → A: Make (Monitoring Configuration, scheduled occurrence) idempotent, support one scheduler-enabled application instance per deployment, and use bounded scheduled-execution capacity that skips without queue when full. Do not add distributed scheduling or leader election.
- Q6: How is the single scheduler process selected? → A: Use `SCHEDULER_ENABLED` to designate the only process that starts the scheduler runner. Default it to true for local/single-process development; set it false for additional API workers. This is an operational single-instance constraint, not distributed coordination.

## User Scenarios & Testing

### User Story 1 - Run an eligible configuration on schedule (Priority: P1)

As a user who configured a schedule, I want the system to start repository mining at the scheduled time so that configured repositories are analyzed without a manual request.

**Why this priority**: Automatic execution is the central value of this feature.

**Independent Test**: Configure an enabled schedule for an enabled Monitoring Configuration, advance a controlled clock to its occurrence, and verify one scheduled Mining Execution enters the existing mining pipeline and reaches the outcome produced by that pipeline.

**Acceptance Scenarios**:

1. **Given** an enabled Monitoring Configuration with an enabled daily, weekly, or monthly schedule and an available scheduler worker, **When** an occurrence becomes due while the scheduler is active, **Then** one Mining Execution is created with trigger `scheduled` and a snapshot of that occurrence's configuration and schedule context.
2. **Given** a scheduled Mining Execution is created, **When** processing begins, **Then** it uses the same execution lifecycle and repository mining orchestration as a manual execution.
3. **Given** the repository mining pipeline succeeds, partially succeeds, or fails, **When** the scheduled run finishes, **Then** the Mining Execution has the corresponding normal Feature 008 final status and is visible in ordinary execution history, dashboard, and repository results.

### User Story 2 - Restore schedules safely after restart (Priority: P1)

As an operator, I want enabled schedules to be restored after application restart so that future occurrences continue without manual rescheduling.

**Why this priority**: Schedules must survive process restarts to be useful.

**Independent Test**: Start the scheduler with persisted schedules, stop and restart it, then verify persisted eligible schedules are reloaded, the periodic runner calculates future due occurrences, and past occurrences are not replayed.

**Acceptance Scenarios**:

1. **Given** enabled configurations and schedules persisted before startup, **When** the scheduler starts, **Then** startup reconciliation loads them and the periodic runner calculates the next future occurrence using Feature 005 recurrence and timezone semantics; the occurrence becomes eligible when due without a per-occurrence timer object or persistence row.
2. **Given** one or more occurrences passed while the application was offline, **When** it restarts, **Then** those missed occurrences are skipped and no catch-up Mining Executions are created.
3. **Given** a scheduled execution was already persisted as active before restart, **When** schedules are reconciled, **Then** the scheduler does not create another execution for that active occurrence or restart its mining pipeline.

### User Story 3 - Respect schedule changes and eligibility (Priority: P1)

As a user, I want schedule edits, disabling, and deletion to affect future automatic runs predictably while retaining existing execution history.

**Why this priority**: Running obsolete or disabled schedules could trigger unexpected repository access and mining.

**Independent Test**: Change or disable a persisted schedule while the scheduler is running and verify that the next dispatch uses current persisted eligibility and recurrence state, without modifying previous executions.

**Acceptance Scenarios**:

1. **Given** a Monitoring Configuration is disabled or its schedule is disabled, **When** its occurrence becomes due, **Then** no Mining Execution is created.
2. **Given** a schedule is edited before an occurrence is dispatched, **When** dispatch rechecks persisted schedule state, **Then** the old occurrence is canceled and only an occurrence from the current schedule version may run.
3. **Given** a schedule is deleted, **When** the scheduler reconciles persisted schedules, **Then** the deleted schedule has no future dispatch and existing Mining Executions remain unchanged.
4. **Given** a schedule edit and dispatch contend at the same instant, **When** one operation commits first, **Then** the scheduler either captures the committed old schedule version before the edit or observes the new version and considers only its occurrences strictly after that version's update time; it never creates an execution with an ambiguous mixture of versions or catches up a time that passed before the edit.

### User Story 4 - Prevent duplicate and conflicting execution (Priority: P1)

As a user or operator, I want scheduled runs to honor the same-configuration execution limit and occurrence idempotency so that manual and scheduled work cannot overlap or duplicate.

**Why this priority**: Duplicate or concurrent mining can waste provider resources and make results ambiguous.

**Independent Test**: Trigger the same scheduled occurrence more than once and race a manual request against it; verify only one active Mining Execution wins and duplicate scheduled triggers do not create additional executions.

**Acceptance Scenarios**:

1. **Given** a manual execution is active for a Monitoring Configuration when its schedule becomes due, **When** the scheduler attempts dispatch, **Then** the occurrence is skipped without creating another active execution; the manual execution continues normally.
2. **Given** a scheduled execution wins the same-configuration active-execution guard, **When** a manual request is made, **Then** the manual request receives the existing normalized conflict behavior.
3. **Given** the same schedule occurrence is triggered repeatedly, **When** duplicate dispatch attempts occur, **Then** at most one Mining Execution exists for that occurrence and subsequent attempts are harmless no-ops.
4. **Given** a scheduled Mining Execution is already active, **When** another due/duplicate event is considered for that configuration, **Then** it is not started concurrently; normal stale-execution reconciliation remains governed by Feature 006.

## Edge Cases

- Occurrences missed while the application is offline are skipped, not replayed; startup establishes a fresh scheduling baseline and reconciles eligible persisted schedules for periodic due-time evaluation. No individual in-memory or persisted timer object is required per occurrence, and no timer persistence model is introduced.
- A process restart during a scheduled mining run does not resume or duplicate that mining run. Its persisted active state remains subject to Feature 006 stale-execution reconciliation.
- A newly enabled or edited schedule does not cause an occurrence earlier than its persisted update time to be run late; its first eligible occurrence is strictly after both the current scan baseline and schedule update time.
- The scheduler has a bounded capacity for concurrent scheduled executions; if capacity is unavailable when an occurrence becomes due, that occurrence is skipped without creating an execution or queueing delayed work.
- If a configuration or schedule is disabled/deleted before dispatch, no execution is created, even if a candidate was calculated during a prior scan.
- If manual and scheduled requests race, the existing atomic same-configuration active-execution guard determines the winner; the loser follows existing conflict behavior. A scheduled occurrence that loses is skipped, not queued for later execution.
- Duplicate delivery for a single scheduled occurrence is idempotent, including after a restart.
- Feature 005 remains authoritative for recurrence, timezone, monthly day clamping, and daylight-saving gaps/overlaps.
- A mining failure or partial result is represented by the ordinary Mining Execution status and safe error metadata; the scheduler does not add a second status model or retry that occurrence.
- Exactly one application process/instance per deployment may start the scheduler runner. The runner starts from FastAPI lifespan only when `SCHEDULER_ENABLED=true`; additional API worker processes must use `SCHEDULER_ENABLED=false`. The default is true for local/single-process development. This operational constraint is not distributed coordination; no leader election or cross-process scheduler lock is provided.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST consider a Monitoring Configuration eligible only when its `enabled` state is true and its associated schedule exists and has `enabled` state true.
- **FR-002**: The system MUST calculate daily, weekly, and monthly occurrences using Feature 005 recurrence semantics, including its timezone, monthly nonexistent-day, and daylight-saving behavior.
- **FR-003**: When an eligible occurrence becomes due while the scheduler is active and scheduling capacity is available, the system MUST create one ordinary Mining Execution with trigger `scheduled` and invoke the same execution orchestration used by manual executions.
- **FR-004**: Scheduled executions MUST use the Feature 006 lifecycle and immutable execution snapshot, which internally preserves schedule-trigger context including the scheduled occurrence and schedule version; credentials MUST remain governed by existing execution security rules. This internal context MUST NOT be added to public execution DTOs solely for Feature 009; public execution APIs MUST keep scheduler/idempotency metadata private unless another approved requirement requires a safe field.
- **FR-005**: Scheduled executions MUST use the Feature 008 Repository Mining Engine and its existing repository processing, counters, error normalization, and aggregate status behavior. The scheduler MUST NOT implement a second mining pipeline.
- **FR-006**: Scheduled executions MUST appear in existing global and configuration execution history, execution dashboards, and repository execution results without separate scheduled-run entities or presentation flows.
- **FR-007**: The system MUST enforce the existing Feature 006 rule allowing at most one active Mining Execution per Monitoring Configuration across manual and scheduled triggers. Stale active executions MUST be reconciled only according to Feature 006 behavior.
- **FR-008**: The system MUST make scheduled occurrence creation idempotent so duplicate scheduler triggers for the same Monitoring Configuration and scheduled occurrence cannot create more than one Mining Execution.
- **FR-009**: If a manual execution is active when an occurrence becomes due, the scheduled occurrence MUST be skipped without creating a Mining Execution or queueing delayed work. If a scheduled execution wins the active-execution guard, a concurrent manual request MUST receive the existing normalized conflict response.
- **FR-010**: At scheduler startup, the system MUST reload persisted schedules and configurations, establish a startup baseline, and periodically evaluate current eligible schedules using Feature 005 recurrence calculation. A calculated next occurrence becomes eligible when due; no individual in-memory or persisted timer object is required for each occurrence and no occurrence timer table may be introduced.
- **FR-011**: Occurrences whose scheduled time passed while the application was offline MUST NOT be replayed or converted into catch-up executions.
- **FR-012**: Before dispatch, the scheduler MUST recheck current persisted configuration enabled state, schedule enabled state, schedule existence, and schedule version. Disabled/deleted schedules MUST not dispatch.
- **FR-013**: Schedule edits MUST invalidate previously calculated future occurrences. Dispatch and edit MUST use a deterministic persisted version check so execution snapshots capture one coherent schedule version and no stale candidate can dispatch an obsolete version. The first occurrence under a changed schedule version MUST be strictly after its persisted update time; edits MUST NOT cause a past wall-clock time to be caught up.
- **FR-014**: Schedule deletion MUST remove that schedule from future scheduler reconciliation without deleting or changing historical Mining Executions.
- **FR-015**: If a scheduled Mining Execution is already active, a duplicate or competing event MUST NOT start another pipeline for that configuration. Existing Feature 006 stale reconciliation remains authoritative; Feature 009 MUST NOT introduce automatic run recovery.
- **FR-016**: The scheduler MUST NOT automatically retry failed or partially completed mining executions. A later recurrence is an independent occurrence.
- **FR-017**: Scheduler activity and safe dispatch outcomes MUST be observable through existing application logging/operational conventions without logging credentials or raw provider internals.
- **FR-018**: Exactly one application process/instance per deployment MUST be configured with `SCHEDULER_ENABLED=true`; additional API worker processes, when used, MUST set it to false. The scheduler runner MUST start from application lifespan only in that designated process. The local/single-process default is true. Feature 009 MUST NOT introduce distributed scheduling, leader election, or cross-process scheduler locking.
- **FR-019**: The scheduler MUST NOT add WebSockets, Server-Sent Events, cancellation, AI/LLM analysis, findings analysis, or new mining rules.
- **FR-020**: Concurrent scheduled Mining Executions MUST be bounded. If capacity is unavailable when an occurrence is due, the occurrence MUST be skipped without creating a Mining Execution or queueing work for later.

### Key Entities

- **Scheduled Occurrence**: A specific due instant calculated from a persisted Feature 005 schedule version for one Monitoring Configuration; it is the idempotency identity for a scheduled trigger.
- **Mining Execution**: Existing Feature 006 execution record, created with scheduled trigger and immutable snapshot; it remains the sole execution entity for both manual and scheduled runs.
- **Schedule Trigger Context**: Existing snapshot context identifying the scheduled occurrence and schedule version that caused the Mining Execution.
- **Monitoring Configuration / Schedule**: Existing Feature 002/005 records whose current enabled states determine future eligibility; changing them never rewrites existing execution snapshots.

## Success Criteria

### Measurable Outcomes

- **SC-001**: For each eligible occurrence observed by the active scheduler, no more than one scheduled Mining Execution is persisted.
- **SC-002**: All schedule types produce due instants consistent with Feature 005 for daily, weekly, monthly, timezone, and daylight-saving cases.
- **SC-003**: Startup reconciliation loads currently eligible persisted schedules; periodic evaluation calculates their next occurrences from Feature 005 state, and a due occurrence becomes eligible for execution without per-occurrence timer persistence or objects. Offline missed occurrences do not create executions.
- **SC-004**: Across concurrent manual and scheduled requests for one configuration, at most one active Mining Execution is persisted and only the winner enters mining orchestration.
- **SC-005**: Every scheduled run that starts uses the same repository mining pipeline and produces the same lifecycle/status/counter semantics as a manual run with equivalent snapshot scope.
- **SC-006**: Changes to schedule/configuration eligibility prevent stale future dispatch while preserving all existing Mining Execution snapshots and results.
- **SC-007**: Concurrent scheduled Mining Executions never exceed the configured limit, and a due occurrence observed while capacity is exhausted does not create a delayed execution.

## Assumptions

- Feature 005 recurrence calculation, timezone validation, monthly day clamping, and DST rules are authoritative and are reused without semantic changes.
- Feature 006 already provides the scheduled trigger, immutable snapshot fields, schedule trigger context, same-configuration active-execution protection, and stale reconciliation behavior.
- Feature 008 already exposes an application-owned orchestration entry point reusable by both manual and scheduler initiation.
- The deployment configures exactly one scheduler-enabled backend process per deployment. Local/single-process development defaults `SCHEDULER_ENABLED=true`; additional API workers use false. No distributed scheduling, leader election, or cross-process scheduler locking is provided.
- Scheduler-dispatched mining runs synchronously through the existing orchestration entry point; process interruption does not cause automatic replay or restart of the same occurrence.
- Conservative missed-run policy: skip every occurrence at or before startup baseline; do not create a backlog after downtime.
- If an occurrence loses the existing active-execution conflict to a manual run, it is skipped and not queued.
