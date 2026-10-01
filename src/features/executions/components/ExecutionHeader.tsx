import { Button, Stack } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import { PageHeader } from '../../../shared/components/layout/PageHeader';
import { ExecutionBadge } from './ExecutionHistory';
import type { ExecutionDetail } from '../types/execution';

export function ExecutionHeader({ execution, returnTo, onRefresh, refreshing = false }: {
  execution: ExecutionDetail; returnTo: string; onRefresh?: () => void; refreshing?: boolean;
}) {
  return <PageHeader
    title={`Execution ${execution.id}`}
    description={`Historical configuration: ${execution.snapshot.configurationName} · Trigger: ${execution.triggerType === 'manual' ? 'Manual' : 'Scheduled'}`}
    status={<ExecutionBadge status={execution.status} />}
    action={<Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}><Button component={RouterLink} to={returnTo}>Execution history</Button>{onRefresh && <Button onClick={onRefresh} disabled={refreshing} aria-busy={refreshing}>{refreshing ? 'Refreshing…' : 'Refresh execution'}</Button>}</Stack>}
  />;
}
