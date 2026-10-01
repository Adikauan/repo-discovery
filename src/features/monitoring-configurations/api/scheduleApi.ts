import { apiRequest } from '../../../shared/utils/apiClient';
import type { Schedule, ScheduleEnvelope, SchedulePreviewEnvelope } from '../types/schedule';

const root = '/monitoring-configurations';

export const scheduleApi = {
  get: (id: string) => apiRequest<ScheduleEnvelope>(`${root}/${encodeURIComponent(id)}/schedule`),
  timezones: () => apiRequest<{ timezones: string[] }>('/schedule-timezones'),
  replace: (id: string, schedule: Schedule, etag: string) => apiRequest<ScheduleEnvelope>(
    `${root}/${encodeURIComponent(id)}/schedule`,
    { method: 'PUT', headers: { 'If-Match': etag }, body: JSON.stringify(schedule) },
  ),
  preview: (id: string, schedule: Schedule) => apiRequest<SchedulePreviewEnvelope>(
    `${root}/${encodeURIComponent(id)}/schedule/preview`,
    { method: 'POST', body: JSON.stringify({ schedule }) },
  ),
  remove: (id: string, etag: string) => apiRequest<void>(
    `${root}/${encodeURIComponent(id)}/schedule`,
    { method: 'DELETE', headers: { 'If-Match': etag } },
  ),
};
