# Data Model: Split Diff Viewer

Feature 012 adds no persisted entity or database schema. It transforms the existing Feature 011 normalized commit-diff response into transient presentation values.

## SplitDiffResult

- `status`: `success | error`.
- `hunks`: ordered `SplitDiffHunk[]` when status is success.
- `error`: safe local parse error code when status is error; no provider exception text.

## SplitDiffHunk

- `header`: original unified hunk header text, displayed as a separator.
- `rows`: ordered source or informational rows belonging to this hunk.

## SplitDiffRow

- `type`: `context | added | removed | modified | metadata`.
- `oldLineNumber`: positive integer or null; null for rows with no old-side source.
- `oldContent`: original source text without its one-character unified marker, or null.
- `newLineNumber`: positive integer or null; null for rows with no new-side source.
- `newContent`: original source text without its one-character unified marker, or null.
- `metadataText`: informational hunk metadata such as the no-newline marker; populated only for `metadata` rows.

`modified` is a presentation-only pairing of adjacent removed/added source lines. It does not alter persisted GitLab change type or patch content. Empty sides are represented by null content and line number; the renderer supplies an accessible empty placeholder. For an explicitly `diffTruncated` patch, a short final hunk is a valid partial prefix and included rows use only coordinates derivable from the hunk header; other malformed/count-inconsistent patches return an error result. These values are recalculated from the selected file patch and are never persisted or cached beyond ordinary component memoization.

## Existing Input

`FindingDiffFile` from Feature 011 remains authoritative for path, provider change type, patch availability, `diffTruncated`, binary, collapsed, and too-large states. `FindingDiffResponse.filesCompleteness` retains the `complete | truncated | unknown` semantics and is not modified by this frontend model.
