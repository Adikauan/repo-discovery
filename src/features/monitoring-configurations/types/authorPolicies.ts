export type AuthorPolicyMode = 'legacy' | 'scope_aware';
export type AuthorPolicyScopeType = 'group' | 'repository_branch';

export interface AuthorPolicy {
  id: string;
  scope_type: AuthorPolicyScopeType;
  active: boolean;
  gitlab_instance_fingerprint: string;
  gitlab_group_id: number | null;
  gitlab_project_id: number | null;
  scope_name: string;
  scope_path: string;
  branch: string | null;
  allowed_author_emails: string[];
}

export interface AuthorPoliciesResponse {
  mode: AuthorPolicyMode;
  legacy_fallback: { active: boolean; allowed_author_emails: string[] };
  policies: AuthorPolicy[];
  repositories: { gitlab_project_id: number; name: string; full_path: string; source: 'direct' | 'group'; status: 'configured' | 'policy_required' }[];
  configuration_revision: number;
}

export interface GitLabBranch { name: string; commit_sha: string; default: boolean }
