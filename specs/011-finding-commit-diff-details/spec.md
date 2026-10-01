# Feature Specification: Finding Commit Diff Details

**Feature Branch**: `011-finding-commit-diff-details`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User description: Create Feature 011 - Finding Commit Diff Details.

## User Scenarios & Testing

### User Story 1 - Inspect an unauthorized commit (Priority: P1)

As a user reviewing an Unauthorized Commit Author Finding, I can open its details and inspect the associated commit metadata, changed files, and each file's diff.

**Why this priority**: This is the core value of the feature: understanding the actual code changes associated with a detected commit.

**Independent Test**: Open a commit-based finding in the Execution Dashboard and verify commit metadata, changed-file entries, and a selected file's line-oriented diff.

**Acceptance Scenarios**:

1. **Given** a commit-based Finding in the Findings section, **When** the user activates “View diff”, **Then** a detail dialog opens and loads the commit associated with the persisted Finding.
2. **Given** a loaded commit detail, **When** the user selects a changed file, **Then** its diff is presented as readable monospace lines with added, removed, and context distinctions where supplied.
3. **Given** the provider identifies a rename or deletion, **When** the file list is displayed, **Then** the old/new paths and available change type remain visible.

### User Story 2 - Understand unavailable or partial diff data (Priority: P1)

As a user, I can distinguish binary files, provider-truncated diffs, application-bounded results, and retrieval errors without losing access to the historical Finding.

**Why this priority**: The feature must communicate limits honestly while retaining the persisted detection record.

**Independent Test**: Supply binary, collapsed, truncated, oversized, and failed provider responses and verify accessible explanatory states, bounded output, and retry behavior.

**Acceptance Scenarios**:

1. **Given** a changed binary file with no text patch, **When** details load, **Then** the file remains listed and textual diff is described as unavailable.
2. **Given** GitLab marks a patch collapsed/truncated/too large, **When** details load, **Then** the UI preserves that limitation indicator.
3. **Given** the diff request fails, **When** the response is shown, **Then** safe normalized feedback and retry are available while the Finding remains visible.

### User Story 3 - Securely retrieve only the Finding's commit diff (Priority: P1)

As a user, I can request diff details without being able to select arbitrary GitLab projects, commits, instances, or credentials.

**Why this priority**: The API must not become a generic provider proxy, and historical instance identity must be respected.

**Independent Test**: Call the Finding diff endpoint while attempting to supply arbitrary lookup identifiers and verify lookup is derived exclusively from persisted Finding and execution context.

**Acceptance Scenarios**:

1. **Given** a valid Finding, **When** its diff is requested, **Then** repository identity, commit hash, and GitLab instance are derived from persisted execution data.
2. **Given** a credential is unavailable or the active instance differs from the execution snapshot, **When** the diff is requested, **Then** the API returns a normalized safe error and keeps the Finding metadata available.
3. **Given** a non-commit Finding or missing Finding, **When** the endpoint is called, **Then** it returns the normalized not-found or not-applicable result without arbitrary provider lookup.

## Edge Cases

- Finding is missing, does not represent a commit, lacks a commit hash, or has no usable repository identity.
- Associated repository or commit is missing, forbidden, unavailable, or times out.
- Current GitLab connection does not match the GitLab instance captured by the execution.
- Commit has no changed files, contains binary files, or includes deleted/renamed files.
- GitLab reports collapsed, truncated, or too-large patches.
- File count, per-file diff, or cumulative textual diff exceeds the application limits; bounded metadata such as file paths remains present where possible.
- GitLab does not provide enough pagination/limit information to prove whether its changed-file list is complete.
- Diff payload contains long lines or many files on a narrow viewport.
- User retries after a normalized error, closes the dialog during loading, or opens the same finding again.
- Provider returns malformed diff data or partial data for one file while other files are usable.

## Requirements

### Functional Requirements

- **FR-001**: Each displayed Unauthorized Commit Author Finding MUST offer an action to inspect its associated commit changes.
- **FR-002**: The detail view MUST display repository identity and persisted commit hash, author name when available, author email, commit timestamp, and message summary when available.
- **FR-003**: The detail view MUST list changed files and expose old path, new path, and change type only when available from the provider.
- **FR-004**: Each changed file MUST present its own line-oriented diff, distinguishing added, removed, and context lines where returned; added/removed meaning MUST not rely on color alone.
- **FR-005**: The API MUST derive repository identity, commit hash, and GitLab instance context from the persisted Finding, RepositoryExecution, and execution snapshot. A caller MUST NOT select arbitrary project IDs, commits, URLs, or credentials.
- **FR-006**: The provider adapter MUST normalize GitLab responses before they reach application/API contracts; raw provider DTOs MUST remain within infrastructure.
- **FR-007**: Diff retrieval MUST use the repository and commit hash associated with the historical Finding, never current HEAD or a caller-supplied replacement commit.
- **FR-008**: Historical execution GitLab instance identity MUST be validated before using stored repository identity. A mismatch MUST fail safely without reinterpreting IDs.
- **FR-009**: Credential resolution MUST reuse secure existing handling. Credentials and authorization headers MUST NOT be persisted in Findings or returned/logged.
- **FR-010**: Provider, credential, authorization, timeout, not-found, unsupported, and malformed-response errors MUST use normalized safe error handling. Diff errors MUST NOT invalidate or delete the Finding.
- **FR-011**: Diff output MUST be bounded by at most 100 changed-file entries, at most 256 KiB of UTF-8 diff text per file, and at most 2 MiB of cumulative UTF-8 diff text per response. `total_diff_bytes` MUST equal the sum of UTF-8 byte lengths of normalized textual `diff` fields actually included. This budget MUST NOT include JSON syntax/serialization overhead, field names, commit metadata, paths, booleans, timestamps, or other normalized metadata. Changed-file paths and repository display paths MUST be bounded to 4096 UTF-8 bytes each with explicit path-truncation indicators; repository name MUST be bounded to 200 UTF-8 bytes. Commit metadata MUST use existing Finding bounds: commit hash up to 64 hexadecimal characters, author email up to 254 characters, author name up to 200 Unicode code points, and message summary up to 500 Unicode code points.
- **FR-012**: Provider-reported collapsed, truncated, or too-large states MUST be preserved in the normalized result and UI.
- **FR-012a**: The changed-file list MUST include `filesCompleteness` with exactly `complete`, `truncated`, or `unknown`. `complete` means completeness is reliably established; `truncated` means the provider or application has evidence that additional changed files were omitted; `unknown` means the provider response does not establish either condition. The system MUST NOT convert `unknown` to either other state without evidence. Per-file patch states MUST remain independent from list completeness.
- **FR-013**: Binary changed files MUST remain listed; when no textual diff exists, the UI MUST state that the text diff is unavailable without failing other files.
- **FR-014**: The Findings list MUST NOT eagerly fetch diffs. The client MUST fetch only after explicit user activation and MUST not issue uncontrolled duplicate requests.
- **FR-015**: The detail interaction MUST provide accessible dialog semantics, title, focus entry/return, keyboard close and file selection, and perceivable loading/error/retry feedback.
- **FR-016**: The diff presentation MUST remain usable on narrow screens, with responsive dialog sizing, scrollable content, and horizontal scrolling for long lines.
- **FR-017**: The system MUST retrieve commit diffs on demand and MUST NOT persist full patches; if the commit becomes unavailable from GitLab later, the Finding metadata remains available and the diff request returns a normalized safe error.
- **FR-018**: The feature MUST remain read-only and MUST NOT implement code review comments, approvals, reverts, merge requests, triage, new detection rules, or AI analysis.
- **FR-019**: The detail API MUST expose normalized commit and changed-file data only, never raw GitLab payloads or internal persistence structures.

### Key Entities

- **Finding**: Existing historical Unauthorized Commit Author detection record, including its persisted commit identity and parent RepositoryExecution.
- **CommitDiffDetails**: Normalized read result associating a Finding and repository with commit metadata and bounded changed-file diff entries.
- **ChangedFileDiff**: Normalized per-file paths, optional provider-supported change type, textual diff when available, and explicit binary/truncation/availability indicators.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A user can open a commit-based Finding and identify its repository, commit, author, timestamp, changed files, and selected file diff without leaving the execution dashboard.
- **SC-002**: Opening the Findings section alone issues zero diff requests; an explicit detail action issues a request for only that Finding.
- **SC-003**: No request can cause provider lookup using a project, commit, instance URL, or credential supplied by the client.
- **SC-004**: Responses contain at most 100 changed-file entries, each returned `diff` is at most 256 KiB UTF-8, and the sum of UTF-8 bytes of all returned `diff` fields is at most 2 MiB. File paths and existing metadata use their own bounds. The diff-text budget excludes JSON/HTTP serialization and metadata. Every known omission is marked; changed-file list completeness is reported as `complete`, `truncated`, or `unknown` according to available evidence.
- **SC-005**: Binary, deleted, renamed, and provider-limited files remain represented honestly; list completeness is exposed as `complete`, `truncated`, or `unknown`, with no warning for complete, a factual omitted-files warning for truncated, and an informational uncertainty message for unknown.
- **SC-006**: Keyboard and screen-reader users can open, operate, and close the detail dialog, with focus returned to its trigger.
- **SC-007**: Safe retrieval failures leave the Finding and its historical metadata available.

## Assumptions

- Feature 010 persists Unauthorized Commit Author Finding commit identity and RepositoryExecution association needed for lookup.
- The execution snapshot contains the GitLab instance identity/fingerprint and configuration association needed to validate the historical provider connection.
- The existing GitLab client and secure credential services can be extended with a normalized commit-diff operation.
- The initial UI is a dialog opened from the Findings section; planning may refine its internal layout without creating a separate code review application.
- Diff bounds are centrally defined as in FR-011. The provider may not expose completeness evidence; in that case the response reports `unknown`.
- Commit diffs are fetched on demand and not persisted; no database migration or diff persistence model is required.

## Clarifications

### Session 2026-09-30

- Decision: Use Option A, fetch commit diffs on demand and do not persist patches. This minimizes database growth and avoids coupling diff capture to mining. Historical Finding metadata remains available, while the diff may become unavailable if GitLab no longer serves the commit.

