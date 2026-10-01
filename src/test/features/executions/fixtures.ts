import type { ExecutionDetail, ExecutionPage } from '../../../features/executions/types/execution';
export const historicalExecutionDetail: ExecutionDetail = {
  id: 'execution-1', monitoringConfigurationId: 'config-1', configurationName: 'Historical platform',
  triggerType: 'manual', status: 'completed', createdAt: '2026-09-29T12:00:00Z',
  startedAt: '2026-09-29T12:00:00Z', completedAt: '2026-09-29T12:00:01Z', durationSeconds: 1,
  findingCount: 0,
  snapshot: { configurationId: 'config-1', configurationName: 'Historical platform', configurationEnabled: false,
    gitlabUrl: 'https://historical.gitlab.example.com', configurationRevision: 2,
    scope: { groups: [{ gitlabGroupId: 1, name: 'Platform', fullPath: 'platform' }],
      repositories: [{ gitlabProjectId: 2, name: 'Service', fullPath: 'platform/service' }] } },
  counters: { repositoryCount: 0, successfulRepositoryCount: 0, failedRepositoryCount: 0, findingCount: 0 },
  error: null, scopeResolutionFailureCount: 0, completionMeaning: 'Repository processing completed successfully; the effective scope contained no repositories.',
};
export const execution = historicalExecutionDetail;
export const page: ExecutionPage = { items: [execution], page: 1, pageSize: 25, totalItems: 1, totalPages: 1 };
export function response(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }); }
export const liveMonitoringConfiguration = { id: 'config-1', name: 'CURRENT live configuration', description: 'Different live scope', gitlab_url: 'https://current.gitlab.example.com', enabled: true, created_at: execution.createdAt, updated_at: execution.createdAt, version: '99', scope: { groups: ['current-group'], repositories: ['current-repository'] } };
export const configuration = liveMonitoringConfiguration;
export function mockOtherRequests(url: string) {
  if (url.endsWith('/gitlab-connection')) return response({ credentialConfigured: false, validationState: 'not_configured' });
  if (url.endsWith('/schedule')) return response({ configured: false, version: '0', schedule: null, nextOccurrence: null });
  if (/\/executions\/[^/]+\/repositories(?:\?|$)/.test(url)) return response({ items: [], page: 1, pageSize: 25, totalItems: 0, totalPages: 0 });
  if (url.includes('/executions/')) return response(execution);
  if (url.includes('/executions')) return response(page);
  return response(configuration);
}
