import { useEffect, useState } from 'react';
import { Link as RouterLink, useLocation, useParams } from 'react-router-dom';
import { Alert, Box, Button, Stack, Tab, Tabs } from '@mui/material';
import { PageContainer } from '../../../shared/components/layout/PageContainer';
import { LoadingState } from '../../../shared/components/feedback/LoadingState';
import { ErrorState } from '../../../shared/components/feedback/ErrorState';
import { ApiError } from '../../../shared/utils/apiClient';
import { executionsApi } from '../api/executionsApi';
import type { ExecutionDetail } from '../types/execution';
import { ExecutionHeader } from '../components/ExecutionHeader';
import { ExecutionOverview } from '../components/ExecutionOverview';
import { ExecutionRepositoriesSection } from '../components/ExecutionRepositoriesSection';
import { ExecutionFindingsSection } from '../components/ExecutionFindingsSection';
import { ExecutionDetailsSection } from '../components/ExecutionDetailsSection';

export function getExecutionReturnPath(state: unknown) {
  const returnTo = (state as { returnTo?: unknown } | null)?.returnTo;
  if (typeof returnTo === 'string' && (/^\/executions(?:\?.*)?$/.test(returnTo) || /^\/monitoring-configurations\/[^/]+\/executions$/.test(returnTo))) return returnTo;
  return '/executions';
}

export function ExecutionDashboardPage() {
  const { id = '' } = useParams();
  const location = useLocation();
  const returnTo = getExecutionReturnPath(location.state);
  const [execution, setExecution] = useState<ExecutionDetail>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const [selectedTab, setSelectedTab] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState('');
  const [refreshRevision, setRefreshRevision] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    executionsApi.get(id).then(result => { if (active) setExecution(result.data); })
      .catch((cause: unknown) => {
        if (!active) return;
        setError(cause instanceof ApiError && cause.status === 404 ? 'Execution was not found.' : 'Unable to load execution.');
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id, retry]);

  async function refreshExecution() {
    setRefreshing(true);
    setRefreshError('');
    try {
      const result = await executionsApi.get(id);
      setExecution(result.data);
      setRefreshRevision(value => value + 1);
    } catch (cause) {
      setRefreshError(cause instanceof ApiError && cause.status === 404 ? 'Execution was not found.' : 'Unable to refresh execution.');
    } finally {
      setRefreshing(false);
    }
  }

  const historyLink = <Button component={RouterLink} to="/executions">Execution history</Button>;
  return <PageContainer>
    {loading && !execution ? <><LoadingState message="Loading execution…" />{historyLink}</> : error && !execution ? <ErrorState
      title={error === 'Execution was not found.' ? 'Execution not found' : 'Unable to load execution'}
      message={error}
      action={<Stack direction="row" spacing={1}>
        {error !== 'Execution was not found.' && <Button onClick={() => setRetry(value => value + 1)}>Retry</Button>}
        {historyLink}
      </Stack>}
    /> : execution && <>
      <ExecutionHeader execution={execution} returnTo={returnTo} onRefresh={refreshExecution} refreshing={refreshing} />
      {refreshing && <Box role="status" aria-label="Refreshing execution" aria-live="polite" sx={{ py: 1 }}>Refreshing execution…</Box>}
      {refreshError && <Alert severity="error" role="alert">{refreshError}</Alert>}
      {error && <Alert severity="error">{error}</Alert>}
      <Box sx={{ mt: 2 }}>
        <Tabs value={selectedTab} onChange={(_, value: number) => setSelectedTab(value)} aria-label="Execution sections" variant="scrollable" scrollButtons="auto">
          {['Overview', 'Repositories', 'Findings', 'Details'].map((label, index) => <Tab key={label} id={`execution-tab-${index}`} aria-controls={`execution-panel-${index}`} label={label} />)}
        </Tabs>
        <Box role="tabpanel" id={`execution-panel-${selectedTab}`} aria-labelledby={`execution-tab-${selectedTab}`} aria-busy={refreshing} sx={{ pt: 3 }}>
          {selectedTab === 0 && <ExecutionOverview execution={execution} />}
          {selectedTab === 1 && <ExecutionRepositoriesSection execution={execution} refreshRevision={refreshRevision} />}
          {selectedTab === 2 && <ExecutionFindingsSection executionId={execution.id} refreshRevision={refreshRevision} />}
          {selectedTab === 3 && <ExecutionDetailsSection execution={execution} />}
        </Box>
      </Box>
    </>}
  </PageContainer>;
}
