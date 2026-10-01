import { apiRequest } from '../../../shared/utils/apiClient';
import type { AuthorPoliciesResponse, AuthorPolicy, GitLabBranch } from '../types/authorPolicies';

const root = (configurationId: string) => `/monitoring-configurations/${encodeURIComponent(configurationId)}/author-policies`;
export const authorPoliciesApi = {
  list: (configurationId: string, signal?: AbortSignal) =>
    apiRequest<AuthorPoliciesResponse>(root(configurationId), { signal }),
  branches: (configurationId: string, projectId: number, signal?: AbortSignal) =>
    apiRequest<{ items: GitLabBranch[] }>(`${root(configurationId)}/repositories/${projectId}/branches`, { signal }),
  saveGroup: (configurationId: string, groupId: number, emails: string[], revision: number) =>
    apiRequest<{ id: string; scope_type: 'group'; allowed_author_emails: string[]; configuration_revision: number }>(
      `${root(configurationId)}/groups/${groupId}`, { method: 'PUT', headers: { 'If-Match': `"${revision}"` },
        body: JSON.stringify({ allowed_author_emails: emails }) }),
  saveRepositoryBranch: (configurationId: string, projectId: number, branch: string, emails: string[], revision: number) =>
    apiRequest<{ id: string; scope_type: 'repository_branch'; allowed_author_emails: string[]; configuration_revision: number }>(
      `${root(configurationId)}/repositories/${projectId}/branches`, { method: 'PUT', headers: { 'If-Match': `"${revision}"` },
        body: JSON.stringify({ branch, allowed_author_emails: emails }) }),
  remove: (configurationId: string, policyId: string, revision: number) =>
    apiRequest<void>(`${root(configurationId)}/${policyId}`, { method: 'DELETE', headers: { 'If-Match': `"${revision}"` } }),
  migrate: (configurationId: string, revision: number) =>
    apiRequest<AuthorPoliciesResponse>(`${root(configurationId)}/migration`, { method: 'POST',
      headers: { 'If-Match': `"${revision}"` }, body: JSON.stringify({}) }),
};

export function withSavedPolicy(policies: AuthorPolicy[], id: string, scopeType: AuthorPolicy['scope_type'],
  emails: string[], scopeId: number, name: string, path: string, branch: string | null): AuthorPolicy[] {
  const found = policies.some(policy => policy.id === id);
  if (found) return policies.map(policy => policy.id === id ? { ...policy, allowed_author_emails: emails } : policy);
  return [...policies, { id, scope_type: scopeType, active: true, gitlab_instance_fingerprint: '',
    gitlab_group_id: scopeType === 'group' ? scopeId : null,
    gitlab_project_id: scopeType === 'repository_branch' ? scopeId : null,
    scope_name: name, scope_path: path, branch, allowed_author_emails: emails }];
}
