import { apiRequest } from '../../../shared/utils/apiClient';
import type { ExecutionDetail, ExecutionFilters, ExecutionPage, RepositoryExecutionPage } from '../types/execution';

function query(filters: ExecutionFilters) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => { if (value !== undefined && value !== '') params.set(key, String(value)); });
  return params.size ? `?${params}` : '';
}
export const executionsApi = {
  create: (configurationId: string, idempotencyKey: string) => apiRequest<ExecutionDetail>(`/monitoring-configurations/${encodeURIComponent(configurationId)}/executions`, { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey } }),
  list: (filters: ExecutionFilters = {}, signal?: AbortSignal) => apiRequest<ExecutionPage>(`/executions${query(filters)}`, { signal }),
  listForConfiguration: (id: string, filters: ExecutionFilters = {}, signal?: AbortSignal) => apiRequest<ExecutionPage>(`/monitoring-configurations/${encodeURIComponent(id)}/executions${query(filters)}`, { signal }),
  get: (id: string) => apiRequest<ExecutionDetail>(`/executions/${encodeURIComponent(id)}`),
  repositories: (id: string, page = 1, signal?: AbortSignal) => apiRequest<RepositoryExecutionPage>(`/executions/${encodeURIComponent(id)}/repositories?page=${page}&pageSize=25`, { signal }),
};
