import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import axe from 'axe-core';
import { renderApp } from '../../renderApp';
import { execution, response } from './fixtures';

afterEach(() => {
  vi.unstubAllGlobals();
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1024 });
});

it('renders persisted repository summaries and safe failures from repository history', async () => {
  const rows = [{ id: 'r1', miningExecutionId: execution.id, gitlabProjectId: 10, repositoryName: 'service', repositoryFullPath: 'team/service', status: 'completed', startedAt: execution.startedAt, completedAt: execution.completedAt, processedBranch: 'trunk', fileCount: 7, observedExtensions: ['.py'], extensionsTruncated: false, findingCount: 0, error: null },
    { id: 'r2', miningExecutionId: execution.id, gitlabProjectId: 11, repositoryName: 'broken', repositoryFullPath: 'team/broken', status: 'failed', startedAt: execution.startedAt, completedAt: execution.completedAt, processedBranch: null, fileCount: 0, observedExtensions: [], extensionsTruncated: false, findingCount: 0, error: { code: 'repository_timeout', summary: 'The repository request timed out.' } }];
  const fetchMock = vi.fn().mockImplementation((url: string) => Promise.resolve(url.includes('/repositories')
    ? response({ items: rows, page: 1, pageSize: 25, totalItems: rows.length, totalPages: 1 }) : response(execution)));
  vi.stubGlobal('fetch', fetchMock);
  renderApp('/executions/execution-1');
  await screen.findByRole('heading', { name: 'Execution execution-1' });
  await userEvent.click(screen.getByRole('tab', { name: 'Repositories' }));
  expect(await screen.findByRole('table', { name: 'Repository processing results' })).toBeInTheDocument();
  expect(screen.getByText('team/service')).toBeInTheDocument();
  expect(screen.getByText('trunk')).toBeInTheDocument();
  expect(screen.getByText('7')).toBeInTheDocument();
  expect(screen.getByText('repository_timeout')).toBeInTheDocument();
  expect(screen.getByText('The repository request timed out.')).toBeInTheDocument();
  expect(fetchMock.mock.calls.every(([url]) => String(url).includes('/executions/'))).toBe(true);
});

it('keeps interrupted repository work visibly active and omits unpersisted summary', async () => {
  const activeExecution = { ...execution, status: 'running' as const, completedAt: null, durationSeconds: null };
  const pending = { id: 'r-pending', miningExecutionId: execution.id, gitlabProjectId: 12, repositoryName: 'worker', repositoryFullPath: 'team/worker', status: 'running', startedAt: execution.startedAt, completedAt: null, processedBranch: null, fileCount: 0, observedExtensions: [], extensionsTruncated: false, findingCount: 0, error: null };
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => Promise.resolve(url.includes('/repositories')
    ? response({ items: [pending], page: 1, pageSize: 25, totalItems: 1, totalPages: 1 }) : response(activeExecution))));
  renderApp('/executions/execution-1');
  await screen.findByRole('heading', { name: 'Execution execution-1' });
  await userEvent.click(screen.getByRole('tab', { name: 'Repositories' }));
  expect(await screen.findByText('team/worker')).toBeInTheDocument();
  expect(screen.getAllByText('Running').length).toBeGreaterThan(0);
  expect(screen.getAllByText('—').length).toBeGreaterThan(0);
  const row = screen.getByRole('row', { name: /team\/worker/ });
  expect(row).toHaveTextContent('Running');
  expect(row).not.toHaveTextContent('Completed');
  expect(screen.queryByText('Completed', { selector: 'span' })).not.toBeInTheDocument();
  expect(row).toHaveTextContent('0');
});

it('refreshes repository results with the dashboard refresh without changing tab', async () => {
  const first = { id: 'r', miningExecutionId: execution.id, gitlabProjectId: 12, repositoryName: 'service', repositoryFullPath: 'team/service', status: 'running', startedAt: execution.startedAt, completedAt: null, processedBranch: null, fileCount: 0, observedExtensions: [], extensionsTruncated: false, findingCount: 0, error: null };
  const second = { ...first, status: 'completed', completedAt: execution.completedAt, processedBranch: 'trunk', fileCount: 3 };
  let listCalls = 0;
  const fetchMock = vi.fn().mockImplementation((url: string) => {
    if (url.includes('/repositories')) return Promise.resolve(response({ items: [listCalls++ === 0 ? first : second], page: 1, pageSize: 25, totalItems: 1, totalPages: 1 }));
    return Promise.resolve(response(execution));
  });
  vi.stubGlobal('fetch', fetchMock);
  renderApp('/executions/execution-1');
  await screen.findByRole('heading', { name: 'Execution execution-1' });
  await userEvent.click(screen.getByRole('tab', { name: 'Repositories' }));
  await screen.findByText('team/service');
  await userEvent.click(screen.getByRole('button', { name: 'Refresh execution' }));
  await waitFor(() => expect(screen.getByRole('tab', { name: 'Repositories' })).toHaveAttribute('aria-selected', 'true'));
  await waitFor(() => expect(screen.getByText('trunk')).toBeInTheDocument());
  expect(fetchMock.mock.calls.filter(([url]) => String(url).includes('/repositories')).length).toBe(2);
});

it('provides accessible repository pagination and loads the next persisted page', async () => {
  const first = { id: 'r1', miningExecutionId: execution.id, gitlabProjectId: 1, repositoryName: 'one', repositoryFullPath: 'team/one', status: 'completed', startedAt: execution.startedAt, completedAt: execution.completedAt, processedBranch: 'main', fileCount: 1, observedExtensions: ['.py'], extensionsTruncated: false, findingCount: 0, error: null };
  const second = { ...first, id: 'r2', gitlabProjectId: 2, repositoryName: 'two', repositoryFullPath: 'team/two' };
  const fetchMock = vi.fn().mockImplementation((url: string) => Promise.resolve(url.includes('/repositories')
    ? response({ items: [url.includes('page=2') ? second : first], page: url.includes('page=2') ? 2 : 1, pageSize: 1, totalItems: 2, totalPages: 2 }) : response(execution)));
  vi.stubGlobal('fetch', fetchMock);
  renderApp('/executions/execution-1');
  await screen.findByRole('heading', { name: 'Execution execution-1' });
  await userEvent.click(screen.getByRole('tab', { name: 'Repositories' }));
  expect(await screen.findByText('team/one')).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Next page' }));
  expect(await screen.findByText('team/two')).toBeInTheDocument();
  const result = await axe.run(document.body, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'] }, rules: { 'color-contrast': { enabled: false } } });
  expect(result.violations).toEqual([]);
});

it('normalizes repository read errors and retries within the selected tab', async () => {
  const row = { id: 'r1', miningExecutionId: execution.id, gitlabProjectId: 1, repositoryName: 'one', repositoryFullPath: 'team/one', status: 'completed', startedAt: execution.startedAt, completedAt: execution.completedAt, processedBranch: 'main', fileCount: 1, observedExtensions: ['.py'], extensionsTruncated: false, findingCount: 0, error: null };
  let repositoryCalls = 0;
  const fetchMock = vi.fn().mockImplementation((url: string) => {
    if (url.includes('/repositories')) {
      repositoryCalls += 1;
      return Promise.resolve(repositoryCalls === 1 ? response({ detail: 'raw backend stacktrace and credential=secret' }, 500)
        : response({ items: [row], page: 1, pageSize: 25, totalItems: 1, totalPages: 1 }));
    }
    return Promise.resolve(response(execution));
  });
  vi.stubGlobal('fetch', fetchMock);
  renderApp('/executions/execution-1');
  await screen.findByRole('heading', { name: 'Execution execution-1' });
  await userEvent.click(screen.getByRole('tab', { name: 'Repositories' }));
  expect(await screen.findByText('Repository history could not be loaded.')).toBeInTheDocument();
  expect(screen.queryByText(/raw backend stacktrace/i)).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Retry repository history' }));
  expect(await screen.findByText('team/one')).toBeInTheDocument();
  expect(screen.getByRole('tab', { name: 'Repositories' })).toHaveAttribute('aria-selected', 'true');
});

it.each([375, 768, 1440])('keeps repository paths and the scrollable table usable at %ipx', async (viewportWidth) => {
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: viewportWidth });
  const longPath = `group/${'nested/'.repeat(18)}repository-with-a-long-name`;
  const row = { id: 'r1', miningExecutionId: execution.id, gitlabProjectId: 1, repositoryName: 'repository-with-a-long-name', repositoryFullPath: longPath, status: 'completed', startedAt: execution.startedAt, completedAt: execution.completedAt, processedBranch: 'release/stable', fileCount: 4, observedExtensions: ['.py'], extensionsTruncated: false, findingCount: 0, error: null };
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => Promise.resolve(url.includes('/repositories')
    ? response({ items: [row], page: 1, pageSize: 25, totalItems: 1, totalPages: 1 }) : response(execution))));
  renderApp('/executions/execution-1', viewportWidth);
  await screen.findByRole('heading', { name: 'Execution execution-1' });
  await userEvent.click(screen.getByRole('tab', { name: 'Repositories' }));

  const table = await screen.findByRole('table', { name: 'Repository processing results' });
  expect(window.innerWidth).toBe(viewportWidth);
  expect(screen.getByText(longPath)).toBeInTheDocument();
  expect(table.parentElement).toHaveClass('MuiTableContainer-root');
  expect(getComputedStyle(table.parentElement!).overflowX).toBe('auto');
  expect(screen.getByRole('columnheader', { name: 'Repository' })).toBeInTheDocument();
  expect(screen.getByRole('columnheader', { name: 'Status' })).toBeInTheDocument();
});
