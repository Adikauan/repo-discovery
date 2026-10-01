import { useEffect, useState } from 'react';
import { Alert, Button, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from '@mui/material';
import { EmptyState } from '../../../shared/components/feedback/EmptyState';
import { LoadingState } from '../../../shared/components/feedback/LoadingState';
import { ErrorState } from '../../../shared/components/feedback/ErrorState';
import { StatusBadge } from '../../../shared/components/status/StatusBadge';
import { ApiError } from '../../../shared/utils/apiClient';
import { executionsApi } from '../api/executionsApi';
import type { ExecutionDetail, RepositoryExecution } from '../types/execution';

export function ExecutionRepositoriesSection({ execution, refreshRevision = 0 }: { execution: ExecutionDetail; refreshRevision?: number }) {
  const [items, setItems] = useState<RepositoryExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    executionsApi.repositories(execution.id, page, controller.signal).then(({ data }) => { setItems(data.items); setTotalPages(data.totalPages); })
      .catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof ApiError ? 'Repository history could not be loaded.' : 'Repository history could not be loaded.'); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [execution.id, retry, refreshRevision, page]);
  return <Stack spacing={2}>
    <Typography component="h2" variant="h2">Repositories</Typography>
    {loading ? <LoadingState message="Loading repository processing results…" /> : error ? <ErrorState title="Repository results unavailable" message={error} action={<Button onClick={() => setRetry(value => value + 1)}>Retry repository history</Button>} /> : items.length === 0 ?
      <EmptyState title={execution.status === 'completed' ? 'No repositories processed' : 'Repository details unavailable'} message={execution.status === 'completed' ? 'This execution completed with a valid empty effective scope. Repository count is 0.' : execution.status === 'pending' || execution.status === 'running' ? 'Repository processing results have not been persisted for this execution yet.' : 'No repository processing rows are available. Check the execution status and safe error summary.'} /> :
      <TableContainer component={Paper} sx={{ overflowX: 'auto' }}><Table aria-label="Repository processing results" size="small"><TableHead><TableRow>
        <TableCell>Repository</TableCell><TableCell>Status</TableCell><TableCell>Branch</TableCell><TableCell>Files</TableCell><TableCell>Findings</TableCell><TableCell>Started</TableCell><TableCell>Completed</TableCell><TableCell>Error</TableCell>
      </TableRow></TableHead><TableBody>{items.map(item => <TableRow key={item.id}>
        <TableCell sx={{ overflowWrap: 'anywhere' }}>{item.repositoryFullPath}</TableCell><TableCell><StatusBadge status={item.status} /></TableCell>
        <TableCell>{item.processedBranch ?? '—'}</TableCell><TableCell>{item.processedBranch ? item.fileCount : '—'}</TableCell><TableCell>{item.findingCount}</TableCell>
        <TableCell>{item.startedAt ?? '—'}</TableCell><TableCell>{item.completedAt ?? '—'}</TableCell>
        <TableCell>{item.error ? <Stack spacing={0.25}>
          <Typography variant="caption" sx={{ fontWeight: 700 }}>{item.error.code}</Typography>
          <Typography variant="body2">{item.error.summary}</Typography>
        </Stack> : '—'}</TableCell>
      </TableRow>)}</TableBody></Table></TableContainer>}
    {totalPages > 1 && <Stack direction="row" spacing={1} sx={{ alignItems: 'center', justifyContent: 'flex-end' }}>
      <Typography aria-live="polite">Page {page} of {totalPages}</Typography>
      <Button onClick={() => setPage(value => Math.max(1, value - 1))} disabled={page <= 1}>Previous page</Button>
      <Button onClick={() => setPage(value => Math.min(totalPages, value + 1))} disabled={page >= totalPages}>Next page</Button>
    </Stack>}
    {execution.scopeResolutionFailureCount ? <Alert severity="warning">{execution.scopeResolutionFailureCount} selected scope item(s) could not be resolved.</Alert> : null}
  </Stack>;
}
