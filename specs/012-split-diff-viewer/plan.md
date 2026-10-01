# Implementation Plan: Split Diff Viewer

**Branch**: `012-split-diff-viewer` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

## Summary

Replace the existing unified text patch in the Feature 011 Finding dialog with a frontend-only parser and split before/after renderer. Keep the existing Finding ID diff request, commit metadata, changed-file sidebar, completeness/errors, and dialog lifecycle. Replace the text action with an accessible Material UI Difference icon button. No backend, API, persistence, migration, or dependency changes are planned.

## Technical Context

**Language/Version**: TypeScript 5.x, React 19 (repository package versions)
**Primary Dependencies**: Existing React, Material UI, `@mui/icons-material`, React Testing Library, Vitest, jsdom, axe-core; no new dependencies.
**Storage**: None; parsed rows are ephemeral frontend presentation data.
**Testing**: Vitest, React Testing Library, existing axe-core accessibility tests, and `npm run build`.
**Target Platform**: Existing browser execution dashboard.
**Project Type**: Frontend feature within the existing full-stack web application.
**Performance Goals**: Parse only the selected file's bounded normalized patch; memoize the parse by patch input; do not add network requests for file selection.
**Constraints**: Consume the Feature 011 response as-is. Preserve patch source text and Feature 011 completeness/limit/error meanings. No API/GitLab changes, persistence, migration, syntax highlighting, or line matching beyond positional pairing.
**Scale/Scope**: One existing Finding dialog, a pure parser, split renderer, and relevant frontend tests.

## Constitution Check

- **Clean Architecture / responsibility**: Pass. Patch-to-row transformation is a pure UI presentation utility; it does not own mining or provider rules.
- **Domain rule ownership**: Pass. Finding applicability and commit-diff retrieval remain owned by Feature 011.
- **Explicit contracts**: Pass. Consume the current normalized Feature 011 response; define only an internal typed parser result, with no public contract change.
- **External integration boundary**: Pass. No GitLab interaction is added or moved into the frontend.
- **Secure by construction**: Pass. Finding ID remains the only frontend lookup input; no credential or provider identifiers are introduced.
- **Immutable history**: Pass. No persisted finding or execution data changes.
- **One controlled pipeline / lifecycle**: Pass. Mining and scheduling are untouched.
- **Migration-managed persistence**: Pass. No data is persisted and no migration is needed.
- **Risk-based verification**: Pass. Parser boundaries, line numbering, dialog interactions, no-eager-fetch, keyboard/focus, and accessibility are covered.
- **Reusable accessible UX**: Pass. Reuse the existing MUI dialog/sidebar and established accessible dialog behavior.
- **Incremental simplicity**: Pass. One dependency-free pure parser and one focused renderer; no new package or alternative diff mode.

No constitution exception is requested.

## Research Decisions

See [research.md](research.md). The parser consumes standard unified patch text returned by Feature 011. It parses hunk headers, models source rows, pairs consecutive remove/add runs by position, and treats metadata as non-source rows. Invalid hunk accounting fails safely rather than fabricating coordinates. The existing `Difference` icon is present in the installed Material Icons package.

## Visual Reference

Use [`references/7e81efbe-77df-480d-8243-df8ff5cb1b3b.png`](references/7e81efbe-77df-480d-8243-df8ff5cb1b3b.png) as a UX/layout reference only. It informs the existing modal shell, commit metadata at the top, left changed-file sidebar, selected-file emphasis, visible file change type, side-by-side Before/After regions, independent line-number gutters, neutral context, distinct additions/removals, hunk separators, and monospace source presentation. The reference is lower priority than `spec.md` and adds no functional requirements. Elements visible only in the image (copy-path control, avatar, and aggregate +/− counts) are not part of this feature.

## Design

### Parser boundary and semantics

Add a pure TypeScript utility under `src/features/executions/utils/` with normalized types in the same feature. It accepts one normalized patch string and returns a discriminated success/error result. A successful result contains ordered hunks and rows; it performs no React, DOM, API, or provider work.

Each hunk starts old/new counters from its header. An omitted hunk count means one. Context increments both counters; removal increments only old; addition increments only new. File headers outside hunks and the no-newline marker are metadata and do not increment counters. Inside a hunk, prefix classification takes precedence, so source content that begins with additional `+` or `-` characters remains source content after removing the one unified-diff marker.

Within a hunk, collect a consecutive run of removals and immediately following additions; pair entries by index into `modified` rows and leave the excess side empty. Unpaired removals or additions remain single-sided rows. Context or metadata closes a pending run. Hunk headers are separate visual separators and never source rows. Validate that parsed source-row counts agree with declared hunk counts. When Feature 011 marks the patch `diffTruncated`, a count shortfall at the final end of the available patch is an expected partial prefix: render only the lines whose positions follow from the hunk header and preserve the existing truncation indicator. Any other malformed header/count mismatch returns a safe parse error and renders no guessed line numbers. Empty/absent patches use the existing honest empty state.

### Split renderer, modal responsibilities, and icon action

Keep `ExecutionFindingsSection` as owner of the Finding action and existing Commit changes dialog unless project conventions justify further extraction. Its logical responsibilities are: FindingDiffAction (compact icon, accessible name, tooltip, open existing dialog), CommitChangesDialog (title, metadata, loading/error/retry/close/focus), and ChangedFilesSidebar (file list, change type, selected state, keyboard navigation). Preserve the left sidebar as the primary file navigation; selecting a file updates only the selected-file presentation and never repeats the commit-level request.

Add a focused `SplitDiffViewer` component that receives parsed hunks and renders labeled Before/After sides with independent fixed-width line-number gutters, monospace preserved source, visible `+`/`-` markers and accessible added/removed labels. Each parsed `SplitDiffRow` MUST map to exactly one DOM row container with a shared four-column CSS Grid: old line number, old content, new line number, and new content. The old and new cells MUST be children of that same row container; they MUST NOT be separate vertically flowing lists. A missing side still gets both of its empty grid cells. Context is neutral; the old/removal cells use removal treatment; the new/addition cells use addition treatment; hunk separators span the viewer width and are followed by the same four-column row structure. This shared-row grid is the synchronization mechanism across every hunk.

Size the existing MUI dialog to approximately 95vw wide (capped at a large desktop width such as 1800px) and 90vh high, bounded by the viewport. Keep the dialog title and bottom Close action outside the scrolling content region. The content region owns a fixed practical sidebar (roughly 210–280px) beside a flexible diff region. The right diff viewport owns vertical and horizontal overflow; source rows remain non-wrapping so long lines scroll inside the dialog. The changed-file list owns its vertical overflow independently. At narrow widths retain the sidebar and the two split sides, using the diff viewport's horizontal scroll rather than stacking Before and After or widening the page.

The data flow is: Findings list loads without a diff request; user activates the supported Finding's Difference IconButton; Feature 011 fetches by Finding ID; the existing dialog holds the normalized response; the sidebar selects one file; a memoized pure parser transforms only that file's patch plus its `diffTruncated` flag; `SplitDiffViewer` renders the rows. Preserve current loading, safe error/retry, focus restoration, file completeness, binary/too-large/collapsed and empty states. The accessible name remains “View commit diff”; tooltip is supplementary. Use the existing theme palette and contrast conventions, not light-only hardcoded colors.

The parser result is an internal frontend view model. Hunk/header/row parsing stays outside React. A `modified` row is only positional pairing; its old cell retains removal semantics and its new cell retains addition semantics. Expose line numbers meaningfully without causing excessive screen-reader repetition. Hunk/row subcomponents may remain private in `SplitDiffViewer.tsx`; do not create files solely to mirror the mock or fragment simple rendering.

### Failure and existing states

Binary, too-large, collapsed, missing-text and file-list-completeness states remain handled by current dialog logic before rendering the parser output. A per-file `diffTruncated` patch still parses its available prefix and retains the existing truncation notice. A parser error displays a localized safe rendering error in the selected-file panel; commit metadata, sidebar, dialog, and Finding remain available. No raw provider diagnostic text is introduced.

### Source Structure

```text
src/features/executions/
├── components/
│   ├── ExecutionFindingsSection.tsx   # existing dialog, icon action and split viewer integration
│   └── SplitDiffViewer.tsx            # accessible old/new rendering
└── utils/
    └── splitDiffParser.ts             # pure unified patch parser and result types

src/test/features/executions/
├── split-diff-parser.test.ts          # pure parser cases
├── split-diff-viewer.test.tsx         # row semantics, labels, layout
├── finding-commit-diff.test.tsx       # icon, sidebar, dialog, existing states
└── execution-accessibility.test.tsx   # integrated accessibility regression
```

No backend or API files are in scope.

## Testing Strategy

1. Parser unit tests cover context/add/remove, a `-old`/`+new` pair as one `modified` row, positional replacements (both unequal directions), multiple hunks, line counters, omitted counts, file/no-newline metadata, added/deleted files, empty input, malformed headers/counts, and source preservation.
2. Renderer tests inspect the DOM structure: each logical row is one shared CSS Grid container with four cells, paired old/new content is inside that same container, and empty-side placeholders preserve alignment. Also verify Before/After names, hunk separators, accessible addition/removal semantics, monospace/whitespace, scrolling, and the bounded wide dialog/sidebar/flexible-diff layout.
3. Integration tests retain the changed-file sidebar and Feature 011 states; test `Difference` icon and tooltip/accessible name, keyboard open/close/focus return, selection without repeat API request, and no eager fetch.
4. Run targeted frontend tests, accessibility assertions, complete frontend test suite, and production build. No backend tests or PostgreSQL checks are required because no backend or persistence behavior changes.

## Operational Notes

The dialog remains the existing Feature 011 interaction. It continues to retrieve a bounded normalized patch on demand and does not cache or persist parsed output. No deployment or configuration change is needed.

## Complexity Tracking

No constitution violations, new dependencies, endpoints, migrations, or storage. The parser and renderer are isolated because each has independently testable responsibility and the parser can be reused if a later UI requires the same split representation.
