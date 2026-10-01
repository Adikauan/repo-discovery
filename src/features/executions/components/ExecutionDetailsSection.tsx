import { Box, Stack, Typography } from '@mui/material';
import { ContentCard } from '../../../shared/components/layout/ContentCard';
import { executionDate, statusLabels } from './ExecutionHistory';
import { ExecutionErrorSummary } from './ExecutionErrorSummary';
import type { ExecutionDetail } from '../types/execution';

export function ExecutionDetailsSection({ execution }: { execution: ExecutionDetail }) {
  const rows = [
    ['Execution ID', execution.id],
    ['Status', statusLabels[execution.status]],
    ['Trigger', execution.triggerType === 'manual' ? 'Manual' : 'Scheduled'],
    ['Created', executionDate(execution.createdAt)],
    ...(execution.startedAt ? [['Started', executionDate(execution.startedAt)]] : []),
    ...(execution.completedAt ? [['Completed', executionDate(execution.completedAt)]] : []),
  ];
  return <Stack spacing={2}>
    <Typography component="h2" variant="h2">Details</Typography>
    <ContentCard><Box component="dl" sx={{ m: 0, display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' }, gap: 2 }}>
      {rows.map(([label, value]) => <Box key={label} sx={{ minWidth: 0 }}><Typography component="dt" color="text.secondary">{label}</Typography><Typography component="dd" sx={{ m: 0, overflowWrap: 'anywhere' }}>{value}</Typography></Box>)}
    </Box></ContentCard>
    <ExecutionErrorSummary error={execution.error} />
  </Stack>;
}
