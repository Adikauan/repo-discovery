import type { PresentationStatus } from '../../../shared/types/presentation';
export const monitoringFixtures: Array<{ id: string; name: string; target: string; lastRun: string; nextRun: string; status: PresentationStatus }> = [
  { id: 'platform', name: 'Platform workspace', target: 'gitlab.example / platform', lastRun: 'Presentation sample', nextRun: 'Not scheduled', status: 'active' },
  { id: 'libraries', name: 'Shared libraries', target: 'gitlab.example / libraries', lastRun: 'Presentation sample', nextRun: 'Not scheduled', status: 'paused' },
  { id: 'legacy', name: 'Legacy projects', target: 'No connection', lastRun: 'Never', nextRun: 'Not scheduled', status: 'disabled' },
];
