import { Grid } from '@mui/material';
import { MetricCard } from '../../../shared/components/dashboard/MetricCard';
import type { ExecutionDetail } from '../types/execution';

export function ExecutionMetrics({ counters }: { counters: ExecutionDetail['counters'] }) {
  const metrics = [
    ['Repositories', counters.repositoryCount],
    ['Successful repositories', counters.successfulRepositoryCount],
    ['Failed repositories', counters.failedRepositoryCount],
    ['Findings', counters.findingCount],
  ] as const;
  return <Grid container spacing={2} aria-label="Execution metrics">
    {metrics.map(([label, value]) => <Grid key={label} size={{ xs: 12, sm: 6, lg: 3 }}>
      <MetricCard label={label} value={String(value)} />
    </Grid>)}
  </Grid>;
}
