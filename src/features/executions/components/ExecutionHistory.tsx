import { useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Button, Link, Pagination, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography } from '@mui/material';
import { executionsApi } from '../api/executionsApi';
import type { ExecutionPage, ExecutionStatus, TriggerType } from '../types/execution';
import { ApiError } from '../../../shared/utils/apiClient';
import { ContentCard } from '../../../shared/components/layout/ContentCard';
import { LoadingState } from '../../../shared/components/feedback/LoadingState';
import { ErrorState } from '../../../shared/components/feedback/ErrorState';
import { EmptyState } from '../../../shared/components/feedback/EmptyState';
import { StatusBadge } from '../../../shared/components/status/StatusBadge';

export const statusLabels: Record<ExecutionStatus, string> = { pending: 'Pending', running: 'Running', completed: 'Completed', partially_completed: 'Partially completed', failed: 'Failed' };
export function executionDate(value: string | null) { return value ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—'; }
export function ExecutionBadge({ status }: { status: ExecutionStatus }) { return <StatusBadge status={status === 'partially_completed' ? 'partially-completed' : status} />; }

export function ExecutionHistory({ configurationId }: { configurationId?: string }) {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<ExecutionStatus | ''>('');
  const [trigger, setTrigger] = useState<TriggerType | ''>('');
  const [configurationFilter, setConfigurationFilter] = useState('');
  const [configurationDraft, setConfigurationDraft] = useState('');
  const [data, setData] = useState<ExecutionPage>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    const filters = { page, status: status || undefined, triggerType: trigger || undefined, monitoringConfigurationId: configurationId ? undefined : configurationFilter || undefined };
    const request = configurationId ? executionsApi.listForConfiguration(configurationId, filters, controller.signal) : executionsApi.list(filters, controller.signal);
    request.then(result => { if (!controller.signal.aborted) setData(result.data); })
      .catch((e: unknown) => { if (!controller.signal.aborted) setError(e instanceof ApiError ? e.message : 'Unable to load execution history.'); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [configurationId, configurationFilter, page, status, trigger, retry]);
  return <ContentCard>
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 3 }}>
      <TextField select label="Status" value={status} onChange={e => { setStatus(e.target.value as ExecutionStatus | ''); setPage(1); }} slotProps={{ select: { native: true } }} sx={{ minWidth: 180 }}>
        <option value="">All statuses</option>{Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </TextField>
      <TextField select label="Trigger" value={trigger} onChange={e => { setTrigger(e.target.value as TriggerType | ''); setPage(1); }} slotProps={{ select: { native: true } }} sx={{ minWidth: 160 }}>
        <option value="">All triggers</option><option value="manual">Manual</option><option value="scheduled">Scheduled</option>
      </TextField>
      {!configurationId && <Stack component="form" direction="row" spacing={1} onSubmit={e => { e.preventDefault(); setConfigurationFilter(configurationDraft.trim()); setPage(1); }}>
        <TextField label="Configuration ID" value={configurationDraft} onChange={e => setConfigurationDraft(e.target.value)} /><Button type="submit">Apply filter</Button>
      </Stack>}
    </Stack>
    {loading ? <LoadingState message="Loading execution history…" /> : error ? <ErrorState message={error} action={<Button onClick={() => setRetry(v => v + 1)}>Retry</Button>} /> : !data?.items.length ?
      <EmptyState title="No executions found" message="Request a manual execution from a Monitoring Configuration, or adjust the filters." /> : <>
        <TableContainer sx={{ overflowX: 'auto' }}><Table aria-label="Execution history" sx={{ minWidth: 980 }}><TableHead><TableRow>
          {['Execution', 'Configuration', 'Status', 'Trigger', 'Created', 'Started', 'Completed', 'Duration', 'Findings'].map(label => <TableCell key={label}>{label}</TableCell>)}
        </TableRow></TableHead><TableBody>{data.items.map(item => <TableRow key={item.id}>
          <TableCell sx={{ overflowWrap: 'anywhere' }}><RouterLink to={`/executions/${item.id}`} state={{ returnTo: configurationId ? `/monitoring-configurations/${configurationId}/executions` : '/executions' }}>{item.id}</RouterLink></TableCell>
          <TableCell><Link component={RouterLink} to={`/monitoring-configurations/${item.monitoringConfigurationId}/executions`}>{item.configurationName}</Link></TableCell>
          <TableCell><ExecutionBadge status={item.status} /></TableCell><TableCell>{item.triggerType === 'manual' ? 'Manual' : 'Scheduled'}</TableCell>
          <TableCell>{executionDate(item.createdAt)}</TableCell><TableCell>{executionDate(item.startedAt)}</TableCell><TableCell>{executionDate(item.completedAt)}</TableCell>
          <TableCell>{item.durationSeconds === null ? '—' : `${item.durationSeconds} s`}</TableCell><TableCell>{item.findingCount}</TableCell>
        </TableRow>)}</TableBody></Table></TableContainer>
        <Stack direction="row" spacing={2} sx={{ mt: 2, alignItems: 'center', flexWrap: 'wrap' }}><Typography>{data.totalItems} executions</Typography>
          <Pagination count={data.totalPages} page={page} onChange={(_, value) => setPage(value)} aria-label="Execution history pages" /></Stack>
      </>}
  </ContentCard>;
}
