import { useEffect, useState } from 'react';
import { Button } from '@mui/material';
import { useNavigate, useParams } from 'react-router-dom';
import { PageContainer } from '../../../shared/components/layout/PageContainer';
import { PageHeader } from '../../../shared/components/layout/PageHeader';
import { LoadingState } from '../../../shared/components/feedback/LoadingState';
import { ErrorState } from '../../../shared/components/feedback/ErrorState';
import { monitoringConfigurationsApi } from '../api/monitoringConfigurationsApi';
import { ScheduleSection } from '../components/ScheduleSection';
import { ConfigurationWizardProgress } from '../components/ConfigurationWizardProgress';
import { MonitoringConfigurationWizardLayout } from '../components/MonitoringConfigurationWizardLayout';
import type { MonitoringConfiguration } from '../model/monitoringConfiguration';

export function SchedulingPage() {
  const { id = '' } = useParams(); const navigate = useNavigate();
  const [configuration, setConfiguration] = useState<MonitoringConfiguration>();
  const [error, setError] = useState(''); const [retry, setRetry] = useState(0);
  useEffect(() => { let active = true; monitoringConfigurationsApi.get(id).then(result => { if (active) setConfiguration(result.data); })
    .catch(reason => { if (active) setError(reason instanceof Error ? reason.message : 'Unable to load this configuration.'); });
    return () => { active = false; }; }, [id, retry]);
  const save = () => (document.getElementById('monitoring-schedule-form') as HTMLFormElement | null)?.requestSubmit();
  return <MonitoringConfigurationWizardLayout step={4} previous={() => navigate(`/monitoring-configurations/${id}/authors`)}
    previousLabel="Policy" next={save} nextLabel="Save schedule" final>
    <PageContainer><PageHeader title="Scheduling" description="Configure automatic execution timing for this Monitoring Configuration."
      breadcrumbs={[{ label: 'Monitoring Configurations', path: '/monitoring-configurations' }, { label: configuration?.name ?? 'Configuration', path: `/monitoring-configurations/${id}` }, { label: 'Scheduling', current: true }]} />
      {error ? <ErrorState message={error} action={<Button onClick={() => { setError(''); setRetry(value => value + 1); }}>Retry</Button>} /> : !configuration ? <LoadingState message="Loading configuration…" /> : <>
        <ConfigurationWizardProgress configurationId={id} currentStep={4} />
        <ScheduleSection configurationId={id} configurationEnabled={configuration.enabled} showSaveButton={false}
          onSaveSuccess={() => navigate('/monitoring-configurations', { state: { notice: 'Monitoring Configuration saved successfully.' } })} />
      </>}
    </PageContainer>
  </MonitoringConfigurationWizardLayout>;
}
