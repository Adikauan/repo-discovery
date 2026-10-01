import { useEffect, useRef, useState } from 'react';
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle } from '@mui/material';
import { useBlocker, useNavigate, useParams } from 'react-router-dom';
import { ContentCard } from '../../../shared/components/layout/ContentCard';
import { PageContainer } from '../../../shared/components/layout/PageContainer';
import { PageHeader } from '../../../shared/components/layout/PageHeader';
import { ErrorState } from '../../../shared/components/feedback/ErrorState';
import { LoadingState } from '../../../shared/components/feedback/LoadingState';
import { ApiError } from '../../../shared/utils/apiClient';
import { monitoringConfigurationsApi } from '../api/monitoringConfigurationsApi';
import { MonitoringConfigurationForm } from '../components/MonitoringConfigurationForm';
import { ConfigurationWizardProgress } from '../components/ConfigurationWizardProgress';
import { MonitoringConfigurationWizardLayout } from '../components/MonitoringConfigurationWizardLayout';
import type { MonitoringConfiguration, ConfigurationInput } from '../model/monitoringConfiguration';

const FORM_ID = 'edit-monitoring-configuration-general-form';

export function EditMonitoringConfigurationPage() {
  const { id = '' } = useParams(); const navigate = useNavigate();
  const [item, setItem] = useState<MonitoringConfiguration>(); const [etag, setEtag] = useState('');
  const [loading, setLoading] = useState(true); const [error, setError] = useState(''); const [retry, setRetry] = useState(0); const [dirty, setDirty] = useState(false);
  const allowNext = useRef(false);
  const blocker = useBlocker(({ nextLocation }) => dirty && !(allowNext.current && nextLocation.pathname === `/monitoring-configurations/${id}/gitlab-connection`));
  useEffect(() => {
    const beforeUnload = (event: BeforeUnloadEvent) => { if (!dirty) return; event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', beforeUnload);
    return () => window.removeEventListener('beforeunload', beforeUnload);
  }, [dirty]);
  useEffect(() => { let live = true; setLoading(true); setError(''); monitoringConfigurationsApi.get(id).then(result => { if (live) { setItem(result.data); setEtag(result.etag ?? `"${result.data.version}"`); } }).catch((e: unknown) => { if (live) setError(e instanceof ApiError ? e.message : 'Unable to load this configuration.'); }).finally(() => { if (live) setLoading(false); }); return () => { live = false; }; }, [id, retry]);
  async function save(values: ConfigurationInput) {
    setError('');
    try { await monitoringConfigurationsApi.update(id, values, etag); allowNext.current = true; setDirty(false); navigate(`/monitoring-configurations/${id}/gitlab-connection`); }
    catch (e) { if (e instanceof ApiError && e.status === 412) setError('This configuration changed since you opened it. Your edits are still here; reload the latest values and reapply your changes.'); else setError(e instanceof ApiError ? e.message : 'Unable to save the configuration.'); }
  }
  function next() { (document.getElementById(FORM_ID) as HTMLFormElement | null)?.requestSubmit(); }
  return <MonitoringConfigurationWizardLayout step={0} next={next} nextLabel="GitLab Connection">
    <PageContainer><PageHeader title="General" description="Set the name, description, and enabled state for this configuration."
      breadcrumbs={[{ label: 'Monitoring Configurations', path: '/monitoring-configurations' }, { label: item?.name ?? 'Configuration', current: true }, { label: 'General', current: true }]} />
      {loading ? <LoadingState message="Loading configuration…" /> : error && !item ? <ErrorState message={error} action={<Button onClick={() => { setError(''); setRetry(x => x + 1); }}>Retry</Button>} /> : item ? <ContentCard>
        <ConfigurationWizardProgress configurationId={id} currentStep={0} />
        <MonitoringConfigurationForm formId={FORM_ID} initial={{ ...item, description: item.description ?? '' }} submitLabel="Save and continue"
          onSubmit={save} error={error} showEnabled configurationId={id} showActions={false} onDirtyChange={setDirty} />
      </ContentCard> : null}
      <Dialog open={blocker.state === 'blocked'} onClose={() => blocker.reset?.()} aria-labelledby="discard-general-title">
        <DialogTitle id="discard-general-title">Discard unsaved General changes?</DialogTitle><DialogContent>Your changes have not been saved.</DialogContent>
        <DialogActions><Button onClick={() => blocker.reset?.()}>Stay</Button><Button color="error" onClick={() => blocker.proceed?.()}>Discard changes</Button></DialogActions>
      </Dialog>
    </PageContainer>
  </MonitoringConfigurationWizardLayout>;
}
