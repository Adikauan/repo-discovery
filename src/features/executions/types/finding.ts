export interface Finding {
  id: string;
  repositoryExecutionId: string;
  repositoryFullPath: string;
  branch?: string | null;
  ruleId: string;
  ruleVersion: string;
  severity: 'warning';
  title: string;
  summary: string;
  commitHash: string;
  authorEmail: string | null;
  authorEmailState: 'valid' | 'missing' | 'malformed';
  authorName: string | null;
  authoredAt: string | null;
  commitMessageSummary: string | null;
  filePath: string | null;
  lineStart: number | null;
  lineEnd: number | null;
  createdAt: string;
}

export interface FindingPage { items: Finding[]; page: number; pageSize: number; totalItems: number; totalPages: number }
