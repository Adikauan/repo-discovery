import { useParams } from 'react-router-dom';
import { PageContainer } from '../../../shared/components/layout/PageContainer';
import { PageHeader } from '../../../shared/components/layout/PageHeader';
import { ExecutionHistory } from '../../executions/components/ExecutionHistory';
export function ConfigurationExecutionsPage() {
  const { id = '' } = useParams();
  return <PageContainer><PageHeader title="Configuration Executions" description="Historical executions remain available after configuration retirement."
    breadcrumbs={[{ label: 'Monitoring Configurations', path: '/monitoring-configurations' }, { label: 'Configuration', path: '/monitoring-configurations/' + id }, { label: 'Executions', current: true }]} />
    <ExecutionHistory key={id} configurationId={id} /></PageContainer>;
}
