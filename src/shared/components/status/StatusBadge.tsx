import { CheckCircle, Error, HourglassTop, PauseCircle, PlayCircle, RemoveCircle, WarningAmber } from '@mui/icons-material';
import { Chip } from '@mui/material';
import type { PresentationStatus } from '../../types/presentation';

const configs = {
  active: { label: 'Active', color: 'success', icon: <PlayCircle /> }, enabled: { label: 'Enabled', color: 'success', icon: <PlayCircle /> }, disabled: { label: 'Disabled', color: 'default', icon: <RemoveCircle /> },
  paused: { label: 'Paused', color: 'warning', icon: <PauseCircle /> }, pending: { label: 'Pending', color: 'info', icon: <HourglassTop /> },
  running: { label: 'Running', color: 'primary', icon: <PlayCircle /> }, completed: { label: 'Completed', color: 'success', icon: <CheckCircle /> },
  'partially-completed': { label: 'Partially completed', color: 'warning', icon: <WarningAmber /> }, failed: { label: 'Failed', color: 'error', icon: <Error /> },
} as const;
export function StatusBadge({ status }: { status: PresentationStatus }) { const c = configs[status]; return <Chip size="small" icon={c.icon} label={c.label} color={c.color} aria-label={`Status: ${c.label}`} sx={{ fontWeight: 700, '& .MuiChip-label': { px: 1 } }} />; }
