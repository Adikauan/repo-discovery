# Feature Specification: Execution Model and History

**Feature Branch**: `006-execution-model-history`  
**Created**: 2026-09-29  
**Status**: Draft  
**Input**: User description: "Create Feature 006 - Execution Model and History, introducing Mining Execution as a first-class concept and allowing users to create, inspect, and review execution history without implementing repository mining."

## Clarifications

### Session 2026-09-29

- Q: Uma Monitoring Configuration existente e não aposentada, mas com `enabled=false`, pode receber execução manual? Agendamento continua sem influência. → A: Sim. Manual execution is allowed when the configuration exists, is not retired/deleted, and no non-stale active execution remains after request-time reconciliation under FR-027; configuration and schedule enabled state affect only future automatic/scheduled eligibility.
- Q: Como a execução manual deve terminar nesta feature, que ainda não minera repositórios? Sugiro criar `pending`, avançar a `running` e finalizar como `failed` com resumo seguro `mining_unavailable`, sem inventar resultados. → A: Create as `pending`, capture the snapshot, transition through the normal lifecycle to `running`, perform only Feature 006 orchestration, then complete as `completed`; all mining counters remain zero, with no repository execution records, discovery, clones, findings, or simulated mining results.

## User Scenarios & Testing

### User Story 1 - Request a manual execution (Priority: P1)

As a user, I can request an execution from an eligible Monitoring Configuration and receive a durable execution record that captures the configuration context used for that request. This gives the execution history a trustworthy starting point before repository mining is introduced.

**Why this priority**: Manual execution creation establishes the core entity, historical snapshot, and active-execution safety rule on which the remaining stories depend.

**Independent Test**: Request an execution for an eligible configuration and verify the internal lifecycle begins at `pending`, traverses `running`, and is persisted/returned as `completed` before the successful response, with its identifier, manual trigger, creation time, immutable configuration/scope snapshot, zero counters, and no credential material. In a controlled orchestration failure, verify a finalized safe `failed` record. Request another while a non-stale execution remains active and verify deterministic conflict with no second record; request another while a stale execution remains active and verify reconciliation followed by creation.

**Acceptance Scenarios**:

1. **Given** an existing non-retired Monitoring Configuration with no active execution, **When** a user requests a manual execution, **Then** one uniquely identified execution is initially created internally with trigger `manual`, status `pending`, its creation time, and a snapshot of configuration and persisted scope intent; the successful synchronous request subsequently completes before its HTTP 201 response as specified in scenario 7.
2. **Given** the Monitoring Configuration is edited after an execution is created, **When** the user opens the earlier execution, **Then** its captured configuration name, GitLab URL, scope intent, trigger context, and captured configuration revision (when available) remain unchanged.
3. **Given** the configuration has GitLab credentials, **When** an execution snapshot is created or read, **Then** no raw, decrypted, or encrypted credential value is stored or returned as execution history.
4. **Given** a non-stale execution for the configuration is `pending` or `running`, **When** another manual request is submitted, **Then** the request receives the project's normalized active-execution conflict response, the existing execution is unchanged, and no second active execution is created. Stale active executions follow scenario 10 instead.
5. **Given** two manual requests arrive concurrently for the same configuration, **When** both attempt to create an active execution, **Then** exactly one request succeeds and at most one active execution is persisted.
6. **Given** a Monitoring Configuration is disabled but not retired and has no active execution, **When** a user requests a manual execution, **Then** the request is allowed; configuration enabled state and schedule existence/enabled state do not block manual execution.
7. **Given** a non-retired Monitoring Configuration has no active execution, **When** a manual execution is requested and Feature 006 orchestration succeeds, **Then** the request creates one durable history record, completes `pending -> running -> completed` before returning HTTP 201, returns the current persisted execution as `completed`, keeps all four mining counters at zero, creates no repository execution or mining/finding data, and clearly indicates that repository mining did not occur.
8. **Given** a Monitoring Configuration is retired or deleted according to established lifecycle rules, **When** a user requests a manual execution, **Then** the request is rejected safely and no execution is created.
9. **Given** a manual execution has been created and its Feature 006 orchestration fails in a controlled application path, **When** the failure is handled, **Then** the execution reaches `failed`, has `completed_at`, contains only a normalized safe error code and user-readable summary, keeps all counters at zero, creates no repository/finding data, is no longer active, and a later manual request may be created.
10. **Given** an existing `pending` or `running` execution has exceeded the configured staleness threshold without a final transition, **When** a new manual request checks it, **Then** the application reconciles it to `failed` with `completed_at`, safe `execution_interrupted` metadata, unchanged snapshot/counters, and no fabricated data, then permits a distinct new request in the same controlled flow. An active execution below the threshold still produces the active-execution conflict.

### User Story 2 - Review execution history (Priority: P1)

As a user, I can review executions across the application or for one Monitoring Configuration, so that I can understand what was requested and what state each execution reached.

**Why this priority**: A durable execution record provides little user value unless its history is discoverable and ordered predictably.

**Independent Test**: Create executions for multiple configurations with tied timestamps and varied statuses/triggers; verify global and configuration-specific lists, filters, newest-first ordering with deterministic tie-breaking, and appropriate loading, empty, and error states.

**Acceptance Scenarios**:

1. **Given** executions exist for multiple configurations, **When** the user opens global execution history, **Then** the list shows each execution's identifier, configuration snapshot name, trigger, status, lifecycle timestamps, and duration when available, ordered newest first with a stable secondary order.
2. **Given** the user opens a configuration's execution history, **When** the list loads, **Then** only that configuration's executions are shown with the same stable ordering and useful status/trigger filters.
3. **Given** no executions exist for the selected view, **When** history loads, **Then** an explicit empty state appears without implying that an execution was created.
4. **Given** an execution history request fails, **When** the user views the page, **Then** a safe error state and retry path are available without exposing internal details.

### User Story 3 - Inspect an execution and its lifecycle (Priority: P1)

As a user, I can open an execution to inspect its immutable snapshot, status, timestamps, counters, and safe error summary, so that historical records remain understandable after configuration changes.

**Why this priority**: Execution detail is necessary to verify audit history, explain outcomes, and support future lifecycle and mining features.

**Independent Test**: Open executions in initial, running, and final states; verify snapshot and lifecycle data, valid timestamp progression, counter values, safe error summaries, missing-record behavior, and that public clients cannot set arbitrary statuses.

**Acceptance Scenarios**:

1. **Given** an execution exists, **When** the user opens it, **Then** the detail view shows its identifier, status, trigger, snapshot name and GitLab URL, creation/start/completion times, calculable duration, summary counters, and safe error summary when present.
2. **Given** a `pending` execution is started, **When** its state changes to `running`, **Then** `started_at` is populated once and cannot later be overwritten.
3. **Given** a `running` execution reaches a final state, **When** it becomes `completed`, `partially_completed`, or `failed`, **Then** `completed_at` is populated once; later transitions from that final state are rejected without changing history.
4. **Given** a client attempts an unsupported transition or generic status mutation, **When** the request is processed, **Then** the transition is rejected safely and existing execution history remains unchanged.
5. **Given** a configuration is retired or removed according to existing lifecycle rules, **When** a user reviews a prior execution, **Then** its snapshot and execution details remain available; new requests follow the established eligibility rule.
6. **Given** an execution identifier does not exist, **When** the user requests its details, **Then** the API and interface return the established safe not-found outcome.

### Edge Cases

- A non-stale active execution may be `pending` or `running`; either state conflicts with a new manual request and prevents a second active execution. Stale active executions follow FR-027.
- Concurrent creation attempts may race; only one may become active for the same configuration.
- A configuration may have no selected groups or repositories; an empty scope is captured as-is and does not prevent a manual request unless the established lifecycle rules make the configuration ineligible. It never fabricates repository work.
- The configuration or its GitLab scope may change after an execution is created; historical snapshot content remains unchanged.
- Retiring or removing a configuration must not cascade-delete, rewrite, or make its historical execution snapshots unreadable.
- A caller may attempt a transition from a final state, skip `pending -> running`, set a timestamp out of order, or overwrite a previously populated timestamp; these mutations are rejected.
- A failed execution may have an error summary, but it must not contain raw exception/provider data, stack traces, secrets, or other sensitive values.
- A manual execution has no required schedule snapshot; it must not be treated as a scheduled trigger because a schedule exists or is enabled.
- Repository counters begin at zero and must not be populated with invented processing results.
- The no-mining orchestration path completes after `pending -> running -> completed`; the completed state means all work available in Feature 006 finished, not that repositories were mined.
- The orchestration-only flow leaves no active execution behind and keeps repository, successful repository, failed repository, and finding counters at zero.
- A controlled application failure before start may transition `pending -> failed` with `started_at` null; a failure after start transitions `running -> failed` with `started_at` preserved. Both set `completed_at` and clear active-execution eligibility.
- A process interruption may leave an active row temporarily; only a later manual request performs stale reconciliation using the configured threshold. No background polling/recovery is introduced.

## Requirements

### Functional Requirements

- **FR-001**: Users MUST be able to request a manual execution for an existing Monitoring Configuration that is not retired under the established lifecycle rules.
- **FR-002**: A successful manual request MUST create exactly one uniquely identified Mining Execution with trigger type `manual` and an initial status of `pending`.
- **FR-003**: A Monitoring Configuration MUST own zero or more executions, and each execution MUST belong to exactly one configuration.
- **FR-004**: At most one execution with status `pending` or `running` MUST exist for a Monitoring Configuration at any time. A manual execution request conflicts when a non-stale `pending` or `running` execution already exists; it MUST be rejected deterministically using the project's normalized conflict outcome and MUST leave that active execution unchanged. A stale active execution is reconciled according to FR-027 before deciding whether a new request may proceed.
- **FR-005**: The one-active-execution rule MUST be enforced by the backend under concurrent requests, not solely by frontend controls.
- **FR-006**: Manual execution eligibility MUST NOT depend on `MonitoringConfiguration.enabled`, whether a schedule exists, or whether `Schedule.enabled` is true. Manual execution requires only that the configuration exists, is not retired/deleted under established lifecycle rules, and has no active execution after applying request-time stale-execution reconciliation under FR-027. `MonitoringConfiguration.enabled` and `Schedule.enabled` remain separate inputs to future automatic/scheduled execution eligibility; Feature 006 does not implement that eligibility evaluation.
- **FR-007**: Each execution MUST capture an immutable snapshot containing the configuration identifier and name, GitLab instance URL, persisted selected-group and selected-repository scope intent, trigger context, and the configuration revision when one is available.
- **FR-008**: A group selection in an execution snapshot MUST remain a group-level scope rule. Feature 006 MUST NOT expand selected groups into repository lists.
- **FR-009**: An execution snapshot MUST NOT store raw, decrypted, or encrypted GitLab credential values. Execution creation MUST NOT rediscover GitLab hierarchy, validate GitLab credentials, clone repositories, or perform mining.
- **FR-010**: The trigger model and contracts MUST define `manual` and `scheduled`. Feature 006 MUST create only manual executions; it MUST NOT implement scheduled trigger processing or automatic scheduler behavior.
- **FR-011**: The supported statuses MUST be `pending`, `running`, `completed`, `partially_completed`, and `failed`. `completed`, `partially_completed`, and `failed` are final states.
- **FR-012**: Allowed state transitions MUST be `pending -> running`; `pending -> failed` for a controlled failure before start or request-time stale reconciliation; `running -> completed` and `running -> partially_completed` for valid orchestration/processing outcomes; and `running -> failed` for controlled failure or request-time stale reconciliation. A failure/reconciliation from `pending` MUST leave `started_at` null; one from `running` MUST preserve its populated `started_at`. Every final transition MUST set `completed_at` once. Transitions from a final state and any other transition MUST be rejected through application-controlled lifecycle operations; the public API MUST NOT expose arbitrary status mutation. Stale reconciliation timing and behavior are defined by FR-027.
- **FR-013**: `created_at` MUST be set when an execution is created. `started_at` MUST be null until the execution enters `running`, then set once. `completed_at` MUST be null until a final state is reached, then set once. Populated lifecycle timestamps MUST NOT be overwritten.
- **FR-014**: Each execution MUST retain counters for repository count, successful repository count, failed repository count, and finding count. These counters MUST start at zero and Feature 006 MUST NOT fabricate repository-processing or finding results.
- **FR-015**: An execution MAY retain a safe high-level error summary when failed. For a controlled Feature 006 orchestration failure after creation, the lifecycle MUST reach `failed`, set `completed_at`, retain a normalized safe application `error_code` and safe user-readable `error_summary`, remain inactive, and preserve zero mining counters. API responses and user-visible content MUST not expose secrets, raw exceptions, stack traces, database details, or raw provider responses.
- **FR-016**: Users MUST be able to list executions globally and for a specific Monitoring Configuration, retrieve execution details, and filter lists by status, trigger type, and configuration where applicable.
- **FR-017**: Execution list results MUST be ordered newest first, using a deterministic secondary ordering when creation timestamps are equal.
- **FR-018**: Execution list and detail views MUST display their available identifying context, status, trigger, timestamps, duration, snapshot summary, counters, and safe error summary, and MUST provide clear loading, empty, and error states.
- **FR-019**: From a Monitoring Configuration, users MUST be able to request a manual execution, receive progress/loading feedback, understand a conflict, and access a successfully created execution without implying that repository mining results exist.
- **FR-020**: Execution snapshots and history MUST remain readable and unchanged after later configuration edits, retirement, or removal according to established lifecycle behavior.
- **FR-021**: New executions MUST be rejected for missing or retired configurations using the project's normalized safe error contract.
- **FR-022**: A manual execution MUST be created as `pending`, capture its immutable snapshot, transition to `running` through the normal lifecycle service, perform only Feature 006 orchestration, and transition to `completed` when that orchestration succeeds. The synchronous create endpoint MUST finish the successful flow before returning HTTP 201, whose body reflects the current persisted `completed` state. For this orchestration-only flow, `completed` means all processing available in Feature 006 completed successfully and MUST NOT imply that repository mining occurred. The frontend MUST use wording that makes this distinction clear.
- **FR-023**: During the Feature 006 orchestration-only flow, `repository_count`, `successful_repository_count`, `failed_repository_count`, and `finding_count` MUST remain zero. The flow MUST create no RepositoryExecution or other repository/mining/finding data, perform no repository discovery or cloning, and generate no simulated results. It MUST finish without leaving the execution active.
- **FR-024**: The public execution API MUST support manual creation, global and configuration-specific listing, and detail retrieval. It MUST NOT provide generic client-controlled status updates.
- **FR-025**: Execution history MUST remain available independently of mutable child data required by the current configuration, including scope selections.
- **FR-026**: If a controlled application/orchestration failure occurs after execution creation but before successful completion, the application lifecycle MUST transition `running -> failed`, or `pending -> failed` if the failure occurs before start. The failure MUST set `completed_at`; `started_at` MUST follow normal transition semantics; `error_code` MUST be normalized and safe; `error_summary` MUST be user-readable and safe; all mining counters MUST remain zero; no repository/finding data may be created; and the failed record MUST no longer block a later manual execution. Raw exception, secret, provider, and database details MUST NOT be persisted or exposed. Repository-mining failure semantics remain out of scope.
- **FR-027**: A `pending` or `running` execution is stale only when elapsed time from `created_at` (`pending`) or `started_at` (`running`) is strictly greater than the configured execution-staleness threshold and no final transition has been recorded. The threshold MUST be configurable and default to five minutes. When a manual request finds a stale active execution, the application MUST reconcile it through lifecycle logic to `failed`, set `completed_at`, preserve `started_at` semantics, assign safe normalized `error_code=execution_interrupted` and a safe summary that the previous execution did not complete, then permit a distinct new manual execution in the same controlled flow. A non-stale active execution MUST retain the existing conflict outcome. Reconciliation MUST be request-driven, atomic with active-execution checking/creation as appropriate, and safe under concurrent requests so at most one active execution exists. It MUST create no repository/mining/finding data and MUST NOT expose raw runtime details. No background job, scheduler polling, scheduled dispatch, or mining recovery worker is introduced.

### Key Entities

- **Mining Execution**: A durable record of one manual or future scheduled execution, its lifecycle state, timestamps, counters, and optional safe error summary.
- **Execution Snapshot**: Immutable context captured at creation, including configuration identity/name, GitLab instance URL, scope intent, trigger metadata, and an available configuration revision; never includes credential material.
- **Monitoring Configuration**: The owning configuration. It may have many historical executions; current edits do not rewrite prior snapshots.
- **GitLab Scope Snapshot**: The selected group identifiers and selected repository identifiers captured as persisted intent, without resolving group descendants.
- **Schedule Trigger Context**: Optional schedule-related context reserved for future scheduled executions; no automatic scheduling is introduced in Feature 006.

## Success Criteria

### Measurable Outcomes

- **SC-001**: For an eligible configuration with no active execution, a manual request creates one durable historical execution with a unique identifier, manual trigger, creation timestamp, and configuration/scope snapshot; the synchronous Feature 006 orchestration completes before the successful HTTP 201 response, which returns the persisted execution as `completed` with all mining counters zero and no fabricated repository/mining/finding data.
- **SC-002**: Across simultaneous manual requests for the same configuration, no more than one request succeeds in creating an active execution and no more than one active record exists afterward.
- **SC-003**: Updating or retiring a configuration after execution creation leaves all captured execution snapshot values unchanged and readable.
- **SC-004**: A user can locate executions in global and configuration-specific history, apply supported filters, and open a detail view showing all required snapshot and lifecycle fields.
- **SC-005**: Every accepted and rejected lifecycle transition produces the defined state/timestamp result, and final states cannot be changed.
- **SC-006**: No Feature 006 request, response, snapshot, or execution history contains raw, decrypted, or encrypted GitLab credential values.
- **SC-007**: All execution counters remain truthful; before repository mining exists, no repository-processing or finding outcome is invented.
- **SC-008**: The manual request journey gives users clear feedback for creation and active-execution conflict and does not suggest that repositories were mined.
- **SC-009**: The feature introduces no repository cloning, Git access, commit traversal, mining, findings, scheduled automatic execution, or dashboard analytics.
- **SC-010**: Manual execution eligibility outcomes are verified against the authoritative rule in FR-006.

## Assumptions

- Manual execution eligibility is defined authoritatively by FR-006.
- Feature 006 manual orchestration advances `pending -> running -> completed`; completion means only the orchestration work available in this feature succeeded. All mining counters remain zero and no repository execution, repository discovery/clone, mining, finding, or simulated result is created.
- Future automatic/scheduled eligibility is conceptually dependent on both `MonitoringConfiguration.enabled == true` and an existing `Schedule` with `Schedule.enabled == true`; this eligibility is not implemented in Feature 006.
- Feature 008 may perform actual repository processing while an execution is `running`, before the same lifecycle service applies its final transition.
- The future scheduler may use the `scheduled` trigger and optional schedule context, but Feature 006 does not create such records.
- Execution history is retained under existing configuration retirement/deletion semantics; historical records do not cascade-delete with mutable configuration child records.
- The API's existing safe Problem Details/error contract is reused for conflicts, validation, missing records, and unexpected failures.
- The user's current application has no authentication/authorization scope in this feature; authorization is not added here.

## Scope Boundaries

This feature implements the Mining Execution model, immutable snapshot, lifecycle, manual execution request, active-execution prevention, history lists, filters, details, and corresponding backend/frontend verification.

This feature does not implement repository mining, Git cloning, commit traversal, repository-level processing, findings, automatic scheduled execution, a scheduler/background worker, execution dashboard analytics, WebSocket progress, or fabricated counters/results.
