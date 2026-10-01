# Feature Specification: Split Diff Viewer

**Feature Branch**: `012-split-diff-viewer`  
**Created**: 2026-09-30  
**Status**: Draft  
**Input**: User description: "Create Feature 012 - Split Diff Viewer. Improve the existing Finding commit diff dialog with side-by-side before/after rendering and a representative accessible Material UI icon action, while preserving Feature 011 behavior and scope."

## User Scenarios & Testing

### User Story 1 - Compare a changed file side by side (Priority: P1)

As a user reviewing an Unauthorized Commit Author Finding, I want to compare the previous and new versions of a selected changed file side by side, so I can understand the commit's changes and their source line locations.

**Why this priority**: Side-by-side comparison is the primary value of this feature.

**Independent Test**: Open a commit diff containing context, additions, removals, replacements, and multiple hunks; select files from the existing sidebar and verify both sides, line numbers, row alignment, and hunk separation.

**Acceptance Scenarios**:

1. **Given** the existing commit changes dialog contains a selected text diff, **When** the user views it, **Then** the old version appears on the left and the new version on the right with independent line numbers and accessible Before/After labels; every logical `SplitDiffRow` appears exactly once as one shared horizontal comparison row, never as independently flowing Before and After lists.
2. **Given** a hunk contains context lines, **When** it is displayed, **Then** each context line appears on both sides with the corresponding old and new line numbers.
3. **Given** adjacent removed and added lines in a hunk, **When** they are displayed, **Then** they are paired by position as modified rows without semantic line matching; excess lines remain aligned with an empty opposite side.
4. **Given** a patch contains multiple hunks, **When** it is displayed, **Then** each hunk header appears as a separator and does not consume a source line number.
5. **Given** a user selects another file in the existing left sidebar, **When** the selection changes, **Then** that file's split diff is shown without another commit-level diff request.
6. **Given** a binary, oversized, truncated, empty, or malformed patch is selected, **When** the viewer processes it, **Then** the existing Feature 011 state remains honest and safe rows or a safe rendering error are shown without fabricated source data.
7. **Given** the changed-file list completeness state is `truncated` or `unknown`, **When** the dialog is displayed, **Then** the existing factual warning or informational message is preserved without reinterpreting the state.

### User Story 2 - Open commit changes accessibly (Priority: P1)

As a user browsing findings, I want a compact, recognizable and accessible action for opening commit changes, so I can reach the existing dialog quickly with a mouse or keyboard.

**Why this priority**: The viewer must remain discoverable and operable from the established Findings workflow.

**Independent Test**: Load Findings and verify no diff request occurs; verify a supported finding has an accessible icon action with tooltip, keyboard activation opens the existing dialog, and closing restores focus to the same action.

**Acceptance Scenarios**:

1. **Given** a Finding supports commit diff inspection, **When** the Findings list is displayed, **Then** its row exposes a compact Material UI difference icon button with an accessible name and supplementary tooltip.
2. **Given** a supported Finding is listed, **When** the user activates its icon by mouse or keyboard, **Then** the existing dialog opens and retrieves the diff on demand using only the Finding ID.
3. **Given** the Findings list is initially loaded, **When** no diff action is activated, **Then** no commit diff request is made.
4. **Given** the dialog is closed, **When** focus returns to the Findings list, **Then** focus is restored to the triggering icon button.
5. **Given** a Finding does not support commit diff inspection, **When** its row is shown, **Then** it has no active diff action.

### Edge Cases

- Hunk headers may omit line counts; an omitted count means one source line for standard unified hunk syntax.
- File marker lines (`---` and `+++`) and the no-newline marker are metadata and never increment source line counters.
- An added file has no old-side source rows; a deleted file has no new-side source rows.
- Unequal replacement blocks leave the excess old or new rows paired with an empty opposite side.
- Long lines and paths must not widen the application layout; diff content may scroll horizontally within the dialog.
- Narrow screens retain both sides and the sidebar; a unified-mode toggle is not part of this feature.

## Requirements

### Functional Requirements

- **FR-001**: The existing Finding commit changes dialog MUST retain commit metadata, the changed-file sidebar, the selected-file detail region, loading/error/retry states, and its close action.
- **FR-002**: For a selected textual patch, the detail region MUST show the prior version on the left (Before) and new version on the right (After).
- **FR-003**: The split representation MUST render each logical `SplitDiffRow` exactly once in a shared horizontal row containing the old line number, old content, new line number, and new content. It MUST NOT render the Before and After sides as independent vertical lists. Each side MUST keep an aligned line-number and content cell; when a side has no source line, both empty cells MUST remain in that row as alignment placeholders. Line numbers MUST be independent and MUST NOT be fabricated.
- **FR-004**: Context lines MUST appear on both sides and increment both line counters; removed lines MUST appear only on the old side and increment only the old counter; added lines MUST appear only on the new side and increment only the new counter.
- **FR-005**: Adjacent removal/addition blocks within a hunk MUST be aligned by position as modified rows; excess lines MUST remain paired with empty opposite-side placeholders. No semantic or AI line matching is allowed.
- **FR-006**: The patch transformation MUST support standard unified hunk headers, multiple hunks, omitted hunk counts, file marker metadata, and no-newline markers. Metadata MUST NOT be displayed as source lines or increment source counters.
- **FR-007**: The viewer MUST preserve patch text and whitespace, use monospace line-oriented presentation, and distinguish added, removed, context, and hunk rows through both visual treatment and accessible text/semantics.
- **FR-008**: The selected file's split representation MUST update when the user chooses a different item in the existing left sidebar; switching files MUST NOT refetch the already-loaded commit-level diff.
- **FR-009**: Added, deleted, renamed, modified, binary, oversized, truncated, empty, and malformed patch cases MUST be represented according to Feature 011's normalized response and safe UI states. The viewer MUST NOT fetch raw content as a workaround or fabricate source data.
- **FR-010**: The changed-file list completeness values `complete`, `truncated`, and `unknown` MUST retain their Feature 011 meaning and existing user communication.
- **FR-011**: The Finding action for supported commit-based findings MUST be a compact Material UI icon button representing differences, preferring the existing `Difference` icon when available. It MUST have an accessible name and a supplementary tooltip.
- **FR-012**: The diff action MUST be available only for findings supported by existing Feature 011 applicability rules. It MUST open the existing dialog and use Finding ID as the only frontend lookup identity.
- **FR-013**: Loading the Findings list or displaying the icon MUST NOT request diff data. The existing on-demand request occurs only after the user activates the action.
- **FR-014**: Keyboard users MUST be able to focus and activate the icon, navigate the file sidebar, close the dialog, and have focus restored to the triggering icon.
- **FR-015**: The existing Commit changes dialog MUST use enough desktop viewport space for side-by-side comparison (approximately 95vw wide, capped at a large desktop width, and approximately 90vh high) while remaining bounded by the viewport. The changed-file sidebar MUST remain a practical bounded width and the diff region MUST use the remaining flexible space. Dialog title and close action MUST remain usable while its content area provides vertical and horizontal scrolling without widening the dashboard. At narrow viewports the Before and After sides MUST remain side by side and may scroll horizontally; they MUST NOT stack or switch to unified mode.
- **FR-016**: Diff parsing and rendering MUST be frontend-only and consume Feature 011 normalized diff responses. The feature MUST NOT add a diff endpoint, alter retrieval/security/limit/completeness semantics, persist diffs, add migrations, or change finding detection.
- **FR-017**: A malformed patch MUST fail safely without crashing the dialog; Finding and commit metadata MUST remain available, and no unverified line numbers may be shown. If Feature 011 marks a patch `diffTruncated`, a source-count shortfall at the end of the final hunk MUST be treated as an expected incomplete prefix: render only rows with positions derivable from that hunk header and retain the truncation indicator.

### Key Entities

- **Normalized Commit Diff**: Feature 011 response containing commit metadata, changed files, per-file patch text and status indicators, and changed-file-list completeness.
- **Split Diff Row**: A frontend presentation value with a row type, optional old/new line numbers, and optional old/new source content; it is derived from a normalized patch and is not persisted.
- **Changed File**: A normalized file entry from Feature 011, retained in the existing sidebar and associated with the selected patch.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Every supported text diff in the feature's standard patch cases presents old and new content in separately labeled sides with independently correct line numbers, and each logical comparison is one visual row container holding both sides and both line numbers.
- **SC-002**: Context, additions, removals, positional replacement blocks, and multiple hunks are represented without line-number drift in all specified parser scenarios.
- **SC-003**: Findings list loading and file switching after the commit diff response is loaded cause zero additional commit-diff requests; opening the diff action causes one on-demand request for that Finding.
- **SC-004**: All existing Feature 011 completeness, binary, oversized, truncation, loading, safe error, and retry states remain available and no diff persistence or migration is introduced.
- **SC-005**: The diff action and dialog can be operated by keyboard, provide accessible names for Before/After and added/removed semantics, and restore focus to the triggering action on close.
- **SC-006**: At desktop and narrow representative viewport sizes, the existing dialog uses approximately 95vw by 90vh (bounded by a large desktop maximum and the viewport), keeps the sidebar beside a flexible diff region, and contains long lines in its own scrollable area without horizontal overflow in the dashboard page.

## Assumptions

- Feature 011's normalized patch text follows standard unified diff syntax for the supported cases.
- Deterministic positional pairing of adjacent removed/added lines is sufficient; word-level and semantic line matching are excluded.
- Existing Material UI packages provide the preferred Difference icon; if unavailable, an already-installed Material icon with comparison semantics may be selected during planning.
- Existing Feature 011 normalized API data is sufficient; if planning discovers otherwise, the smallest safe contract gap must be documented before any backend change is proposed.
- The existing dialog and test/accessibility tooling are reused; no new frontend framework, icon package, persistence, or backend retrieval flow is needed.

## Out of Scope

- Unified/Split mode toggle, word-level highlighting, syntax highlighting, semantic matching, code review comments, inline threads, approvals, rejections, finding triage, commit revert, merge request creation, arbitrary GitLab browsing, diff persistence, new diff endpoints, and AI/LLM/SLM analysis.
