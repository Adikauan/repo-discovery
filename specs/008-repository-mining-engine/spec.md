# Feature Specification: Repository Mining Engine

**Feature Branch**: `008-repository-mining-engine`  
**Created**: 2026-09-29  
**Status**: Draft  
**Input**: User description: "Create Feature 008 - Repository Mining Engine. Implement the first real repository mining pipeline for Mining Executions, using the immutable execution scope snapshot, processing unique repositories independently with safe GitLab access, persisted repository results and counters, deterministic mining rules, bounded concurrency, aggregate execution statuses, and dashboard repository history. Do not implement automatic scheduled execution or AI/LLM analysis."

## Clarifications

### Session 2026-09-29

- Q: What should happen when scope resolution succeeds but yields zero repositories? → A: Complete successfully with all four counters at zero. Missing, inaccessible, or invalid selected scope entries remain explicit failures and must not be treated as an empty successful scope.
- Q: What is the first deterministic mining rule? → A: Use the Repository Summary Rule to produce factual bounded processing metadata. These outputs are not Findings; Feature 008 keeps `finding_count` at zero and does not add Finding persistence or TODO/FIXME detection.
- Q: What should happen when a repository has no default branch? → A: Fail that RepositoryExecution with a normalized safe error code and summary, increment the failed repository count, and continue processing other repositories where safe. Do not guess a branch or expose provider details or credentials.
- Q: How do scope-resolution failures affect an execution when other selected scope entries resolve? → A: Continue with the resolved repositories and count unresolved selected entries as failures for aggregate status. If resolved repositories succeed alongside any scope-resolution failure, the execution is partially completed; if no repository succeeds and scope failures prevent processing, it is failed. Scope failures must be represented explicitly without fabricated RepositoryExecution rows; repository counters continue to reconcile with persisted RepositoryExecution records.

## User Scenarios & Testing

### User Story 1 - Run a real mining execution (Priority: P1)

As a user, I can request a manual Mining Execution and have it process the repositories represented by the execution's saved scope, so the execution result reflects real repository processing.

**Why this priority**: This is the first feature that turns the execution lifecycle into actual mining work; later repository history and findings depend on its persisted results.

**Independent Test**: Create a manual execution with a controlled GitLab scope and mocked provider data. Verify it uses the execution snapshot, resolves each effective repository once, persists repository outcomes, and derives execution counters and final status from those outcomes.

**Acceptance Scenarios**:

1. **Given** a pending manual execution with selected repositories and/or groups, **When** the mining pipeline runs, **Then** it moves through the Feature 006 lifecycle and processes the unique effective repositories from that execution snapshot.
2. **Given** two concurrent manual execution requests for the same Monitoring Configuration, **When** execution creation applies the Feature 006 active-execution protection, **Then** at most one execution becomes active and only its winning request enters repository processing; the losing request receives the existing normalized conflict outcome.
3. **Given** the current Monitoring Configuration scope differs from the execution snapshot, **When** the execution is processed, **Then** the saved snapshot determines the scope intent and current selections are not substituted.
4. **Given** overlapping selected groups, nested groups, or an explicitly selected repository covered by a group, **When** effective scope is resolved, **Then** each effective repository is processed once in deterministic order.
5. **Given** scope resolution succeeds and finds no effective repositories, **When** the execution completes, **Then** it is completed successfully with repository, successful repository, failed repository, and finding counters all equal to zero.
6. **Given** selected groups or repositories are missing, inaccessible, or invalid for the snapshot GitLab instance, **When** scope resolution runs, **Then** the failure is explicit and is not reported as a successful empty scope.
7. **Given** a repository is processed by the Repository Summary Rule, **When** its result is persisted, **Then** factual bounded metadata such as the processed branch, files considered, and observed extensions is recorded without creating Findings and the execution finding count remains zero.
8. **Given** all repository processing finishes, **When** aggregate status is determined, **Then** counters and execution status match persisted repository outcomes.

### User Story 2 - Isolate repository failures safely (Priority: P1)

As a user, I can see successful and failed repository outcomes independently, so one repository problem does not discard results already produced for other repositories.

**Why this priority**: GitLab repositories can fail independently; preserving each result makes execution history useful and prevents one provider error from masking other outcomes.

**Independent Test**: Process multiple mocked repositories where some succeed and others fail for authentication, authorization, timeout, missing scope entities, malformed provider data, or missing branch. Verify a safe per-repository record is persisted and processing continues when safe.

**Acceptance Scenarios**:

1. **Given** one repository fails while other effective repositories remain, **When** the failure is isolated, **Then** that repository is marked failed with normalized safe error metadata and other repositories continue where safe.
2. **Given** at least one repository succeeds and at least one fails, **When** all processing ends, **Then** the Mining Execution is partially completed and successful repository results remain persisted.
3. **Given** all repositories fail or a pre-processing failure prevents repository work, **When** the execution ends, **Then** it is failed with safe execution-level error information and no repository is falsely marked completed.
4. **Given** credentials are absent or the configured GitLab instance no longer matches the execution snapshot, **When** processing begins, **Then** affected work fails safely without exposing credentials or sending snapshot identifiers to a different GitLab instance.
5. **Given** a repository has no provider-declared default branch, **When** it is processed, **Then** its RepositoryExecution fails with normalized safe error metadata, contributes to the failed count, and does not prevent other repositories from being processed.

### User Story 3 - Inspect repository processing history (Priority: P1)

As a user, I can inspect the repositories processed for an execution from its dashboard, so I can understand each repository's status, timing, findings count, and safe failure summary.

**Why this priority**: Per-repository records are the user-visible evidence that the mining engine processed the execution's actual scope.

**Independent Test**: Retrieve an execution with successful, failed, and, where valid, pending/running repository records. Verify the dashboard lists persisted repository data with safe errors, loading/empty states, and pagination or bounded result behavior appropriate to the response.

**Acceptance Scenarios**:

1. **Given** repository execution records exist, **When** a user opens the dashboard's Repositories section, **Then** each persisted record is shown with its name/path, status, timestamps, findings count, and safe error summary when present.
2. **Given** no repository records exist, **When** the section is opened, **Then** it explains the actual empty or unavailable state without sample rows.
3. **Given** the execution is partially completed, **When** its dashboard is viewed, **Then** successful and failed repository outcomes remain distinguishable and consistent with execution summary counters.

### Edge Cases

- A saved group or repository is no longer visible to the configured credential, has been deleted, or cannot be retrieved.
- The Monitoring Configuration's current GitLab URL or instance identity differs from the snapshot; historical identifiers must not be used against the other instance.
- A selected group is inaccessible while an independently selected repository remains processable, or vice versa.
- Multiple scope rules resolve to the same repository, or GitLab returns duplicate repository identifiers.
- Scope resolution succeeds with no effective repositories; the execution completes successfully with all counters at zero. Any selected group or repository that is missing, inaccessible, or invalid remains an explicit failure rather than being silently omitted.
- A repository has no default branch, is empty, or its default branch changes during processing; no branch is guessed, and missing default branch is a normalized repository failure that does not stop independent repository processing.
- GitLab returns a timeout, rate limit, forbidden response, malformed metadata, incomplete tree, or binary/oversized file. Repository Summary uses metadata eligibility; future text rules use a separate text-content eligibility policy.
- A repository has only excluded/generated files, or a repository tree contains more items than the configured processing bounds.
- A repository failure occurs after earlier repositories completed; completed records and counters remain consistent.
- A worker crashes during repository processing; persisted states remain diagnosable and unfinished work is never presented as completed.
- Duplicate invocation or retry attempts encounter already persisted repository records; processing must not duplicate outcomes.
- The configured concurrency limit is reached; no unbounded provider requests or tasks are created.
- Credentials are missing, rotated, revoked, or invalid at runtime; no secret is written to the execution snapshot or exposed in errors.

## Requirements

### Functional Requirements

- **FR-001**: A manual Mining Execution MUST use the shared Mining Execution application pipeline. The pipeline MUST be reusable by future scheduled triggers, but Feature 008 MUST NOT add automatic scheduled execution or a second trigger-specific mining implementation.
- **FR-002**: Execution lifecycle transitions MUST remain controlled by the Feature 006 lifecycle service. A mining execution MUST transition from pending to running and then to completed, partially_completed, or failed according to processing outcomes; arbitrary public status mutation MUST NOT be introduced.
- **FR-003**: The execution snapshot MUST remain authoritative for the historical scope intent. Current Monitoring Configuration group or repository selections MUST NOT replace or alter the scope intent of an existing execution.
- **FR-004**: Effective scope resolution MUST include explicitly selected repositories and repositories belonging to selected groups or their descendants under Feature 004 semantics. Projects merely shared with a selected hierarchy but owned outside it MUST be excluded.
- **FR-005**: Effective scope resolution MUST be deterministic and MUST deduplicate repositories selected through multiple groups or both group and direct repository rules. Every unique effective repository MUST be processed at most once per Mining Execution.
- **FR-006**: Scope resolution MUST safely identify unavailable selected groups/repositories and GitLab instance mismatches. Snapshot GitLab entity identifiers MUST NOT be queried against a different GitLab instance; affected work MUST fail with normalized safe error metadata.
- **FR-007**: Runtime credential resolution MUST use the approved secure credential associated with the relevant Monitoring Configuration/GitLab connection, MUST NOT store credential material in the execution snapshot, and MUST fail safely when no usable credential exists. Credential values, authorization data, and secrets MUST NOT appear in records, API responses, logs, or user-visible errors.
- **FR-008**: Each effective repository MUST have one persisted RepositoryExecution record associated with its Mining Execution. Each record MUST include the repository identifier, safe name/path snapshot, status, start and completion timestamps where available, findings count, and normalized safe error code/summary when applicable.
- **FR-009**: RepositoryExecution MUST support pending, running, completed, and failed statuses. Repository processing MUST be isolated so a repository failure does not automatically abort other safe-to-process repositories or erase completed results.
- **FR-010**: Mining executions MUST derive completed, partially_completed, or failed status from persisted repository outcomes, explicit scope-resolution failures, and pre-processing failures. A completed execution MUST represent successful processing of all effective repositories, including a successfully resolved empty effective scope; for that empty case all execution counters MUST be zero. partially_completed MUST represent at least one successful repository and at least one repository or scope-resolution failure; failed MUST represent no successful repository with one or more repository/scope failures, or a pre-processing failure preventing repository processing. If some selected entities fail resolution, remaining resolved repositories MUST still be processed where safe. Missing, inaccessible, or invalid selected scope entries MUST remain explicit failures and MUST NOT be treated as an empty successful scope or as fabricated RepositoryExecution records. Repository counters MUST continue to reconcile with persisted RepositoryExecution records.
- **FR-011**: Execution repository_count MUST equal the number of unique effective repositories selected for processing. successful_repository_count and failed_repository_count MUST equal the corresponding persisted RepositoryExecution totals. Feature 008's Repository Summary Rule produces factual summary metadata, not Findings; therefore `finding_count` MUST remain zero. Counters MUST NOT be fabricated.
- **FR-012**: GitLab access MUST retrieve only repository data needed for the first deterministic mining rule. Repository provider DTOs and errors MUST remain behind the GitLab infrastructure boundary and be normalized before application/domain use.
- **FR-013**: Repository branch selection MUST use the repository's provider-declared default branch and MUST NOT guess branch names. If no default branch is reported, that RepositoryExecution MUST fail with a normalized safe error code and summary, increment `failed_repository_count`, and allow other repositories to continue where safe. Provider details and credentials MUST NOT be exposed.
- **FR-014**: The engine MUST define an extensible deterministic mining-rule input/output contract and MUST include a Repository Summary Rule. The rule MUST produce factual bounded repository-processing metadata, including processed branch/reference, files considered, and observed file extensions. Such metadata MUST NOT be treated as Findings. Feature 008 MUST NOT add Feature 010 Finding persistence or TODO/FIXME finding detection, and `finding_count` MUST remain zero. Rule logic MUST consume normalized repository context and MUST NOT depend on provider transports, persistence mechanisms, web frameworks, or raw GitLab responses. AI, LLMs, embeddings, and semantic models MUST NOT be introduced.
- **FR-015**: Repository processing MUST distinguish metadata eligibility from text-content eligibility. Repository Summary Rule metadata eligibility MUST exclude directories and paths containing the configured exact excluded path segments, but MUST NOT exclude a file solely because it is oversized or binary; eligible blob/file metadata MAY contribute to `file_count` and observed extensions. The rule MUST NOT download file content solely to classify size or binary status. For text-content rules, files above the configured maximum size MUST be excluded from text input, and binary content MUST NOT be passed as text. A reliable provider binary indicator MAY be used without retrieval, but MUST NOT be required; where binary status is unknown, any future content reader MUST establish text safety before a rule receives decoded content. Skipping ineligible inputs MUST NOT fail a repository unless a selected rule explicitly requires them.
- **FR-016**: Repository processing concurrency MUST be bounded by a configurable maximum with a conservative default, and processing MUST NOT create unbounded tasks based on scope size. This bounds RepositoryExecution processors inside one valid Mining Execution only. Separately, the existing Feature 006 active-execution protection MUST continue to allow at most one active Mining Execution per Monitoring Configuration; Feature 008 MUST NOT add a second execution-concurrency mechanism. Database transaction boundaries MUST preserve independently completed repository outcomes.
- **FR-017**: Feature 008 MUST NOT introduce silent automatic retry behavior. Authentication and authorization failures MUST NOT be retried automatically. Any explicitly approved retry behavior MUST have bounded attempts and deterministic backoff.
- **FR-018**: Feature 008 MUST reuse Feature 006 stale/interrupted execution safety. Process crashes MUST leave unfinished records diagnosable; recovery beyond existing reconciliation MUST be explicitly deferred if not implemented. No unfinished repository may be marked completed.
- **FR-019**: RepositoryExecution and any minimal rule-result persistence MUST be created through versioned database migrations and MUST retain historical execution data without unexpected cascade deletion.
- **FR-020**: Users and the execution dashboard MUST be able to retrieve repository processing results for one Mining Execution and a safe detail view for one repository result where needed. These reads MUST NOT permit arbitrary status mutation or expose internal persistence/provider structures.
- **FR-021**: The Feature 007 Repositories dashboard section MUST replace its unavailable placeholder with persisted repository execution results, showing repository name/path, status, timestamps, findings count, and safe error summary when present. The dashboard shell and other sections MUST NOT be redesigned. Findings detail MAY remain unavailable until Feature 010.
- **FR-022**: Manual execution initiated through Feature 006 MUST invoke the real mining pipeline instead of the temporary orchestration-only completion path. Existing lifecycle, idempotency, stale reconciliation, and same-configuration active-execution protection MUST remain authoritative. A non-stale pending/running execution for the same configuration MUST cause the existing normalized conflict outcome before a losing request enters repository processing.
- **FR-023**: All provider interactions in the normal automated test suite MUST use controlled mocks. PostgreSQL-specific concurrency and persistence behavior MUST be validated against PostgreSQL when available; SQLite MUST NOT replace PostgreSQL.
- **FR-025**: The execution detail `completionMeaning` MUST distinguish legacy Feature 006 orchestration-only executions from Feature 008 mining executions, including valid empty-scope success. A private persisted completion marker MUST default to false for existing rows and become true only after the Feature 008 pipeline successfully finalizes; it MUST NOT expose additional provider or persistence internals through the API.
- **FR-024**: The feature MUST NOT implement automatic scheduled execution, a scheduler, AI/LLM analysis, embeddings, advanced findings analytics or management UI, WebSockets/SSE, user cancellation, or unbounded repository cloning.

### Key Entities

- **Mining Execution**: The existing execution record and immutable Feature 006 scope snapshot whose lifecycle, trigger, and summary counters are authoritative.
- **RepositoryExecution**: One persisted processing outcome for one unique effective repository within one Mining Execution, including safe repository identity snapshot, lifecycle, counters, and safe error metadata.
- **Repository Context**: A normalized, transport-independent set of repository identity, selected branch/reference, bounded file metadata/content, and other safe inputs consumed by mining rules.
- **Mining Rule**: A deterministic, independently executable unit that consumes Repository Context and returns a versioned or otherwise identifiable result.
- **Repository Summary Result**: The minimal persisted factual output of the Repository Summary Rule, including bounded branch/reference and file summary metadata; it is not a Finding and does not require Feature 010 Finding persistence.

## Success Criteria

### Measurable Outcomes

- **SC-001**: For every scope-resolution test case, each unique eligible repository appears in exactly one RepositoryExecution record, including overlapping groups and direct selections.
- **SC-002**: For successful, partially successful, failed, and successfully resolved empty-scope executions, persisted final status and counters exactly reconcile with RepositoryExecution outcomes; empty scope completes with all counters at zero, while invalid selected scope remains an explicit failure.
- **SC-003**: A failure in one repository does not prevent safe processing of remaining repositories, and all completed repository records remain available afterward.
- **SC-004**: Repeating the Repository Summary Rule against the same normalized repository input produces identical factual summary metadata, without producing Findings, AI services, or nondeterministic external analysis.
- **SC-005**: Automated safety tests confirm that credentials, authorization headers, raw provider bodies, stack traces, and internal database errors are not persisted or exposed in user-facing responses.
- **SC-006**: Automated tests confirm repository processing never exceeds its configured per-execution limit and overlapping scope never duplicates processing; concurrent manual requests for one Monitoring Configuration yield at most one active execution and only the winner starts repository processing.
- **SC-007**: Users can inspect persisted repository names/paths, statuses, times, findings counts, and safe errors in the existing dashboard for completed, partial, and failed executions.
- **SC-008**: File-policy tests confirm excluded directories do not contribute to summary `file_count`; oversized and binary metadata may contribute to metadata-only summary counts; no content is fetched solely for summary size/binary classification; and future text-content eligibility excludes oversized files and never passes binary content as text.

## Assumptions

- Feature 006 lifecycle, idempotency, stale execution reconciliation, immutable snapshots, and secure credential storage remain authoritative.
- Feature 004's clarified group semantics include projects owned by the selected group and its subgroups, but exclude projects merely shared from another ownership hierarchy.
- Feature 010 is not yet present in the repository; Feature 008 persists only the minimal Repository Summary result needed for factual processing history, does not create Finding persistence, and keeps `finding_count` at zero.
- Repository-level read APIs are internal application-facing product contracts for dashboard history; they do not permit callers to mutate execution or repository statuses.
- A selected repository or group becoming inaccessible should be represented as a safe processing failure while other independent scope entries continue where safe.
- The execution snapshot's GitLab instance identity/fingerprint is the authority for preventing identifiers from being reused against another provider instance; credential changes are allowed only when the secure connection still identifies that same instance.
- A conservative default repository concurrency limit and maximum source file size will be selected and documented in the implementation plan, with configuration overrides bounded to safe values.
- Retry is absent by default. If implementation requires retry for safe transient reads, the plan must define exactly retryable conditions, attempt cap, and backoff without retrying authentication or authorization errors.
- Execution-triggered scope resolution and mining are synchronous from the application's lifecycle perspective; background scheduling and live progress delivery are outside this feature.

## Scope Boundaries

Feature 008 implements effective snapshot scope resolution, unique repository processing, safe GitLab data retrieval, RepositoryExecution persistence, a deterministic Repository Summary Rule with factual non-Finding output, bounded concurrency, real counters and aggregate execution status (including successful empty scope), safe repository read APIs, and integration of real repository outcomes into the existing execution dashboard.

Feature 008 does not implement automatic scheduled execution, scheduler infrastructure, AI/LLM or embedding analysis, full Feature 010 Finding management, advanced analytics, WebSockets/SSE, user cancellation, unbounded cloning, or arbitrary public lifecycle mutation.
