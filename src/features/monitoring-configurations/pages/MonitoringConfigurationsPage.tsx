import { useEffect, useState } from 'react';
import { AddRounded, SearchRounded } from '@mui/icons-material';
import { Alert, Box, Button, InputAdornment, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography } from '@mui/material';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import { ContentCard } from '../../../shared/components/layout/ContentCard';
import { PageContainer } from '../../../shared/components/layout/PageContainer';
import { PageHeader } from '../../../shared/components/layout/PageHeader';
import { EmptyState } from '../../../shared/components/feedback/EmptyState';
import { ErrorState } from '../../../shared/components/feedback/ErrorState';
import { LoadingState } from '../../../shared/components/feedback/LoadingState';
import { StatusBadge } from '../../../shared/components/status/StatusBadge';
import { ApiError } from '../../../shared/utils/apiClient';
import { monitoringConfigurationsApi } from '../api/monitoringConfigurationsApi';
import { DeleteConfigurationDialog } from '../components/DeleteConfigurationDialog';
import { ManualExecutionAction } from '../../executions/components/ManualExecutionAction';
import type { MonitoringConfiguration } from '../model/monitoringConfiguration';

function date(value: string) { return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value)); }
export function MonitoringConfigurationsPage() {
  const [query, setQuery] = useState('');
  const [items, setItems] = useState<MonitoringConfiguration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const [deleteTarget, setDeleteTarget] = useState<MonitoringConfiguration | null>(null);
  const location = useLocation();
  const [notice, setNotice] = useState((location.state as { notice?: string } | null)?.notice ?? '');

  useEffect(() => {
    const controller = new AbortController();
    let live = true;
    setLoading(true); setError('');
    monitoringConfigurationsApi.list(query, controller.signal)
      .then(result => { if (live) setItems(result.data.items); })
      .catch((reason: unknown) => { if (live && !controller.signal.aborted) setError(reason instanceof ApiError ? reason.message : 'Unable to load configurations.'); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; controller.abort(); };
  }, [query, retry]);

  async function deleteConfiguration() {
    if (!deleteTarget) return;
    try {
      await monitoringConfigurationsApi.remove(deleteTarget.id);
      setDeleteTarget(null); setNotice('Monitoring Configuration deleted successfully.'); setRetry(value => value + 1);
    } catch (reason) { setDeleteTarget(null); setError(reason instanceof ApiError ? reason.message : 'Unable to delete this configuration.'); }
  }

  return <PageContainer>
    <PageHeader title="Monitoring Configurations" description="Configure and organize recurring repository mining."
      breadcrumbs={[{ label: 'Monitoring Configurations', current: true }]}
      action={<Button component={RouterLink} to="/monitoring-configurations/new" variant="contained" startIcon={<AddRounded />}>New configuration</Button>} />
    {notice && <Alert severity="success" onClose={() => setNotice('')} sx={{ mb: 2 }}>{notice}</Alert>}
    <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}><TextField label="Search configurations" placeholder="Search by name" value={query} onChange={event => setQuery(event.target.value)} sx={{ flex: '1 1 320px' }} slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchRounded /></InputAdornment> } }} /></Box>
    {loading ? <LoadingState message="Loading Monitoring Configurations…" /> : error ? <ErrorState message={error} action={<Button onClick={() => setRetry(value => value + 1)}>Retry</Button>} /> : items.length === 0 ? <ContentCard><EmptyState title={query.trim() ? 'No matching configurations' : 'No Monitoring Configurations yet'} message={query.trim() ? 'Try another name or clear your search.' : 'Create a configuration to get started.'} action={!query.trim() && <Button component={RouterLink} to="/monitoring-configurations/new" variant="contained">Create configuration</Button>} /></ContentCard> : <ContentCard sx={{ '& .MuiCardContent-root': { p: 0 } }}><TableContainer sx={{ overflowX: 'auto' }}><Table aria-label="Monitoring configurations table" sx={{ minWidth: 1080 }}><TableHead><TableRow><TableCell>Name</TableCell><TableCell>Description</TableCell><TableCell>GitLab URL</TableCell><TableCell>Status</TableCell><TableCell>Schedule</TableCell><TableCell>Created</TableCell><TableCell>Updated</TableCell><TableCell align="right">Actions</TableCell></TableRow></TableHead><TableBody>{items.map(item => <TableRow key={item.id} hover>
      <TableCell><Button component={RouterLink} to={`/monitoring-configurations/${item.id}`} color="inherit" sx={{ fontWeight: 700 }}>{item.name}</Button></TableCell>
      <TableCell>{item.description || <Typography color="text.secondary">—</Typography>}</TableCell><TableCell sx={{ overflowWrap: 'anywhere' }}>{item.gitlab_url}</TableCell><TableCell><StatusBadge status={item.enabled ? 'enabled' : 'disabled'} /></TableCell><TableCell>{item.scheduleSummary ? <Stack spacing={.25}><Typography variant="body2" sx={{ textTransform: 'capitalize' }}>{item.scheduleSummary.recurrenceType} · {item.scheduleSummary.executionTime}</Typography><Typography variant="caption" color="text.secondary">{item.scheduleSummary.timezone} · {item.scheduleSummary.enabled ? 'Enabled' : 'Disabled'}</Typography></Stack> : <Typography variant="body2" color="text.secondary">No schedule</Typography>}</TableCell><TableCell>{date(item.created_at)}</TableCell><TableCell>{date(item.updated_at)}</TableCell>
      <TableCell align="right"><Stack direction="row" spacing={.5} sx={{ justifyContent: 'flex-end', alignItems: 'center' }}>
        <ManualExecutionAction configurationId={item.id} configurationName={item.name} compact />
        <Button component={RouterLink} to={`/monitoring-configurations/${item.id}/edit`} size="small">Edit</Button>
        <Button size="small" color="error" onClick={() => setDeleteTarget(item)} aria-label={`Delete ${item.name}`}>Delete</Button>
      </Stack></TableCell>
    </TableRow>)}</TableBody></Table></TableContainer></ContentCard>}
    <DeleteConfigurationDialog open={!!deleteTarget} name={deleteTarget?.name ?? ''} onClose={() => setDeleteTarget(null)} onConfirm={deleteConfiguration} />
  </PageContainer>;
}
