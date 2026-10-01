import { useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Box, Button, Grid, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from '@mui/material';
import { ContentCard } from '../../../shared/components/layout/ContentCard';
import { PageContainer } from '../../../shared/components/layout/PageContainer';
import { PageHeader } from '../../../shared/components/layout/PageHeader';
import { EmptyState } from '../../../shared/components/feedback/EmptyState';
import { ErrorState } from '../../../shared/components/feedback/ErrorState';
import { LoadingState } from '../../../shared/components/feedback/LoadingState';
import { MetricCard } from '../../../shared/components/dashboard/MetricCard';
import { StatusBadge } from '../../../shared/components/status/StatusBadge';
import { ApiError } from '../../../shared/utils/apiClient';
import { dashboardApi, type DashboardSummary } from '../api/dashboardApi';

const number = new Intl.NumberFormat();
function isDashboardSummary(value: unknown): value is DashboardSummary {
  if (!value || typeof value !== 'object') return false;
  const summary = value as Partial<DashboardSummary>;
  return !!summary.metrics && typeof summary.metrics.executionCount === 'number' &&
    typeof summary.metrics.repositoriesProcessed === 'number' && typeof summary.metrics.findingCount === 'number' &&
    !!summary.statusDistribution && Array.isArray(summary.dailyExecutions) &&
    Array.isArray(summary.recentExecutions) && Array.isArray(summary.findingsByRule);
}
function date(value: string) { return new Intl.DateTimeFormat(undefined, { day: '2-digit', month: '2-digit' }).format(new Date(value)); }
function dateTime(value: string | null) { return value ? new Intl.DateTimeFormat(undefined, { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value)) : '—'; }
function status(value: string) { return value === 'partially_completed' ? 'partially-completed' : value as 'pending' | 'running' | 'completed' | 'failed'; }

export function HomePage() {
  const [data, setData] = useState<DashboardSummary>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError('');
    dashboardApi.summary(controller.signal).then(result => { if (!controller.signal.aborted) {
      if (!isDashboardSummary(result.data)) { setData(undefined); setError('Dashboard summary is unavailable.'); return; }
      setData(result.data);
    } })
      .catch((reason: unknown) => { if (!controller.signal.aborted) setError(reason instanceof ApiError ? reason.message : 'Unable to load dashboard summary.'); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [retry]);

  return <PageContainer>
    <PageHeader title="Home" description="Your repository mining workspace." />
    {loading ? <LoadingState message="Loading dashboard summary…" /> : error ? <ErrorState message={error} action={<Button onClick={() => setRetry(value => value + 1)}>Retry</Button>} /> : !data ? null : <>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>Last 7 days · UTC</Typography>
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 6, xl: 3 }}><MetricCard label="Executions" value={number.format(data.metrics.executionCount)} detail="Created in the last 7 days" /></Grid>
        <Grid size={{ xs: 12, sm: 6, xl: 3 }}><MetricCard label="Repositories" value={number.format(data.metrics.repositoriesProcessed)} detail="Distinct repositories processed" /></Grid>
        <Grid size={{ xs: 12, sm: 6, xl: 3 }}><MetricCard label="Findings" value={number.format(data.metrics.findingCount)} detail="Persisted findings" /></Grid>
        <Grid size={{ xs: 12, sm: 6, xl: 3 }}><MetricCard label="Success rate" value={data.metrics.successRatePercent === null ? '—' : `${data.metrics.successRatePercent}%`} detail={data.metrics.terminalExecutionCount ? `${data.metrics.terminalExecutionCount} terminal executions` : 'No completed executions in this period'} /></Grid>
        <Grid size={{ xs: 12, lg: 7 }}><ContentCard><Typography variant="h2" sx={{ fontSize: '1.25rem', mb: 2 }}>Executions per day</Typography>
          {data.metrics.executionCount === 0 ? <EmptyState title="No executions in this period" message="Execution activity will appear here when runs are recorded." /> : <Box role="img" aria-label={`Daily executions: ${data.dailyExecutions.map(day => `${date(day.date)} ${day.count}`).join(', ')}`} sx={{ height: 210, display: 'flex', alignItems: 'end', gap: 1, borderBottom: 1, borderColor: 'divider', overflowX: 'auto', px: 1 }}>
            {data.dailyExecutions.map(day => { const max = Math.max(1, ...data.dailyExecutions.map(item => item.count)); const height = Math.max(day.count ? 12 : 2, Math.round(day.count / max * 150)); return <Box key={day.date} sx={{ flex: '1 0 36px', minWidth: 24, height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'end', alignItems: 'center', gap: .75 }}><Typography variant="caption">{day.count || ''}</Typography><Box sx={{ height, width: '75%', minWidth: 18, borderRadius: '5px 5px 0 0', bgcolor: 'primary.main' }} /><Typography variant="caption" color="text.secondary">{date(day.date)}</Typography></Box>; })}
          </Box>}
        </ContentCard></Grid>
        <Grid size={{ xs: 12, lg: 5 }}><ContentCard><Typography variant="h2" sx={{ fontSize: '1.25rem', mb: 2 }}>Execution status</Typography><Stack spacing={1.5}>{(['completed', 'failed', 'partially_completed', 'running', 'pending'] as const).map(key => <Box key={key} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><StatusBadge status={status(key)} /><Typography sx={{ fontWeight: 600 }}>{number.format(data.statusDistribution[key === 'partially_completed' ? 'partiallyCompleted' : key])}</Typography></Box>)}</Stack></ContentCard></Grid>
        <Grid size={{ xs: 12, lg: 7 }}><ContentCard sx={{ '& .MuiCardContent-root': { p: 0 } }}><Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', px: 2.5, py: 2 }}><Typography variant="h2" sx={{ fontSize: '1.25rem' }}>Recent executions</Typography><Button component={RouterLink} to="/executions">View all</Button></Box>
          {!data.recentExecutions.length ? <Box sx={{ p: 2.5 }}><EmptyState title="No recent executions" message="Runs will appear here after a Monitoring Configuration is executed." /></Box> : <Box sx={{ overflowX: 'auto' }}><Table aria-label="Recent executions" size="small" sx={{ minWidth: 680 }}><TableHead><TableRow>{['Execution', 'Configuration', 'Status', 'Trigger', 'Started', 'Duration', 'Findings'].map(text => <TableCell key={text}>{text}</TableCell>)}</TableRow></TableHead><TableBody>{data.recentExecutions.map(item => <TableRow key={item.id} hover><TableCell><RouterLink to={`/executions/${item.id}`}>{item.id.slice(0, 12)}</RouterLink></TableCell><TableCell>{item.configurationName}</TableCell><TableCell><StatusBadge status={status(item.status)} /></TableCell><TableCell>{item.triggerType === 'scheduled' ? 'Scheduled' : 'Manual'}</TableCell><TableCell>{dateTime(item.startedAt)}</TableCell><TableCell>{item.durationSeconds === null ? '—' : `${Math.round(item.durationSeconds / 60)} min`}</TableCell><TableCell>{item.findingCount}</TableCell></TableRow>)}</TableBody></Table></Box>}
        </ContentCard></Grid>
        <Grid size={{ xs: 12, lg: 5 }}><ContentCard sx={{ '& .MuiCardContent-root': { p: 0 } }}><Typography variant="h2" sx={{ fontSize: '1.25rem', px: 2.5, py: 2 }}>Findings by rule</Typography>{!data.findingsByRule.length ? <Box sx={{ p: 2.5 }}><EmptyState title="No findings detected" message="Only persisted findings from implemented rules are shown." /></Box> : <><Table aria-label="Findings by rule" size="small"><TableHead><TableRow><TableCell>Rule</TableCell><TableCell align="right">Count</TableCell></TableRow></TableHead><TableBody>{data.findingsByRule.map(rule => <TableRow key={rule.ruleId}><TableCell>{rule.label}</TableCell><TableCell align="right">{rule.count}</TableCell></TableRow>)}</TableBody></Table><Typography variant="caption" color="text.secondary" sx={{ display: 'block', p: 2 }}>Only implemented finding rules are shown.</Typography></>}</ContentCard></Grid>
      </Grid>
    </>}
  </PageContainer>;
}
