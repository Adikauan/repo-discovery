import { apiRequest } from '../../../shared/utils/apiClient';
import type { FindingPage } from '../types/finding';
import type { FindingDiffResponse } from '../types/findingDiff';

export const findingsApi = {
  listForExecution: (executionId: string, page = 1, signal?: AbortSignal) =>
    apiRequest<FindingPage>(`/executions/${encodeURIComponent(executionId)}/findings?page=${page}&pageSize=25`, { signal }),
  getCommitDiff: (findingId: string, signal?: AbortSignal) =>
    apiRequest<FindingDiffResponse>(`/findings/${encodeURIComponent(findingId)}/diff`, { signal }),
};
