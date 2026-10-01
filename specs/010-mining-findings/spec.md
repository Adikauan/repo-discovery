# Feature Specification: Mining Findings

**Feature Branch**: `010-mining-findings`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User description: Introduce durable findings from repository mining rules, incremental commit-author validation, repository checkpoints, read APIs, and dashboard presentation, reusing the existing mining pipeline.

## Clarifications

### Session 2026-09-30

- Q: What should an empty allowed-author list mean? → A: It is an explicit empty allowlist: every commit with a valid author email is unauthorized and produces a finding after the repository baseline.
- Q: How should missing or malformed commit author emails be handled? → A: Produce one finding per affected commit; store no malformed raw email, set author email to null, and record a safe identity state of `missing` or `malformed`. Never infer identity from author name.
- Q: What severity should the Unauthorized Commit Author rule assign? → A: Use `warning` for every finding from this rule.
- Q: What happens when a commit range is larger than the per-repository processing limit? → A: Fail that RepositoryExecution with normalized code `commit_range_limit_exceeded`; persist no findings from the rejected range and leave the prior checkpoint unchanged. Default the configured limit to 1,000 commits per repository execution, with an allowed setting range of 1–10,000.

- Q: How large may the configured allowed-author list be? A: Limit it to 500 email entries, each at most 254 characters, to bound configuration and snapshot payloads; trim, validate, case-fold, deduplicate, and sort before persistence.
- Q: How is an empty/whitespace-only provider author email classified? A: Treat it as missing; a non-empty value that fails email validation is malformed. Neither raw malformed input nor whitespace-only text is retained.

## User Scenarios & Testing

### User Story 1 - Configure allowed commit authors (Priority: P1)

As a Mining Configuration owner, I can maintain the author email addresses allowed to contribute to repositories, so future executions evaluate commits against the policy that was in force when each execution began.

**Why this priority**: The deterministic rule needs an explicit policy and execution-time historical context.

**Independent Test**: Create or update a Monitoring Configuration with allowed emails, create an execution, then change the configuration and prove the execution retains its original allowed-email set.

**Acceptance Scenarios**:

1. **Given** a valid list containing mixed-case and whitespace-padded addresses, **When** it is saved, **Then** addresses are trimmed and compared case-insensitively and duplicates do not create distinct allowed identities.
2. **Given** an execution snapshot containing an allowed-email list, **When** the live configuration list changes, **Then** findings for the historical execution remain governed by the snapshot list.
3. **Given** an invalid configured address, **When** the configuration is saved, **Then** the request is rejected with normalized field feedback and no credential or provider data is exposed.

### User Story 2 - Detect unauthorized commit authors incrementally (Priority: P1)

As a user running a manual or scheduled mining execution, I want new commits after a repository's successful checkpoint evaluated by the Unauthorized Commit Author rule, so the system reports newly observed authors who are not on the execution's allowed list without repeatedly mining old history.

**Why this priority**: It delivers the core finding-producing value while bounding work to new repository history.

**Independent Test**: With a mocked repository HEAD and commit graph, prove the first successful execution establishes a baseline without historical findings, and the next execution creates findings only for new unauthorized commits and advances the checkpoint on success.

**Acceptance Scenarios**:

1. **Given** a repository with no checkpoint, **When** its first successful processing establishes the current branch HEAD, **Then** older commits create no findings and the checkpoint is persisted at that HEAD.
2. **Given** a reachable checkpoint and new commits, **When** the same shared mining pipeline processes the repository, **Then** each commit after the checkpoint through the current HEAD is examined once, allowed authors create no finding, and unauthorized authors create persisted findings.
3. **Given** a commit with a missing or malformed author email, **When** the rule evaluates it, **Then** one finding is persisted with a null author email and safe `missing` or `malformed` identity state; author name is not used.
4. **Given** manual and scheduled executions with equivalent snapshots and commit ranges, **When** they run, **Then** they apply the same rule, checkpoint, and finding semantics.

### User Story 3 - Inspect findings from an execution (Priority: P1)

As a user inspecting an execution dashboard, I can see the findings produced by that execution and their repository and commit context, so I can understand which author triggered the rule and where the finding came from.

**Why this priority**: Durable findings need to be discoverable through the established execution history workflow.

**Independent Test**: Seed zero, one, and multiple safe finding DTOs and verify the dashboard Findings section shows real records and honest empty, loading, and normalized error states.

**Acceptance Scenarios**:

1. **Given** an execution with persisted findings, **When** its Findings section is opened, **Then** findings are ordered deterministically and show rule, repository, safe summary, severity, commit hash, author email when valid/present, and timestamp.
2. **Given** an execution with no findings, **When** its Findings section is opened, **Then** the zero persisted counter and an honest empty state are shown without fabricated rows.
3. **Given** a finding belonging to a repository execution, **When** it is queried through execution or repository scope, **Then** its owning MiningExecution is derived from that RepositoryExecution and cannot be reassigned.

### User Story 4 - Preserve checkpoints and historical findings through failures (Priority: P1)

As a user relying on mining history, I want failed processing to leave the last successful checkpoint unchanged and existing findings immutable, so retries or later runs neither skip unprocessed commits nor rewrite prior results.

**Why this priority**: Advancing a checkpoint before durable findings are written could permanently lose detections.

**Independent Test**: Inject commit retrieval, rule, and finding persistence failures and prove the repository fails safely, the old checkpoint remains, other repositories continue, and previously persisted findings stay queryable.

**Acceptance Scenarios**:

1. **Given** a previously successful checkpoint, **When** commit retrieval, rule execution, or finding persistence fails, **Then** the repository fails, the checkpoint remains unchanged, and no partial count is reported as committed.
2. **Given** the checkpoint is not an ancestor of the current branch HEAD, **When** history is evaluated, **Then** the repository fails with a normalized history-rewrite error, creates no findings for that range, and does not reset the checkpoint.
3. **Given** a commit range exceeds the approved processing limit, **When** the repository is evaluated, **Then** the RepositoryExecution fails with `commit_range_limit_exceeded`, no findings from that range are persisted, and the checkpoint remains unchanged.
4. **Given** repeated processing or duplicate provider commit records for one repository execution, **When** findings are persisted, **Then** uniqueness constraints prevent duplicate logical findings.

## Edge Cases

- An empty allowed-email list means all valid commit author emails are unauthorized.
- Missing or malformed author emails produce one finding per commit with a null author email and safe identity state; raw malformed values are not retained and author name is never used as a substitute.
- The first repository execution establishes a baseline at the selected/default branch HEAD and does not analyze older commits.
- A branch with no prior checkpoint establishes its own baseline; checkpoints are isolated by Monitoring Configuration, stable GitLab project identity, and branch.
- A branch HEAD that no longer descends from the stored checkpoint is a history rewrite and fails safely without checkpoint advancement.
- A repository with no default branch follows Feature 008's safe repository failure behavior.
- Commit pagination must be complete; malformed or incomplete pages fail the repository rather than silently truncating the range.
- Commit-range safety limit overflow fails the repository with `commit_range_limit_exceeded`, persists no findings from that range, and does not advance its checkpoint.
- A checkpoint for one Monitoring Configuration must not affect another configuration analyzing the same GitLab project.
- A later allowed-email, scope, repository, branch, or schedule change does not alter existing execution snapshots or findings.
- Finding persistence failure rolls back findings, finding counters, and checkpoint advancement for that repository processing result.
- A repeated commit hash in provider pages is deduplicated before rule evaluation and persistence.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST persist a Finding produced by a mining rule and associate it with exactly one RepositoryExecution; the owning MiningExecution MUST be derived through that RepositoryExecution.
- **FR-002**: Findings MUST retain historical execution, repository, rule identity/version, severity, safe title and explanatory summary, commit hash, normalized author email when available, authored timestamp, and optional file path/line context when a rule provides it. For the initial rule, the summary is the finding explanation and a bounded commit-message summary is optional supporting context. Feature 010's commit-author rule MUST NOT fabricate file context.
- **FR-003**: Findings MUST be immutable historical detection records; this feature MUST NOT add triage statuses or mutation endpoints.
- **FR-004**: Monitoring Configuration MUST support at most 500 allowed commit-author email entries, each at most 254 characters, and validate entries as email addresses; edit behavior MUST follow existing configuration revision/ETag conventions.
- **FR-005**: Every newly created MiningExecution snapshot MUST capture the normalized allowed-email set used by its rules; manual and scheduled executions MUST use the same snapshot behavior. Credentials MUST NOT be included.
- **FR-006**: Allowed emails MUST be normalized by trimming surrounding whitespace and Unicode case-folding before comparison; duplicate normalized addresses MUST have set semantics. Author name MUST NOT be used for identity matching.
- **FR-007**: An empty allowed list MUST treat every valid author email as unauthorized. Missing or whitespace-only author emails, and malformed non-empty author emails, MUST produce a finding with null author email and safe identity state; raw malformed values MUST NOT be stored.
- **FR-008**: The Unauthorized Commit Author rule MUST be deterministic, non-AI, independently testable, and integrated through the existing Feature 008 MiningRule contract and repository processing pipeline.
- **FR-009**: Commit analysis MUST be incremental per Monitoring Configuration, stable GitLab project identity, and branch. The first successful processing without a checkpoint MUST store the current branch HEAD as a baseline and MUST NOT emit findings for earlier commits.
- **FR-010**: Later processing MUST examine commits strictly after the previous successful checkpoint and through the current branch HEAD, deduplicate commits by stable commit hash, and apply the execution snapshot's allowed-email set.
- **FR-011**: The system MUST advance a checkpoint only after commit retrieval, rule processing, finding persistence, and successful repository result persistence have succeeded atomically. Failure MUST preserve the previous checkpoint and MUST NOT report uncommitted findings.
- **FR-012**: Checkpoint identity MUST include Monitoring Configuration, stable GitLab project ID, and branch/reference. It MUST persist the last successfully processed commit hash and update timestamp; checkpoints from different configurations MUST be isolated.
- **FR-013**: If the stored checkpoint is not reachable from current branch HEAD, the repository MUST fail with a normalized safe history/checkpoint error, create no findings for the invalid range, and leave the checkpoint unchanged. Automatic checkpoint reset is prohibited.
- **FR-014**: Commit retrieval MUST use normalized commit models behind the GitLab integration boundary, handle all provider pages, and never expose raw provider DTOs to application or domain rules.
- **FR-015**: Commit processing MUST be bounded by the configured maximum commits per repository execution (default 1,000; allowed setting range 1–10,000). A larger range MUST fail with `commit_range_limit_exceeded`, persist no findings from that range, and retain the prior checkpoint.
- **FR-016**: A commit retrieval, validation, finding persistence, or checkpoint error for one repository MUST fail that RepositoryExecution safely and MUST NOT prevent other repositories in the same MiningExecution from processing.
- **FR-017**: Finding identifiers and uniqueness MUST prevent duplicate persistence of the same rule finding for a commit within its repository execution, including duplicate provider records and repeated persistence attempts.
- **FR-018**: RepositoryExecution.finding_count MUST equal the persisted findings owned by that RepositoryExecution; MiningExecution.finding_count MUST equal the persisted findings across its repository executions.
- **FR-019**: The Unauthorized Commit Author finding MUST use `warning` severity and include enough safe context to explain the detection without storing raw provider responses.
- **FR-020**: The system MUST provide read-only list APIs for findings scoped by MiningExecution and RepositoryExecution, plus read-only finding detail where specified by project API conventions; reads MUST return normalized not-found and safe error behavior.
- **FR-021**: Finding queries MUST have deterministic ordering and may provide only basic repository, rule, and severity filters; arbitrary query languages and mutation endpoints are out of scope.
- **FR-022**: The existing dashboard Findings section MUST display persisted findings and their rule, repository, path when applicable, commit context, author email when available, safe summary, severity, and timestamp; zero findings MUST remain distinct from unavailable detail data.
- **FR-023**: Findings from old and new executions MUST remain associated with the immutable execution that produced them; current configuration, allowed-email list, scope, schedule, branch content, or repository state MUST NOT be queried to reinterpret historical findings.
- **FR-024**: Manual and scheduled executions MUST run the same finding-producing rules through Feature 008; no schedule-specific mining path is permitted.
- **FR-025**: Commit history retrieval MUST not automatically retry authentication, authorization, malformed-response, or not-found failures; any retry behavior MUST reuse a bounded existing approved provider policy.
- **FR-026**: Commit message text persisted for finding context MUST be limited to 500 Unicode code points and stripped of control characters; provider responses, credentials, authorization headers, raw exceptions, and database internals MUST NOT be exposed in APIs or logs.
- **FR-027**: PostgreSQL constraints and transactions MUST protect checkpoint uniqueness, finding uniqueness, atomic counter/checkpoint behavior, and concurrent persistence as required by the approved data model.
- **FR-028**: No AI/LLM/SLM, embeddings, CodeBERT, semantic similarity, triage workflow, notifications, WebSockets, SSE, distributed workers, or new mining pipeline may be introduced.

### Key Entities

- **Finding**: Immutable detection record owned by one RepositoryExecution and attributed to a rule identity/version. Unauthorized Commit Author findings contain commit hash, normalized valid author email or null with a safe `author_email_state` of `missing` or `malformed`, authored timestamp, `warning` severity, safe summary, and bounded commit message summary.
- **MiningRuleResult**: Normalized output containing zero or more domain findings and rule execution facts; application orchestration persists it after rule execution.
- **RepositoryCheckpoint**: Last successful commit hash for a Monitoring Configuration, stable GitLab project, and branch.
- **ExecutionSnapshot**: Existing immutable execution context, minimally extended with normalized allowed author emails.
- **MonitoringConfiguration**: Existing configuration, minimally extended with the allowed author email list and existing update revision semantics.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The first successful processing of a repository with no checkpoint creates no findings from commits before the established baseline.
- **SC-002**: For each later successful execution, each commit in the eligible range is evaluated at most once, and each unauthorized valid author commit yields exactly one finding per rule version and RepositoryExecution.
- **SC-003**: In all injected repository failures before transaction commit, the prior checkpoint remains unchanged and no success count is added for unpersisted findings.
- **SC-004**: Repository and execution finding counters equal exact persisted Finding row counts after every completed or partially completed MiningExecution.
- **SC-005**: Processing never evaluates more commits for one repository execution than the configured maximum; exceeding it follows the explicit safe outcome and never skips an unprocessed range by checkpointing its HEAD.
- **SC-006**: Users can retrieve and understand each persisted finding from the existing execution dashboard with its repository and commit context, without a separate findings workflow.
- **SC-007**: Changing allowed emails after an execution does not change the snapshot or findings returned for that historical execution.

## Assumptions

- Monitoring Configuration is the owner-editable source for allowed author emails; configuration changes use existing create/update contracts and revision semantics.
- The allowed-list size, malformed/missing author, fixed severity, and range-overflow semantics are fixed in Clarifications.
- The repository default branch from Feature 008 is the analyzed branch for a repository execution; checkpoint identity is branch-specific.
- A new branch with no checkpoint establishes its own baseline rather than inheriting another branch's checkpoint.
- A validated setting bounds commits processed per repository execution; its default is 1,000 and its allowed range is 1–10,000.
- Findings are append-only and are retained according to existing execution/repository history retention; no automatic finding deletion is introduced.
- GitLab provider interactions remain mocked in normal automated tests; PostgreSQL is required for schema/uniqueness/concurrency validation.
