export type FilesCompleteness = 'complete' | 'truncated' | 'unknown';
export type FindingDiffFile = {
  oldPath: string | null;
  newPath: string | null;
  changeType: 'added' | 'modified' | 'deleted' | 'renamed' | null;
  diff: string | null;
  textDiffAvailable: boolean;
  binary: boolean | null;
  collapsed: boolean | null;
  tooLarge: boolean | null;
  diffTruncated: boolean;
  oldPathTruncated: boolean;
  newPathTruncated: boolean;
};
export type FindingDiffResponse = {
  findingId: string;
  repositoryName: string;
  repositoryNameTruncated: boolean;
  repositoryFullPath: string;
  repositoryFullPathTruncated: boolean;
  commitHash: string;
  authorName: string | null;
  authorEmail: string | null;
  authoredAt: string | null;
  commitMessageSummary: string | null;
  filesCompleteness: FilesCompleteness;
  files: FindingDiffFile[];
};
