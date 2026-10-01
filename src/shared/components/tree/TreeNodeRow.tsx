import { Box, Checkbox, IconButton, Typography } from '@mui/material';
import { ChevronRightRounded, ExpandMoreRounded, FolderRounded, InsertDriveFileOutlined } from '@mui/icons-material';

export function TreeNodeRow({ label, depth = 0, kind = 'repository', expanded, selected, indeterminate,
  loading = false, onExpand, onSelect }: { label: string; depth?: number; kind?: 'group' | 'repository';
  expanded?: boolean; selected?: boolean; indeterminate?: boolean; loading?: boolean;
  onExpand?: () => void; onSelect?: () => void }) {
  return <Box sx={{ display: 'flex', alignItems: 'center', minHeight: 42, pl: Math.min(depth, 8) * 2 }}>
    <IconButton size="small" aria-label={kind === 'group' ? (expanded ? `Collapse ${label}` : `Expand ${label}`) : `Repository ${label}`}
      disabled={kind !== 'group' || loading} onClick={onExpand} aria-expanded={kind === 'group' ? !!expanded : undefined}>
      {kind === 'group' ? (expanded ? <ExpandMoreRounded /> : <ChevronRightRounded />) : <InsertDriveFileOutlined fontSize="small" />}
    </IconButton>
    <Checkbox size="small" checked={!!selected} indeterminate={!!indeterminate} onChange={onSelect}
      slotProps={{ input: { 'aria-label': `${selected ? 'Deselect' : 'Select'} ${label}` } }} />
    <FolderRounded color={kind === 'group' ? 'primary' : 'disabled'} fontSize="small" />
    <Typography sx={{ ml: 1, fontWeight: kind === 'group' ? 700 : 400, overflowWrap: 'anywhere' }}>{label}</Typography>
  </Box>;
}
