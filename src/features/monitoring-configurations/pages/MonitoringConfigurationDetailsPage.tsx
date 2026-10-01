import { useEffect, useState } from 'react';
import { Alert, Button, Grid, Stack, Typography } from '@mui/material';
import { Link as RouterLink, useLocation, useParams } from 'react-router-dom';
import { ContentCard } from '../../../shared/components/layout/ContentCard';
import { PageContainer } from '../../../shared/components/layout/PageContainer';
import { PageHeader } from '../../../shared/components/layout/PageHeader';
import { ErrorState } from '../../../shared/components/feedback/ErrorState';
import { LoadingState } from '../../../shared/components/feedback/LoadingState';
import { StatusBadge } from '../../../shared/components/status/StatusBadge';
import { ApiError } from '../../../shared/utils/apiClient';
import { monitoringConfigurationsApi } from '../api/monitoringConfigurationsApi';
import type { MonitoringConfiguration } from '../model/monitoringConfiguration';
import { ManualExecutionAction } from '../../executions/components/ManualExecutionAction';

function Field({ label, value }: { label: string; value: string }) { return <Grid size={{ xs: 12, sm: 6 }}><Typography variant="body2" color="text.secondary">{label}</Typography><Typography sx={{ mt: .5, overflowWrap: 'anywhere' }}>{value || '—'}</Typography></Grid>; }
function date(value: string) { return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)); }

export function MonitoringConfigurationDetailsPage() {
  const { id = '' } = useParams(); const location = useLocation();
  const [item, setItem] = useState<MonitoringConfiguration>(); const [loading, setLoading] = useState(true);
  const [error, setError] = useState(''); const [retry, setRetry] = useState(0);
  const [notice, setNotice] = useState((location.state as { notice?: string } | null)?.notice ?? '');
  useEffect(() => { let live = true; setLoading(true); setError(''); monitoringConfigurationsApi.get(id).then(result => { if (live) setItem(result.data); })
    .catch((e: unknown) => { if (live) setError(e instanceof ApiError ? (e.status === 404 ? 'This Monitoring Configuration is unavailable.' : e.message) : 'Unable to load this configuration.'); })
    .finally(() => { if (live) setLoading(false); }); return () => { live = false; }; }, [id, retry]);
  return <PageContainer><PageHeader title="Monitoring Configuration" description="Review configuration identity and execution history."
    breadcrumbs={[{ label: 'Monitoring Configurations', path: '/monitoring-configurations' }, { label: item?.name ?? 'Configuration', current: true }]}
    status={item && <StatusBadge status={item.enabled ? 'active' : 'disabled'} />} />
    {notice && <Alert severity="success" onClose={() => setNotice('')} sx={{ mb: 2 }}>{notice}</Alert>}
    {loading ? <LoadingState message="Loading configuration…" /> : error && !item ? <ErrorState message={error} action={<Button onClick={() => { setError(''); setRetry(value => value + 1); }}>Retry</Button>} /> : item ? <>
      <ContentCard><Grid container spacing={3}><Field label="Name" value={item.name} /><Field label="Description" value={item.description ?? ''} /><Field label="GitLab instance URL" value={item.gitlab_url} /><Field label="Status" value={item.enabled ? 'Enabled' : 'Disabled'} /><Field label="Created" value={date(item.created_at)} /><Field label="Last updated" value={date(item.updated_at)} /></Grid>
        <Stack direction="row" spacing={1} sx={{ mt: 2 }}><Button component={RouterLink} to={`/monitoring-configurations/${id}/executions`}>View execution history</Button></Stack>
      </ContentCard>
      <ContentCard sx={{ mt: 2 }}><Typography variant="h2" sx={{ fontSize: '1.15rem' }}>Execution actions</Typography><ManualExecutionAction key={item.id} configurationId={item.id} /></ContentCard>
    </> : null}
  </PageContainer>;
}
