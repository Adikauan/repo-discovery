# Split Diff Presentation Contract

This is an internal frontend presentation contract. It does not change Feature 011 HTTP/API contracts.

## Input

The existing `FindingDiffFile.diff` normalized unified patch string plus existing file-state indicators. The dialog continues to request `/findings/{findingId}/diff` on explicit open only.

## Parser output

- A discriminated result: parsed hunks or a safe parse error.
- Hunk headers and metadata are not source rows and do not increment counters.
- Source rows expose independent old/new line numbers and content.
- Adjacent removal/addition blocks pair positionally within one hunk; no content-based match is attempted.
- Context appears on both sides; removal only on Before; addition only on After.
- Malformed header/count data yields no invented line positions. A final hunk count shortfall is accepted as an incomplete prefix only when Feature 011 marks that patch `diffTruncated`; render the positions derived from the header and retain its truncation notice.

## Renderer

- Two labeled regions: Before and After.
- Fixed-width line-number gutters and monospace source content.
- Add/remove semantics include textual/accessibility cues in addition to theme styling.
- Hunk separators and metadata rows remain visually distinguishable.
- Empty opposite sides use a non-source placeholder.
- Long lines scroll inside the bounded dialog region.

## Non-changes

No new endpoint, request parameters, provider lookup, persistence, migration, cache, patch retrieval, or `filesCompleteness` reinterpretation is introduced.
