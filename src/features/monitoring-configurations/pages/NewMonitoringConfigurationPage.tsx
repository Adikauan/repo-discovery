import { useEffect, useRef, useState } from 'react';
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle } from '@mui/material';
import { useNavigate, useBlocker } from 'react-router-dom';
import { ContentCard } from '../../../shared/components/layout/ContentCard';
import { PageContainer } from '../../../shared/components/layout/PageContainer';
import { PageHeader } from '../../../shared/components/layout/PageHeader';
import { MonitoringConfigurationForm } from '../components/MonitoringConfigurationForm';
import { ConfigurationWizardProgress } from '../components/ConfigurationWizardProgress';
import { MonitoringConfigurationWizardLayout } from '../components/MonitoringConfigurationWizardLayout';
import { useMonitoringConfigurationWizard } from '../context/MonitoringConfigurationWizardContext';
import type { ConfigurationInput } from '../model/monitoringConfiguration';

const FORM_ID = 'new-monitoring-configuration-general-form';

export function NewMonitoringConfigurationPage() {
  const navigate = useNavigate();
  const wizard = useMonitoringConfigurationWizard();
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState('');
  const allowDraftAdvance = useRef(false);
  const blocker = useBlocker(({ nextLocation }) => dirty && !(
    allowDraftAdvance.current && nextLocation.pathname === '/monitoring-configurations/new/gitlab-connection'
  ));
  useEffect(() => {
    const beforeUnload = (event: BeforeUnloadEvent) => { if (!dirty) return; event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', beforeUnload);
    return () => window.removeEventListener('beforeunload', beforeUnload);
  }, [dirty]);
  async function stage(values: ConfigurationInput) {
    if (!values.name.trim()) { setError('Enter a configuration name.'); return; }
    wizard.setGeneral({ name: values.name.trim(), description: values.description?.trim() ?? '', enabled: false });
    allowDraftAdvance.current = true;
    setDirty(false);
    setError('');
    navigate('/monitoring-configurations/new/gitlab-connection');
  }
  function next() {
    const form = document.getElementById(FORM_ID) as HTMLFormElement | null;
    form?.requestSubmit();
  }
  return <MonitoringConfigurationWizardLayout next={next} nextLabel="GitLab Connection">
    <PageContainer>
      <PageHeader title="New Monitoring Configuration" description="Start with the configuration name and description."
        breadcrumbs={[{ label: 'Monitoring Configurations', path: '/monitoring-configurations' }, { label: 'New', current: true }]} />
      <ContentCard>
        <ConfigurationWizardProgress currentStep={0} />
        <MonitoringConfigurationForm formId={FORM_ID} initial={wizard.general ?? undefined} submitLabel="GitLab Connection"
          showActions={false} onSubmit={stage} onDirtyChange={setDirty} />
        {error && <Alert severity="error" role="alert" sx={{ mt: 2 }}>{error}</Alert>}
      </ContentCard>
      <Dialog open={blocker.state === 'blocked'} onClose={() => blocker.reset?.()} aria-labelledby="discard-new-configuration-title">
        <DialogTitle id="discard-new-configuration-title">Discard this configuration draft?</DialogTitle>
        <DialogContent>The General values have not been created yet. Leaving will discard this in-memory draft.</DialogContent>
        <DialogActions><Button onClick={() => blocker.reset?.()}>Stay</Button><Button color="error" onClick={() => { wizard.clear(); blocker.proceed?.(); }}>Discard draft</Button></DialogActions>
      </Dialog>
    </PageContainer>
  </MonitoringConfigurationWizardLayout>;
}
