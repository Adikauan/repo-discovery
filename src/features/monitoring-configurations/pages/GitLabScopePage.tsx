import { useEffect, useRef } from 'react';
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, Grid, Stack } from '@mui/material';
import { useBlocker, useNavigate, useParams } from 'react-router-dom';
import { PageContainer } from '../../../shared/components/layout/PageContainer';
import { PageHeader } from '../../../shared/components/layout/PageHeader';
import { LoadingState } from '../../../shared/components/feedback/LoadingState';
import { useGitLabScope } from '../hooks/useGitLabScope';
import { RepositoryTree } from '../components/RepositoryTree';
import { ScopeSelectionSummary } from '../components/ScopeSelectionSummary';
import { ConfigurationWizardProgress } from '../components/ConfigurationWizardProgress';
import { MonitoringConfigurationWizardLayout } from '../components/MonitoringConfigurationWizardLayout';

export function GitLabScopePage() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const model = useGitLabScope(id);
  const allowNext = useRef(false);
  const hasUnsavedChanges = model.dirty;
  const blocker = useBlocker(({ nextLocation }) => hasUnsavedChanges && !(allowNext.current && nextLocation.pathname === `/monitoring-configurations/${encodeURIComponent(id)}/authors`));

  useEffect(() => {
    const beforeUnload = (event: BeforeUnloadEvent) => {
      if (!hasUnsavedChanges) return;
      event.preventDefault(); event.returnValue = '';
    };
    window.addEventListener('beforeunload', beforeUnload);
    return () => window.removeEventListener('beforeunload', beforeUnload);
  }, [hasUnsavedChanges]);

  const previous = () => navigate(`/monitoring-configurations/${encodeURIComponent(id)}/gitlab-connection`);
  async function next() {
    if (model.dirty && !(await model.save())) return;
    allowNext.current = true;
    navigate(`/monitoring-configurations/${encodeURIComponent(id)}/authors`);
  }
  if (model.scopeLoading && !model.scope) return <MonitoringConfigurationWizardLayout step={2} previous={previous} previousLabel="GitLab Connection" next={() => void next()} nextLabel="Policy" busy={model.saving}><PageContainer><LoadingState message="Loading saved GitLab scope…" /></PageContainer></MonitoringConfigurationWizardLayout>;
  if (model.scopeError && !model.scope) return <MonitoringConfigurationWizardLayout step={2} previous={previous} previousLabel="GitLab Connection" next={() => void next()} nextLabel="Policy"><PageContainer><PageHeader title="GitLab Scope" />
    <Alert severity="error" action={<Button color="inherit" onClick={() => void model.reload()}>Retry</Button>}>{model.scopeError}</Alert>
  </PageContainer></MonitoringConfigurationWizardLayout>;

  const allLoadedNodes = [...model.rootNodes, ...Object.values(model.children).flat()];
  return <MonitoringConfigurationWizardLayout step={2} previous={previous} previousLabel="GitLab Connection" next={() => void next()} nextLabel="Policy" busy={model.saving}><PageContainer>
    <PageHeader title="GitLab Scope" description="Choose the groups and repositories included in this Monitoring Configuration’s scope."
      breadcrumbs={[{ label: 'Monitoring Configurations', path: '/monitoring-configurations' },
        { label: 'Configuration', path: `/monitoring-configurations/${encodeURIComponent(id)}` },
        { label: 'GitLab Scope', current: true }]} />
    <ConfigurationWizardProgress configurationId={id} currentStep={2} />
    {model.scopeError && <Alert severity="warning" sx={{ mb: 2 }}>{model.scopeError}</Alert>}
    {model.rootError && model.rootError.includes('credential') && <Alert severity="info" sx={{ mb: 2 }}>
      Configure a GitLab credential on the Monitoring Configuration to browse and add scope. Saved selections remain available below.
    </Alert>}
    {model.notice && <Alert severity="success" onClose={model.dismissNotice} sx={{ mb: 2 }}>{model.notice}</Alert>}
    {model.saveError && <Alert severity="error" sx={{ mb: 2 }}>{model.saveError}</Alert>}
    <Grid container spacing={2} sx={{ alignItems: 'flex-start' }}>
      <Grid size={{ xs: 12, lg: 7 }}><RepositoryTree rootNodes={model.rootNodes} childrenByGroup={model.children}
        expanded={model.expanded} loaded={model.loaded} loadingNodes={model.loadingNodes} nodeErrors={model.nodeErrors}
        draft={model.draft} rootLoading={model.rootLoading} rootError={model.rootError}
        onRetryRoot={() => void model.loadRoot()} onLoadChildren={id => void model.loadChildren(id)}
        onToggleExpanded={model.toggleExpanded} onToggleSelection={model.toggleSelection} /></Grid>
      <Grid size={{ xs: 12, lg: 5 }} data-sticky-desktop="true" data-sticky-top-offset="16"
        sx={{ alignSelf: 'flex-start', position: { xs: 'static', lg: 'sticky' },
        top: { lg: 2 }, maxHeight: { xs: 'none', lg: 'calc(100vh - 128px)' },
        overflowY: { xs: 'visible', lg: 'auto' }, overscrollBehavior: 'contain' }}>
        <ScopeSelectionSummary draft={model.draft} treeNodes={allLoadedNodes}
        onRemove={model.removeRule} onClear={model.clear} /></Grid>
    </Grid>
    {model.dirty && <Alert severity="info" sx={{ mt: 2 }}>You have unsaved scope changes.</Alert>}
    <Stack direction="row" spacing={1} sx={{ mt: 2, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
      <Button disabled={!model.dirty || model.saving} onClick={() => void model.reload()}>Discard changes</Button>
      <Button variant="contained" disabled={!model.dirty || model.saving} onClick={() => void model.save()}>
        {model.saving ? 'Saving…' : 'Save scope'}
      </Button>
    </Stack>
    <Dialog open={blocker.state === 'blocked'} onClose={() => blocker.reset?.()}>
      <DialogTitle>Discard unsaved scope changes?</DialogTitle>
      <DialogContent>Your current selection has not been saved. Leave this page and discard the draft?</DialogContent>
      <DialogActions><Button onClick={() => blocker.reset?.()}>Stay</Button><Button color="error" onClick={() => blocker.proceed?.()}>Leave page</Button></DialogActions>
    </Dialog>
  </PageContainer></MonitoringConfigurationWizardLayout>;
}
