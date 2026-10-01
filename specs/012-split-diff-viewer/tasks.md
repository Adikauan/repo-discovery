---

description: "Dependency-ordered task list for Feature 012"
---

# Tasks: Split Diff Viewer

**Input**: Design documents from `specs/012-split-diff-viewer/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/split-diff-presentation.md`, `quickstart.md`

**Tests**: Required explicitly by Feature 012. Parser, renderer, integration, regression, and accessibility tests are included.

**Organization**: Tasks follow user-story priority and file ownership. Feature 011 API, GitLab, and persistence remain unchanged.

## Phase 1: User Story 1 - Compare a changed file side by side (Priority: P1)

**Goal**: Transform the normalized unified patch into a deterministic, accessible split Before/After presentation.

**Independent Test**: Pure parser and renderer tests prove line coordinates, row classification, positional pairing, hunk boundaries, safe truncation, and a readable split layout without API changes.

- [X] T001 [US1] Define the transient split-diff types in `src/features/executions/utils/splitDiffParser.ts`: result `success|error`, hunk `header`/`rows`, and row `type`, nullable old/new line numbers and content, plus nullable metadata text; do not add React or persisted/API fields (FR-003–FR-006, FR-016–FR-017).
- [X] T002 [US1] Add pure parser tests in `src/test/features/executions/split-diff-parser.test.ts` for context/add/remove, old/new start positions and counters, omitted counts, one/many hunks, file/no-newline markers, one-to-one and unequal positional replacement blocks, added/deleted sides, source whitespace, empty patch, malformed headers/counts, and final-hunk count shortfall only when `diffTruncated=true` (FR-003–FR-006, FR-017).
- [X] T003 [US1] Implement the pure unified patch parser in `src/features/executions/utils/splitDiffParser.ts`; classify source rows, advance independent counters, align adjacent removed/added blocks positionally per hunk, retain hunk and metadata rows outside source numbering, allow an incomplete final prefix only when Feature 011 marks `diffTruncated`, and return a safe error instead of guessed coordinates for other malformed patches (FR-003–FR-006, FR-017).
- [X] T004 [US1] Add renderer tests in `src/test/features/executions/split-diff-viewer.test.tsx` that inspect one paired replacement inside a single visual row container with old/new line numbers and content cells; cover both unequal replacement directions, removed/added empty-side cells, context, multiple hunks, labels, semantics, preserved whitespace, and horizontal scrolling (FR-002–FR-007, FR-015).
- [X] T005 [US1] Implement `src/features/executions/components/SplitDiffViewer.tsx` so every logical row is one shared four-column CSS Grid container (old number, old content, new number, new content), with aligned placeholders, independent fixed-width gutters, Before/After headings, monospace source, accessible add/remove markers, neutral context, and full-width hunk/metadata rows; keep simple row rendering private to this module (FR-002–FR-007, FR-015).

## Phase 2: User Story 2 - Open commit changes accessibly (Priority: P1)

**Goal**: Open the existing commit changes dialog from a compact accessible Difference icon while preserving the Feature 011 request and modal behavior.

**Independent Test**: Findings and icon render with no diff request; mouse/keyboard activation opens the same dialog, retrieves only by Finding ID, retains sidebar/metadata/states, and restores focus on close.

- [X] T006 [P] [US2] Extend `src/test/features/executions/finding-commit-diff.test.tsx` for supported/unsupported Finding action applicability, `Difference` icon accessible name and tooltip, mouse/keyboard activation, no eager fetch, same-dialog request by Finding ID, changed-file selection without repeat request, focus restoration, and existing metadata/loading/error/retry/completeness/binary/too-large/truncated behavior (FR-001, FR-008–FR-014, FR-016).
- [X] T007 [P] [US2] Extend `src/test/features/executions/execution-accessibility.test.tsx` for accessible Before/After labels, addition/removal semantics beyond color, sensible line-number announcements, keyboard file navigation and action activation, dialog title/focus behavior, and no accessibility regressions without changing reviewer-owned markers (FR-007, FR-011, FR-014–FR-015).
- [X] T008 [US2] Update `src/features/executions/components/ExecutionFindingsSection.tsx` as the sole dialog integration owner: preserve the Feature 011 flow and size the existing dialog to approximately 95vw by 90vh (capped at 1800px); keep title/Close available, a bounded 210–280px sidebar beside a flexible split viewer, and internal two-axis diff scrolling. Verify the sidebar and diff are side by side and the diff is not vertically stacked (FR-001, FR-008–FR-015, FR-016–FR-017).

## Phase 3: Polish and Cross-Cutting Validation

- [X] T009 Run parser, renderer, Finding interaction, viewport/layout and accessibility tests, the complete frontend test suite, and production build; confirm no API, GitLab retrieval, persistence, migration, or Feature 011 semantic change. Validation: 43 frontend test files / 181 tests passed; `tsc -b` passed; production Vite build passed with a temporary config loader workaround because the default config loader hits Windows `spawn EPERM`. (FR-016, SC-001–SC-006).

## Dependencies and Execution Order

### Phase dependencies

- T001 precedes T002 and T003; T002 precedes T003.
- T003 precedes T004/T005 integration expectations; T004 precedes T005 implementation.
- T006 and T007 are separate test files and may proceed in parallel after T005.
- T008 depends on T003, T005, T006, and T007; it is the only task that edits `ExecutionFindingsSection.tsx`.
- T009 depends on every implementation and test task.

### Parallel execution examples

```text
After parser types and parser tests are established:
  T003 implements the parser; it owns the parser module after T001.

After T003:
  T004 establishes viewer expectations, then T005 builds the viewer.

After T005:
  T006 and T007 may proceed in parallel because they edit different test files.

After T006 and T007:
  T008 integrates the viewer and icon into the existing dialog; no task runs beside it on that file.
```

The existing changed-file sidebar remains in `ExecutionFindingsSection.tsx`; no separate sidebar file is required by this change. Do not split files solely to parallelize.

## Requirement-to-Task Traceability

| Requirement | Tasks |
|---|---|
| FR-001: retain dialog, metadata, sidebar, states and close behavior | T006, T008 |
| FR-002–FR-007: split sides, line rules, alignment, hunks, visual/accessibility semantics | T001–T005, T007 |
| FR-008: file selection updates view without another request | T006, T008 |
| FR-009–FR-010: existing file states/completeness semantics | T006, T008 |
| FR-011–FR-014: applicable icon, tooltip, on-demand, keyboard and focus | T006–T008 |
| FR-015: responsive viewport-sized dialog and bounded split view | T004–T005, T007–T008 |
| FR-016: frontend-only/no endpoint or persistence change | T001, T003, T008–T009 |
| FR-017: safe malformed/truncated patch handling | T001–T003, T006, T008 |
| SC-001–SC-002: correct split output and coordinates | T001–T005, T009 |
| SC-003–SC-004: request boundary and Feature 011 preservation | T006, T008–T009 |
| SC-005–SC-006: accessibility and responsive containment | T004–T009 |

## Implementation Strategy

1. Define the view model, write parser tests, and implement the parser (T001–T003).
2. Write renderer expectations and implement the split viewer (T004–T005).
3. Add interaction and accessibility coverage in parallel on distinct files (T006–T007), then integrate the existing dialog once (T008).
4. Run full validation (T009). No backend changes or migration are expected.
