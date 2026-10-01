import { Box, Typography } from '@mui/material';
import type { SplitDiffHunk, SplitDiffRow } from '../utils/splitDiffParser';

const splitColumns = '3.5rem minmax(280px, 1fr) 3.5rem minmax(280px, 1fr)';

function LineNumber({ value, side }: { value: number | null; side: 'old' | 'new' }) {
  return <Box
    data-testid={`${side}-line-number`}
    aria-hidden="true"
    sx={{
      minWidth: '3.5rem', width: '3.5rem', boxSizing: 'border-box',
      textAlign: 'right', px: 1, py: 0.5, color: 'text.secondary',
      borderRight: 1, borderColor: 'divider', fontFamily: 'monospace',
      userSelect: 'none', whiteSpace: 'pre',
    }}
  >{value ?? ''}</Box>;
}

function SourceCell({ content, marker, kind, side }: {
  content: string | null;
  marker: '+' | '-' | null;
  kind: 'context' | 'removed' | 'added' | 'empty';
  side: 'old' | 'new';
}) {
  return <Box
    data-testid={`${side}-content`}
    data-empty-placeholder={kind === 'empty' ? 'true' : undefined}
    sx={{
      minWidth: 0, boxSizing: 'border-box', px: 1, py: 0.5,
      whiteSpace: 'pre', fontFamily: 'monospace',
      overflow: 'visible',
      bgcolor: kind === 'removed' ? 'error.light' : kind === 'added' ? 'success.light' : kind === 'empty' ? 'action.hover' : 'background.paper',
      borderRight: 1, borderColor: 'divider',
    }}
  >
    {marker && <Box component="span" aria-hidden="true" sx={{ fontWeight: 'bold', pr: 0.75 }}>{marker}</Box>}
    {content ?? <Box component="span" aria-hidden="true"> </Box>}
  </Box>;
}

function DiffRow({ row }: { row: SplitDiffRow }) {
  if (row.type === 'metadata') {
    return <Box
      data-testid="split-diff-metadata-row"
      role="note"
      sx={{ gridColumn: '1 / -1', px: 1, py: 0.5, bgcolor: 'action.hover', fontFamily: 'monospace' }}
    >{row.metadataText}</Box>;
  }

  const accessible = row.type === 'modified'
    ? `Modified. Removed line ${row.oldLineNumber}: ${row.oldContent ?? ''}. Added line ${row.newLineNumber}: ${row.newContent ?? ''}.`
    : row.type === 'removed'
      ? `Removed line ${row.oldLineNumber}: ${row.oldContent ?? ''}.`
      : row.type === 'added'
        ? `Added line ${row.newLineNumber}: ${row.newContent ?? ''}.`
        : `Context, old line ${row.oldLineNumber}, new line ${row.newLineNumber}: ${row.oldContent ?? ''}.`;

  const oldKind = row.type === 'removed' || row.type === 'modified' ? 'removed' : row.type === 'context' ? 'context' : 'empty';
  const newKind = row.type === 'added' || row.type === 'modified' ? 'added' : row.type === 'context' ? 'context' : 'empty';
  return <Box
    data-testid="split-diff-row"
    data-row-type={row.type}
    role="group"
    aria-label={accessible}
    sx={{
      gridColumn: '1 / -1', display: 'grid', gridTemplateColumns: splitColumns,
      minWidth: 0, borderBottom: 1, borderColor: 'divider',
    }}
  >
    <LineNumber side="old" value={row.oldLineNumber} />
    <SourceCell side="old" content={row.oldContent} marker={oldKind === 'removed' ? '-' : null} kind={oldKind} />
    <LineNumber side="new" value={row.newLineNumber} />
    <SourceCell side="new" content={row.newContent} marker={newKind === 'added' ? '+' : null} kind={newKind} />
  </Box>;
}

export function SplitDiffViewer({ hunks }: { hunks: SplitDiffHunk[] }) {
  if (hunks.length === 0 || hunks.every(hunk => hunk.rows.length === 0)) {
    return <Typography role="status">No textual diff was returned for this file.</Typography>;
  }

  return <Box
    role="region"
    aria-label="Split diff content"
    data-testid="split-diff-content"
    sx={{
      width: '100%', maxWidth: '100%', minWidth: 0, minHeight: 0, flex: '1 1 auto',
      overflow: 'auto', border: 1, borderColor: 'divider',
    }}
  >
    <Box sx={{ minWidth: 1030, width: '100%', display: 'grid', gridTemplateColumns: splitColumns }}>
      <Box role="region" aria-label="Before (previous version)" sx={{ gridColumn: '1 / 3', minWidth: 0, px: 1, py: 1, bgcolor: 'action.hover', borderRight: 1, borderBottom: 1, borderColor: 'divider' }}>
        <Typography component="h4" variant="subtitle2">Before (previous version)</Typography>
      </Box>
      <Box role="region" aria-label="After (new version)" sx={{ gridColumn: '3 / 5', minWidth: 0, px: 1, py: 1, bgcolor: 'action.hover', borderBottom: 1, borderColor: 'divider' }}>
        <Typography component="h4" variant="subtitle2">After (new version)</Typography>
      </Box>
      {hunks.map((hunk, hunkIndex) => <Box key={`${hunk.header}-${hunkIndex}`} sx={{ display: 'contents' }}>
        <Box role="separator" aria-label={`Diff section ${hunk.header}`} sx={{ gridColumn: '1 / -1', px: 1, py: 0.75, bgcolor: 'info.light', color: 'text.primary', borderBottom: 1, borderColor: 'divider', fontFamily: 'monospace' }}>
          {hunk.header}
        </Box>
        {hunk.rows.map((row, rowIndex) => <DiffRow key={`${hunkIndex}-${rowIndex}`} row={row} />)}
      </Box>)}
    </Box>
  </Box>;
}
