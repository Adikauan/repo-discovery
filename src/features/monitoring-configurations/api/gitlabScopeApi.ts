import { apiRequest } from '../../../shared/utils/apiClient';
import type { GitLabScope, GitLabScopeInput, GitLabScopeNode } from '../types/gitlabScope';

const root = (id: string) => `/monitoring-configurations/${encodeURIComponent(id)}/gitlab-scope`;
export const gitlabScopeApi = {
  root: (id: string, signal?: AbortSignal) => apiRequest<{ nodes: GitLabScopeNode[] }>(`${root(id)}/root`, { signal }),
  children: (id: string, groupId: number, signal?: AbortSignal) =>
    apiRequest<{ nodes: GitLabScopeNode[] }>(`${root(id)}/groups/${groupId}/children`, { signal }),
  get: (id: string, signal?: AbortSignal) => apiRequest<GitLabScope>(root(id), { signal }),
  replace: (id: string, body: GitLabScopeInput, etag: string, signal?: AbortSignal) =>
    apiRequest<GitLabScope>(root(id), { method: 'PUT', headers: { 'If-Match': etag }, body: JSON.stringify(body), signal }),
};
