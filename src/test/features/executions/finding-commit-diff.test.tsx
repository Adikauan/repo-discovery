import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import axe from 'axe-core';
import userEvent from '@testing-library/user-event';
import { ExecutionFindingsSection } from '../../../features/executions/components/ExecutionFindingsSection';

const finding = {
  id: 'finding-1', repositoryExecutionId: 'repo-1', repositoryFullPath: 'team/repo',
  ruleId: 'unauthorized-commit-author', ruleVersion: '1', severity: 'warning' as const,
  title: 'Unauthorized commit author', summary: 'Unauthorized author', commitHash: 'a'.repeat(40),
  authorEmail: 'writer@example.com', authorEmailState: 'valid' as const, authorName: 'Writer',
  authoredAt: '2026-09-30T10:00:00Z', commitMessageSummary: 'Change source', filePath: null,
  lineStart: null, lineEnd: null, createdAt: '2026-09-30T10:00:00Z',
};
const list = { items: [finding], page: 1, pageSize: 25, totalItems: 1, totalPages: 1 };
function diff(filesCompleteness: 'complete' | 'truncated' | 'unknown') {
  return { findingId: finding.id, repositoryName: 'repo', repositoryNameTruncated: false,
    repositoryFullPath: 'team/repo', repositoryFullPathTruncated: false, commitHash: finding.commitHash,
    authorName: 'Writer', authorEmail: 'writer@example.com', authoredAt: finding.authoredAt,
    commitMessageSummary: 'Change source', filesCompleteness, files: [{ oldPath: 'src/a.ts', newPath: 'src/a.ts',
      changeType: 'modified', diff: '@@ -1 +1 @@\n-old\n+new\n', textDiffAvailable: true, binary: null,
      collapsed: false, tooLarge: false, diffTruncated: false, oldPathTruncated: false, newPathTruncated: false }] };
}
function setup(completeness: 'complete' | 'truncated' | 'unknown' = 'complete', payload = diff(completeness)) {
  const fetcher = vi.fn().mockImplementation((url: string) => Promise.resolve({ ok: true, status: 200,
    headers: new Headers(), json: async () => String(url).includes('/diff') ? payload : list }));
  vi.stubGlobal('fetch', fetcher);
  render(<ExecutionFindingsSection executionId="execution-1" />);
  return fetcher;
}

describe('finding commit diff dialog', () => {
  it('does not fetch diffs until the Difference action is activated and displays split commit changes', async () => {
    const fetcher = setup();
    await screen.findByText('Unauthorized author');
    expect(fetcher.mock.calls.filter(([url]) => String(url).includes('/diff'))).toHaveLength(0);
    const trigger = screen.getByRole('button', { name: 'View commit diff' });
    expect(trigger.querySelector('[data-testid="DifferenceIcon"]')).toBeInTheDocument();
    fireEvent.mouseOver(trigger);
    expect(await screen.findByRole('tooltip')).toHaveTextContent('View diff');
    fireEvent.click(trigger);
    expect(await screen.findByRole('dialog', { name: 'Commit changes' })).toBeInTheDocument();
    const dialog = screen.getByRole('dialog', { name: 'Commit changes' });
    expect(dialog.style.width).toContain('95vw');
    expect(dialog.style.width).toContain('100vw');
    expect(dialog.style.maxWidth).toBe('1800px');
    expect(dialog.style.height).toContain('90vh');
    expect(dialog.style.height).toContain('100vh');
    expect(dialog.style.maxHeight).toContain('100vh');
    expect(await screen.findByRole('heading', { name: 'src/a.ts' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Before (previous version)' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'After (new version)' })).toBeInTheDocument();
    expect(screen.getByRole('group', { name: 'Modified. Removed line 1: old. Added line 1: new.' })).toBeInTheDocument();
    const body = screen.getByTestId('changed-files-and-diff');
    expect(body).toHaveStyle({ display: 'flex', flexDirection: 'row' });
    expect(body).toContainElement(screen.getByRole('list', { name: 'Changed files' }));
    const viewer = screen.getByRole('region', { name: 'Split diff content' });
    expect(body).toContainElement(viewer);
    expect(viewer).toHaveStyle({ overflow: 'auto' });
    expect(fetcher.mock.calls.filter(([url]) => String(url).includes('/diff'))).toHaveLength(1);
  });

  it('lets keyboard-accessible file controls select each file patch', async () => {
    const payload = diff('complete');
    payload.files.push({ ...payload.files[0], oldPath: 'src/b.ts', newPath: 'src/b.ts', diff: '@@ -0,0 +1 @@\n+second file' });
    const fetcher = vi.fn().mockImplementation((url: string) => Promise.resolve({ ok: true, status: 200,
      headers: new Headers(), json: async () => String(url).includes('/diff') ? payload : list }));
    vi.stubGlobal('fetch', fetcher);
    render(<ExecutionFindingsSection executionId="execution-1" />);
    await screen.findByText('Unauthorized author');
    fireEvent.click(screen.getByRole('button', { name: 'View commit diff' }));
    const secondFile = await screen.findByRole('button', { name: /src\/b\.ts/ });
    secondFile.focus();
    await userEvent.setup().keyboard('{Enter}');
    expect(secondFile).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('src/b.ts', { selector: 'h3' })).toBeInTheDocument();
    expect(screen.getByRole('group', { name: 'Added line 1: second file.' })).toBeInTheDocument();
    expect(fetcher.mock.calls.filter(([url]) => String(url).includes('/diff'))).toHaveLength(1);
  });

  it.each([
    ['binary', { binary: true, textDiffAvailable: false }, 'Text diff is unavailable for this binary file.'],
    ['too large', { tooLarge: true, textDiffAvailable: false }, 'GitLab marked this file diff as too large to return.'],
    ['collapsed', { collapsed: true, textDiffAvailable: false }, 'GitLab collapsed this file diff.'],
    ['truncated', { diffTruncated: true, diff: '@@ -1,2 +1,2 @@\n-old\n+new' }, 'The available text diff was truncated to fit the response limit.'],
  ] as const)('preserves the Feature 011 %s file state', async (_state, changes, message) => {
    const payload = diff('complete');
    Object.assign(payload.files[0], changes);
    setup('complete', payload);
    await screen.findByText('Unauthorized author');
    fireEvent.click(screen.getByRole('button', { name: 'View commit diff' }));
    expect(await screen.findByRole('heading', { name: 'src/a.ts' })).toBeInTheDocument();
    expect(await screen.findByText(message)).toBeInTheDocument();
    if (_state === 'truncated') expect(screen.getByRole('group', { name: /Modified\. Removed line 1/ })).toBeInTheDocument();
    else expect(screen.queryByRole('region', { name: 'Split diff content' })).not.toBeInTheDocument();
  });

  it.each([
    ['added', null, 'src/new.ts'],
    ['deleted', 'src/old.ts', null],
    ['renamed', 'src/before.ts', 'src/after.ts'],
  ] as const)('retains the %s file identity in the sidebar and selected-file header', async (changeType, oldPath, newPath) => {
    const payload = diff('complete');
    Object.assign(payload.files[0], { changeType, oldPath, newPath });
    setup('complete', payload);
    await screen.findByText('Unauthorized author');
    fireEvent.click(screen.getByRole('button', { name: 'View commit diff' }));
    expect(await screen.findByRole('heading', { name: newPath && oldPath ? `${oldPath} → ${newPath}` : newPath ?? oldPath ?? '' })).toBeInTheDocument();
    const fileButton = screen.getByRole('button', { name: new RegExp(changeType) });
    expect(fileButton).toHaveAttribute('aria-expanded', 'true');
  });

  it.each([
    ['complete', null],
    ['truncated', 'Additional changed files were omitted.'],
    ['unknown', 'GitLab did not provide enough information to confirm whether all changed files were returned.'],
  ] as const)('communicates %s file-list completeness truthfully', async (state, message) => {
    setup(state);
    await screen.findByText('Unauthorized author');
    fireEvent.click(screen.getByRole('button', { name: 'View commit diff' }));
    await screen.findByRole('dialog', { name: 'Commit changes' });
    if (message) expect(await screen.findByText(message)).toBeInTheDocument();
    else await waitFor(() => expect(screen.queryByText(/Additional changed files|GitLab did not provide/)).not.toBeInTheDocument());
  });

  it('closes by keyboard and leaves Findings available', async () => {
    setup();
    await screen.findByText('Unauthorized author');
    const trigger = screen.getByRole('button', { name: 'View commit diff' });
    trigger.focus();
    await userEvent.setup().keyboard('{Enter}');
    await screen.findByRole('dialog', { name: 'Commit changes' });
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    await waitFor(() => expect(trigger).toHaveFocus());
    expect(trigger).toBeInTheDocument();
  });

  it('does not offer a diff action for findings without the supported rule context', async () => {
    const unsupported = { ...finding, ruleId: 'other-rule', commitHash: null };
    const fetcher = vi.fn().mockImplementation(() => Promise.resolve({ ok: true, status: 200, headers: new Headers(), json: async () => ({ ...list, items: [unsupported] }) }));
    vi.stubGlobal('fetch', fetcher);
    render(<ExecutionFindingsSection executionId="execution-1" />);
    await screen.findByText('Unauthorized author');
    expect(screen.queryByRole('button', { name: 'View commit diff' })).not.toBeInTheDocument();
    expect(fetcher.mock.calls.some(([url]) => String(url).includes('/diff'))).toBe(false);
  });

  it('keeps the dialog retryable after a normalized error and restores focus', async () => {
    const fetcher = vi.fn().mockImplementationOnce(() => Promise.resolve({ ok: true, status: 200, headers: new Headers(), json: async () => list }))
      .mockImplementationOnce(() => Promise.resolve({ ok: false, status: 503, json: async () => ({ code: 'commit_diff_unavailable', detail: 'The commit diff is temporarily unavailable. Try again.' }) }))
      .mockImplementationOnce(() => Promise.resolve({ ok: true, status: 200, headers: new Headers(), json: async () => diff('complete') }));
    vi.stubGlobal('fetch', fetcher);
    render(<ExecutionFindingsSection executionId="execution-1" />);
    await screen.findByText('Unauthorized author');
    const trigger = screen.getByRole('button', { name: 'View commit diff' });
    trigger.focus();
    fireEvent.click(trigger);
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load commit changes. Try again.');
    expect(screen.queryByText('raw provider exception')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    await screen.findByRole('heading', { name: 'src/a.ts' });
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it('explains a missing historical commit without offering a futile retry', async () => {
    const fetcher = vi.fn().mockImplementationOnce(() => Promise.resolve({ ok: true, status: 200, headers: new Headers(), json: async () => list }))
      .mockImplementationOnce(() => Promise.resolve({ ok: false, status: 404, json: async () => ({ code: 'commit_not_found', detail: 'The commit associated with this Finding could not be found.' }) }));
    vi.stubGlobal('fetch', fetcher);
    render(<ExecutionFindingsSection executionId="execution-1" />);
    await screen.findByText('Unauthorized author');
    fireEvent.click(screen.getByRole('button', { name: 'View commit diff' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('GitLab could not find this commit. The Finding remains available, but its changes cannot be loaded.');
    expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument();
    expect(screen.getByText('Unauthorized author')).toBeInTheDocument();
    expect(screen.getByRole('dialog')).toHaveTextContent(finding.commitHash);
  });

  it('runs an accessibility scan on the opened diff dialog', async () => {
    setup();
    await screen.findByText('Unauthorized author');
    fireEvent.click(screen.getByRole('button', { name: 'View commit diff' }));
    await screen.findByRole('heading', { name: 'src/a.ts' });
    const result = await axe.run(screen.getByRole('dialog'), {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'] },
      rules: { 'color-contrast': { enabled: false } },
    });
    expect(result.violations).toEqual([]);
  });
});
