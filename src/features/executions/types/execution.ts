export type TriggerType = 'manual' | 'scheduled';
export type ExecutionStatus = 'pending' | 'running' | 'completed' | 'partially_completed' | 'failed';
export interface ExecutionListItem {
  id: string; monitoringConfigurationId: string; configurationName: string;
  triggerType: TriggerType; status: ExecutionStatus;
  createdAt: string; startedAt: string | null; completedAt: string | null; durationSeconds: number | null;
  findingCount: number;
}
export interface ExecutionSnapshot {
  configurationId: string; configurationName: string; configurationEnabled: boolean;
  gitlabUrl: string; configurationRevision: number | null;
  scope: {
    groups: { gitlabGroupId: number; name: string; fullPath: string }[];
    repositories: { gitlabProjectId: number; name: string; fullPath: string }[];
  };
}
export interface ExecutionDetail extends ExecutionListItem {
  snapshot: ExecutionSnapshot;
  counters: { repositoryCount: number; successfulRepositoryCount: number; failedRepositoryCount: number; findingCount: number };
  scopeResolutionFailureCount: number;
  error: { code: string; summary: string } | null;
  completionMeaning: string | null;
}
export interface RepositoryExecution {
  id: string; miningExecutionId: string; gitlabProjectId: number; repositoryName: string;
  repositoryFullPath: string; status: 'pending' | 'running' | 'completed' | 'failed';
  startedAt: string | null; completedAt: string | null; processedBranch: string | null;
  fileCount: number; observedExtensions: string[]; extensionsTruncated: boolean;
  findingCount: number; error: { code: string; summary: string } | null;
}
export interface RepositoryExecutionPage { items: RepositoryExecution[]; page: number; pageSize: number; totalItems: number; totalPages: number }
export interface ExecutionPage { items: ExecutionListItem[]; page: number; pageSize: number; totalItems: number; totalPages: number }
export interface ExecutionFilters { page?: number; pageSize?: number; status?: ExecutionStatus; triggerType?: TriggerType; monitoringConfigurationId?: string }
