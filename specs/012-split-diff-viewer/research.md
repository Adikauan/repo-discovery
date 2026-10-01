# Research: Split Diff Viewer

## Decision 1: Parse normalized unified patch text in the frontend

- **Decision**: Add a pure TypeScript parser that returns ordered hunk/row values and a safe parse error result.
- **Rationale**: Feature 011 already returns bounded normalized patch text. Parsing in a dependency-free frontend utility keeps the existing backend contract unchanged and allows deterministic unit tests.
- **Alternatives considered**: New backend split-row API (duplicates frontend presentation and expands backend contract); general patch library (not required for the bounded supported format and adds a dependency).

## Decision 2: Deterministic source coordinates and positional replacement alignment

- **Decision**: Initialize old/new counters from standard hunk headers; treat omitted counts as one; context increments both counters, removals old only, additions new only. Pair each consecutive removal run followed immediately by additions in the same hunk positionally; do not use semantic matching. Keep metadata and hunk headings outside source numbering.
- **Rationale**: These rules are explicit in the feature scope and produce repeatable output without inventing source coordinates.
- **Alternatives considered**: Word/semantic matching (out of scope and nondeterministic); unified-only display (does not deliver side-by-side comparison).

## Decision 3: Fail safely on malformed patch accounting

- **Decision**: If a hunk header is invalid or source row counts conflict with declarations, return a parser error and show a safe local rendering error. Exception: when Feature 011 marks the patch `diffTruncated`, a count shortfall at the end of the available final hunk is an expected partial prefix; render its included rows with positions derived from the header and retain the truncation indicator. Do not present guessed line numbers or raw provider exceptions.
- **Rationale**: False line coordinates mislead users. The explicit Feature 011 truncation flag allows a known prefix to render safely while its displayed truncation indicator prevents it from appearing complete.
- **Alternatives considered**: Render best-effort partial numbering (can fabricate positions); hide the entire dialog (unnecessarily loses commit context).

## Decision 4: Reuse existing Material UI icon and dialog

- **Decision**: Use `Difference` from the already-installed `@mui/icons-material`, wrapped in the existing MUI `IconButton` and tooltip conventions. Preserve the current dialog, sidebar, request lifecycle and focus behavior.
- **Rationale**: The exact icon exists in the current dependency; no new package or interaction path is needed.
- **Alternatives considered**: Add another icon package (unnecessary dependency); replace the sidebar with tabs (conflicts with the requirement).

## Decision 5: Use the supplied image as layout reference only

- **Decision**: Use `references/7e81efbe-77df-480d-8243-df8ff5cb1b3b.png` to guide the modal/sidebar/selected-file/split layout, independent line-number gutters, addition/removal hierarchy, hunk separators, and monospace presentation. `spec.md` remains authoritative.
- **Rationale**: The image illustrates the requested UX without defining business behavior. Elements visible only in the mock, such as copy-path controls, an avatar, and aggregate change counts, are not added.
- **Alternatives considered**: Treat every visible mock element as required (would expand scope beyond the specification).

## Decision 6: Keep partial data semantics owned by Feature 011

- **Decision**: Do not reinterpret `filesCompleteness`; render available truncated file text with the existing indicator; preserve binary/too-large/collapsed/unavailable states and do not fetch content as fallback.
- **Rationale**: Feature 012 is a presentation-only evolution and the Feature 011 contract already defines these states.
- **Alternatives considered**: Retrieve file content or alter the response to complete a patch (unsafe scope and violates Feature 011 bounds).

## Decision 7: Keep each comparison synchronized in one shared row grid

- **Decision**: Render each parser row through one DOM row container with four shared CSS Grid tracks: old line number, old content, new line number, and new content. Render the empty cells for an absent side inside the same row. Give the existing dialog about 95vw width (capped at 1800px) and 90vh height, with a bounded file sidebar, flexible diff pane, and internal scrolling.
- **Root-cause finding**: The parser already returns one `modified` row for adjacent `-old`/`+new` input. The stacking came from the viewer rendering the old and new cell components as sibling auto-placed items in the parent grid; they did not share an explicit per-row grid container. The dialog also retained its default maximum width, which left too little horizontal space for two code panes.
- **Rationale**: A shared row grid guarantees that both sides and both gutters occupy the same visual line, including replacement blocks and empty-side rows. A bounded viewport-sized modal and local scrolling provide usable code width without changing page layout or Feature 011 retrieval.
- **Alternatives considered**: Keep two independent side lists (can desynchronize vertically); increase only the outer grid width (does not establish logical-row ownership); create another modal or change the diff API (unnecessary and out of scope).
