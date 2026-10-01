import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ExecutionFindingsSection } from '../../../features/executions/components/ExecutionFindingsSection';

const finding = {
  id: 'finding-1', repositoryExecutionId: 'repo-exec-1', repositoryFullPath: 'team/sample',
  branch: 'release/stable',
  ruleId: 'unauthorized-commit-author', ruleVersion: '1', severity: 'warning',
  title: 'Unauthorized commit author', summary: 'Commit author (writer@example.com) is not in the allowed commit author list.',
  commitHash: 'a'.repeat(40), authorEmail: 'writer@example.com', authorEmailState: 'valid',
  authorName: 'Writer', authoredAt: '2026-09-30T10:00:00Z', commitMessageSummary: 'Update project',
  filePath: null, lineStart: null, lineEnd: null, createdAt: '2026-09-30T10:01:00Z',
};

function mockFetch(body: unknown, status = 200) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: status >= 200 && status < 300, status,
    headers: new Headers({ 'Content-Type': 'application/json' }), json: async () => body }));
}

describe('ExecutionFindingsSection', () => {
  it('shows persisted findings with accessible table headings and context', async () => {
    mockFetch({ items: [finding], page: 1, pageSize: 25, totalItems: 1, totalPages: 1 });
    render(<ExecutionFindingsSection executionId="exec-1" />);
    expect(await screen.findByText('writer@example.com')).toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'Execution findings' })).toBeInTheDocument();
    expect(screen.getByText('team/sample')).toBeInTheDocument();
    expect(screen.getByText('release/stable')).toBeInTheDocument();
    expect(screen.getByText('a'.repeat(40))).toBeInTheDocument();
    expect(screen.getByText(/not in the allowed commit author list/)).toBeInTheDocument();
  });

  it('labels legacy findings without recorded branch context safely', async () => {
    const { branch: _branch, ...legacyFinding } = finding;
    mockFetch({ items: [legacyFinding], page: 1, pageSize: 25, totalItems: 1, totalPages: 1 });
    render(<ExecutionFindingsSection executionId="exec-legacy" />);
    expect(await screen.findByText('Branch unavailable (historical context not recorded)')).toBeInTheDocument();
  });

  it('shows a real empty state for zero findings', async () => {
    mockFetch({ items: [], page: 1, pageSize: 25, totalItems: 0, totalPages: 0 });
    render(<ExecutionFindingsSection executionId="exec-1" />);
    expect(await screen.findByText('No findings detected')).toBeInTheDocument();
  });

  it('uses normalized error feedback and supports retry', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce({ ok: false, status: 500, json: async () => ({ detail: 'raw backend trace' }) })
      .mockResolvedValueOnce({ ok: true, status: 200, headers: new Headers(), json: async () => ({ items: [finding], page: 1, pageSize: 25, totalItems: 1, totalPages: 1 }) });
    vi.stubGlobal('fetch', fetcher);
    render(<ExecutionFindingsSection executionId="exec-1" />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load findings for this execution.');
    expect(screen.queryByText('raw backend trace')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    await waitFor(() => expect(screen.getByText('writer@example.com')).toBeInTheDocument());
  });
});
