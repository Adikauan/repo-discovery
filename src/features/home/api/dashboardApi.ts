import { apiRequest } from '../../../shared/utils/apiClient';

export type DashboardSummary = {
  window: { start: string; end: string; timezone: 'UTC' };
  metrics: { executionCount: number; repositoriesProcessed: number; findingCount: number; successRatePercent: number | null; terminalExecutionCount: number };
  statusDistribution: Record<'pending' | 'running' | 'completed' | 'partiallyCompleted' | 'failed', number>;
  dailyExecutions: Array<{ date: string; count: number }>;
  recentExecutions: Array<{ id: string; configurationName: string; status: string; triggerType: string; createdAt: string; startedAt: string | null; completedAt: string | null; durationSeconds: number | null; findingCount: number }>;
  findingsByRule: Array<{ ruleId: string; label: string; count: number }>;
};

export const dashboardApi = {
  summary: (signal?: AbortSignal) => apiRequest<DashboardSummary>('/dashboard/summary', { signal }),
};
