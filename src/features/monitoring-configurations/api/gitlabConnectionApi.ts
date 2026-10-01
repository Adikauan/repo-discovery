import { apiRequest } from '../../../shared/utils/apiClient';
import type { GitLabConnectionStatus, GitLabValidationResponse } from '../types/gitlabConnection';
export interface GitLabCandidateValidationResponse { state: 'validated' | 'failed'; result: string; message: string; checked_at: string; }
const root = (id: string) => `/monitoring-configurations/${encodeURIComponent(id)}/gitlab-connection`;
export const gitlabConnectionApi = {
  status: (id: string, signal?: AbortSignal) => apiRequest<GitLabConnectionStatus>(root(id), { signal }),
  save: (id: string, token: string, signal?: AbortSignal) => apiRequest<GitLabConnectionStatus>(`${root(id)}/credential`, { method: 'PUT', body: JSON.stringify({ token }), signal }),
  remove: (id: string, signal?: AbortSignal) => apiRequest<void>(`${root(id)}/credential`, { method: 'DELETE', signal }),
  validateSaved: (id: string, signal?: AbortSignal) => apiRequest<GitLabValidationResponse>(`${root(id)}/validate`, { method: 'POST', body: JSON.stringify({}), signal }),
  validateCandidate: (id: string, token: string, signal?: AbortSignal) => apiRequest<GitLabValidationResponse>(`${root(id)}/validate`, { method: 'POST', body: JSON.stringify({ token }), signal }),
  validateUnpersistedCandidate: (gitlabUrl: string, token: string, signal?: AbortSignal) => apiRequest<GitLabCandidateValidationResponse>('/gitlab-connections/validate-candidate', { method: 'POST', body: JSON.stringify({ gitlab_url: gitlabUrl, token }), signal }),
};
