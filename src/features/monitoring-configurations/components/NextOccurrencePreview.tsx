import { Alert, Typography } from '@mui/material';
import type { NextOccurrence } from '../types/schedule';

export function NextOccurrencePreview({ occurrence, loading, hasSchedule, enabled }: {
  occurrence: NextOccurrence | null; loading: boolean; hasSchedule: boolean; enabled: boolean;
}) {
  if (loading) return <Typography role="status" aria-live="polite">Calculating next scheduled occurrence…</Typography>;
  if (hasSchedule && !enabled) return <Alert severity="info" role="status">No next scheduled occurrence is available while automatic scheduling is disabled.</Alert>;
  if (!hasSchedule && !occurrence) return null;
  if (!occurrence) return <Typography role="status" aria-live="polite">Preview the current draft to calculate its next scheduled occurrence.</Typography>;
  const formatted = new Intl.DateTimeFormat(undefined, {
    dateStyle: 'full', timeStyle: 'short', timeZone: occurrence.timezone,
  }).format(new Date(occurrence.instant));
  return <Alert severity="info" role="status" aria-live="polite">
    <strong>Next scheduled occurrence (preview):</strong> {formatted} ({occurrence.timezone}). This is a calculation, not a guaranteed execution.
  </Alert>;
}
