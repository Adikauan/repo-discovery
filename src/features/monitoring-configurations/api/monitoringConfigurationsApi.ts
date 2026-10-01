import { apiRequest } from '../../../shared/utils/apiClient';
import type { ConfigurationInput, CreateConfigurationInput, MonitoringConfiguration, MonitoringConfigurationList } from '../model/monitoringConfiguration';

const root = '/monitoring-configurations';
export const monitoringConfigurationsApi = {
  list: (search = '', signal?: AbortSignal) => apiRequest<MonitoringConfigurationList>(`${root}${search.trim() ? `?search=${encodeURIComponent(search.trim())}` : ''}`, { signal }),
  get: (id: string) => apiRequest<MonitoringConfiguration>(`${root}/${encodeURIComponent(id)}`),
  create: (body: CreateConfigurationInput, idempotencyKey?: string) => apiRequest<MonitoringConfiguration>(root, { method: 'POST', headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined, body: JSON.stringify(body) }),
  update: (id: string, body: ConfigurationInput, etag: string) => apiRequest<MonitoringConfiguration>(`${root}/${encodeURIComponent(id)}`, { method: 'PUT', headers: { 'If-Match': etag }, body: JSON.stringify(body) }),
  remove: (id: string) => apiRequest<void>(`${root}/${encodeURIComponent(id)}`, { method: 'DELETE' }),
};
