import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { renderApp } from '../../renderApp';
import { execution, historicalExecutionDetail, liveMonitoringConfiguration, response } from './fixtures';

afterEach(() => vi.unstubAllGlobals());

it.each(['pending', 'running', 'completed', 'partially_completed', 'failed'] as const)('renders %s from the execution detail contract', async status => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ ...execution, status,
    startedAt: status === 'pending' ? null : execution.startedAt,
    completedAt: ['completed', 'partially_completed', 'failed'].includes(status) ? execution.completedAt : null,
    durationSeconds: status === 'pending' || status === 'running' ? null : execution.durationSeconds,
    completionMeaning: status === 'completed' ? execution.completionMeaning : null,
    error: status === 'failed' || status === 'partially_completed' ? { code: 'execution_interrupted', summary: 'A safe execution summary.' } : null })));
  renderApp('/executions/execution-1');
  expect(await screen.findByRole('heading', { name: 'Execution execution-1' })).toBeInTheDocument();
  expect(screen.getAllByText(status === 'partially_completed' ? 'Partially completed' : status[0].toUpperCase() + status.slice(1)).length).toBeGreaterThan(0);
  expect(screen.getByText(/Trigger: Manual/)).toBeInTheDocument();
  expect(screen.getByText(/Historical configuration: Historical platform/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole('tab', { name: 'Overview' }));
  expect(screen.getByText('Created')).toBeInTheDocument();
  if (status === 'pending') {
    expect(screen.getByText('Not started')).toBeInTheDocument();
    expect(screen.getByText('Not completed')).toBeInTheDocument();
    expect(screen.getByText('Not available')).toBeInTheDocument();
  } else if (status === 'running') {
    expect(screen.getByText('Not completed')).toBeInTheDocument();
    expect(screen.getByText('Not available')).toBeInTheDocument();
  } else {
    expect(screen.getAllByText('Completed').length).toBeGreaterThan(0);
    expect(screen.getByText('1 second')).toBeInTheDocument();
  }
  expect(screen.getByText(execution.snapshot.gitlabUrl)).toBeInTheDocument();
  expect(screen.getByText(/Platform · platform/)).toBeInTheDocument();
  expect(screen.getByText(/Service · platform\/service/)).toBeInTheDocument();
  expect(screen.getAllByText('0')).toHaveLength(4);
  if (status === 'pending') expect(screen.queryByText('1 s')).not.toBeInTheDocument();
  if (status === 'completed') expect(screen.getByText(/Repository processing completed successfully/i)).toBeInTheDocument();
  else expect(screen.queryByText(execution.completionMeaning!)).not.toBeInTheDocument();
  if (status === 'failed' || status === 'partially_completed') expect(screen.getByText('A safe execution summary.')).toBeInTheDocument();
});

it('renders only historical snapshot context and never requests current configuration data', async () => {
  // The live fixture intentionally conflicts with the immutable snapshot returned for this execution.
  const fetchMock = vi.fn().mockImplementation((url: string) => url.endsWith('/executions/execution-1')
    ? Promise.resolve(response(historicalExecutionDetail))
    : Promise.resolve(response(liveMonitoringConfiguration)));
  vi.stubGlobal('fetch', fetchMock);
  renderApp('/executions/execution-1');
  expect(await screen.findByRole('heading', { name: 'Execution execution-1' })).toBeInTheDocument();
  await userEvent.click(screen.getByRole('tab', { name: 'Overview' }));
  expect(screen.getByText(/Historical configuration: Historical platform/)).toBeInTheDocument();
  expect(screen.getByText('https://historical.gitlab.example.com')).toBeInTheDocument();
  expect(screen.getByText(/Platform · platform/)).toBeInTheDocument();
  expect(screen.getByText(/Service · platform\/service/)).toBeInTheDocument();
  expect(screen.queryByText('CURRENT live configuration')).not.toBeInTheDocument();
  expect(screen.queryByText('https://current.gitlab.example.com')).not.toBeInTheDocument();
  expect(screen.queryByText('current-group')).not.toBeInTheDocument();
  expect(screen.queryByText('current-repository')).not.toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(fetchMock.mock.calls[0][0]).toContain('/executions/execution-1');
});

it('shows loading, normalized not found, retry, and safe retrieval errors', async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce(response({ detail: 'Execution not found.' }, 404))
    .mockResolvedValueOnce(response({ detail: 'sensitive backend internals' }, 500))
    .mockResolvedValueOnce(response(execution));
  vi.stubGlobal('fetch', fetchMock);
  renderApp('/executions/missing');
  expect(screen.getByRole('status')).toBeInTheDocument();
  expect(await screen.findByText(/execution was not found/i)).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /execution history/i })).toHaveAttribute('href', '/executions');
});

it('shows retry after normalized API failure', async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce(response({ detail: 'sensitive backend internals' }, 500)).mockResolvedValueOnce(response(execution));
  vi.stubGlobal('fetch', fetchMock);
  renderApp('/executions/execution-1');
  expect(await screen.findByText('Unable to load execution.')).toBeInTheDocument();
  expect(screen.queryByText('sensitive backend internals')).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Retry' }));
  expect(await screen.findByRole('heading', { name: 'Execution execution-1' })).toBeInTheDocument();
});

it('shows honest repository and findings states and safe execution details', async () => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => Promise.resolve(url.includes('/repositories')
    ? response({ items: [], page: 1, pageSize: 25, totalItems: 0 })
    : url.includes('/findings')
      ? response({ items: [], page: 1, pageSize: 25, totalItems: 0 })
      : response({ ...execution, error: { code: 'execution_interrupted', summary: 'Safe summary only.' } }))));
  renderApp('/executions/execution-1');
  await screen.findByRole('heading', { name: 'Execution execution-1' });
  await userEvent.click(screen.getByRole('tab', { name: 'Repositories' }));
  expect(screen.getByText(/valid empty effective scope/i)).toBeInTheDocument();
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('tab', { name: 'Findings' }));
  expect(screen.getByText(/no findings were detected for this execution/i)).toBeInTheDocument();
  expect(screen.queryByText(/sample finding/i)).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('tab', { name: 'Details' }));
  expect(screen.getByText('execution_interrupted')).toBeInTheDocument();
  expect(screen.getByText('Safe summary only.')).toBeInTheDocument();
});

it.each(['Overview', 'Repositories', 'Findings', 'Details'])('refreshes from the %s tab and preserves its selection', async selectedTab => {
  const refreshed = { ...execution, status: 'running' as const, completedAt: null, durationSeconds: null,
    counters: { ...execution.counters, repositoryCount: 3 } };
  const fetchMock = vi.fn().mockImplementation((url: string, _init?: RequestInit) => {
    if (url.includes('/repositories')) return Promise.resolve(response({ items: [], page: 1, pageSize: 25, totalItems: 0 }));
    if (url.includes('/findings')) return Promise.resolve(response({ items: [], page: 1, pageSize: 25, totalItems: 0 }));
    return fetchMock.mock.calls.filter(([called]) => !String(called).includes('/repositories')).length === 1
      ? Promise.resolve(response(execution))
      : new Promise(resolve => setTimeout(() => resolve(response(refreshed)), 100));
  });
  vi.stubGlobal('fetch', fetchMock);
  renderApp('/executions/execution-1');
  await screen.findByRole('heading', { name: 'Execution execution-1' });
  await userEvent.click(screen.getByRole('tab', { name: selectedTab }));
  await userEvent.click(screen.getByRole('button', { name: 'Refresh execution' }));
  expect(await screen.findByRole('status', { name: /refreshing execution/i })).toBeInTheDocument();
  await waitFor(() => expect(screen.getByRole('tab', { name: selectedTab })).toHaveAttribute('aria-selected', 'true'));
  expect((await screen.findAllByText('Running')).length).toBeGreaterThan(0);
  expect(screen.getByText(/Historical configuration: Historical platform/)).toBeInTheDocument();
  if (selectedTab === 'Overview') expect(screen.getByText('3')).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(selectedTab === 'Repositories' ? 4 : selectedTab === 'Findings' ? 4 : 2);
  expect(fetchMock.mock.calls.every(([url]) => String(url).includes('/executions/'))).toBe(true);
});

it('keeps the selected tab and shows normalized feedback when refresh fails', async () => {
  const fetchMock = vi.fn().mockImplementation((url: string) => url.includes('/findings')
    ? Promise.resolve(response({ items: [], page: 1, pageSize: 25, totalItems: 0 }))
    : fetchMock.mock.calls.filter(([called]) => !String(called).includes('/findings')).length === 1
      ? Promise.resolve(response(execution))
      : Promise.resolve(response({ detail: 'internal failure details' }, 500)));
  vi.stubGlobal('fetch', fetchMock);
  renderApp('/executions/execution-1');
  await screen.findByRole('heading', { name: 'Execution execution-1' });
  await userEvent.click(screen.getByRole('tab', { name: 'Findings' }));
  await userEvent.click(screen.getByRole('button', { name: 'Refresh execution' }));
  expect(await screen.findByText('Unable to refresh execution.')).toBeInTheDocument();
  expect(screen.getAllByRole('alert').every(alert => !alert.textContent?.includes('internal failure details'))).toBe(true);
  expect(screen.getByRole('tab', { name: 'Findings' })).toHaveAttribute('aria-selected', 'true');
});
