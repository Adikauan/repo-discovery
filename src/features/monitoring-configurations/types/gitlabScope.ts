export type GitLabScopeNodeType = 'group' | 'repository';
export type ScopeAvailability = 'available' | 'unavailable' | 'unresolved' | 'stale';

export interface GitLabScopeNode {
  id: number;
  type: GitLabScopeNodeType;
  name: string;
  full_path: string;
  parent_group_id?: number | null;
  expandable: boolean;
}

export interface GitLabScopeRule {
  selection_id: string;
  gitlab_id: number;
  name: string;
  full_path: string;
  parent_group_id?: number | null;
  availability: ScopeAvailability;
}

export interface GitLabScope {
  groups: GitLabScopeRule[];
  repositories: GitLabScopeRule[];
  stale: boolean;
}

export interface GitLabScopeSelectionInput {
  selection_id?: string;
  gitlab_id: number;
}

export interface GitLabScopeInput {
  groups: GitLabScopeSelectionInput[];
  repositories: GitLabScopeSelectionInput[];
}

export interface GitLabScopeDraft {
  groups: GitLabScopeRule[];
  repositories: GitLabScopeRule[];
}
