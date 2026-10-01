import { Alert, Box, Stack, Typography } from '@mui/material';
import { ContentCard } from '../../../shared/components/layout/ContentCard';
import { executionDate } from './ExecutionHistory';
import { ExecutionMetrics } from './ExecutionMetrics';
import { ExecutionErrorSummary } from './ExecutionErrorSummary';
import type { ExecutionDetail } from '../types/execution';

function formatDuration(seconds: number | null) {
  if (seconds === null || !Number.isFinite(seconds) || seconds < 0) return 'Not available';
  if (seconds < 60) return `${seconds} ${seconds === 1 ? 'second' : 'seconds'}`;
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return remainder ? `${minutes} min ${remainder} sec` : `${minutes} ${minutes === 1 ? 'minute' : 'minutes'}`;
}

function ScopeList({ title, items }: { title: string; items: { name: string; fullPath: string }[] }) {
  return <Box>
    <Typography component="h3" variant="h3" sx={{ mb: 1 }}>{title}</Typography>
    {items.length ? <Box component="ul" aria-label={title} sx={{ m: 0, pl: 3 }}>
      {items.map(item => <li key={`${item.fullPath}-${item.name}`}><Typography component="span" sx={{ overflowWrap: 'anywhere' }}>{item.name}{item.name !== item.fullPath ? ` · ${item.fullPath}` : ''}</Typography></li>)}
    </Box> : <Typography color="text.secondary">No {title.toLowerCase()} selected.</Typography>}
  </Box>;
}

export function ExecutionOverview({ execution }: { execution: ExecutionDetail }) {
  const { snapshot } = execution;
  return <Stack spacing={2.5}>
    <Typography component="h2" variant="h2">Overview</Typography>
    {execution.completionMeaning && <Alert severity="info" aria-label="Completion meaning">{execution.completionMeaning}</Alert>}
    <ExecutionErrorSummary error={execution.error} />
    <ContentCard component="section" aria-labelledby="execution-lifecycle-heading">
      <Typography component="h3" variant="h3" id="execution-lifecycle-heading" sx={{ mb: 2 }}>Execution lifecycle</Typography>
      <Box component="dl" sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' }, gap: 2, m: 0 }}>
        {[
          ['Created', executionDate(execution.createdAt)],
          ['Started', execution.startedAt ? executionDate(execution.startedAt) : 'Not started'],
          ['Completed', execution.completedAt ? executionDate(execution.completedAt) : 'Not completed'],
          ['Duration', formatDuration(execution.durationSeconds)],
        ].map(([label, value]) => <Box key={label}><Typography component="dt" color="text.secondary">{label}</Typography><Typography component="dd" sx={{ m: 0 }}>{value}</Typography></Box>)}
      </Box>
    </ContentCard>
    <ContentCard component="section" aria-labelledby="execution-snapshot-heading">
      <Typography component="h3" variant="h3" id="execution-snapshot-heading" sx={{ mb: 2 }}>Historical execution snapshot</Typography>
      <Box sx={{ mb: 2 }}><Typography component="span" sx={{ fontWeight: 700 }}>GitLab URL: </Typography><Box component="span" sx={{ overflowWrap: 'anywhere' }}>{snapshot.gitlabUrl}</Box></Box>
      <Stack spacing={2}><ScopeList title="Selected groups" items={snapshot.scope.groups} /><ScopeList title="Selected repositories" items={snapshot.scope.repositories} /></Stack>
    </ContentCard>
    <Box component="section" aria-label="Persisted execution metrics"><ExecutionMetrics counters={execution.counters} /></Box>
  </Stack>;
}
