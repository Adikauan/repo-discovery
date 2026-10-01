import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { renderApp } from '../../renderApp';
import { execution, page, response } from './fixtures';
afterEach(() => vi.unstubAllGlobals());

it.each(['/executions','/monitoring-configurations/config-1/executions'])('loads and filters history at %s', async path => {
  const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(response(page)));
  vi.stubGlobal('fetch', fetchMock);
  renderApp(path);
  expect(screen.getByRole('status')).toBeInTheDocument();
  expect(await screen.findByRole('link', { name: execution.id })).toHaveAttribute('href', '/executions/execution-1');
  expect(screen.getAllByText('Completed')).toHaveLength(3);
  expect(screen.getByRole('columnheader', { name: 'Findings' })).toBeInTheDocument();
  expect(screen.getByRole('cell', { name: String(execution.findingCount) })).toBeInTheDocument();
  fireEvent.change(screen.getByRole('combobox', { name: 'Status' }), { target: { value: 'failed' } });
  await waitFor(() => expect(fetchMock.mock.calls.at(-1)?.[0]).toContain('status=failed'));
  fireEvent.change(screen.getByRole('combobox', { name: 'Trigger' }), { target: { value: 'scheduled' } });
  await waitFor(() => expect(fetchMock.mock.calls.at(-1)?.[0]).toContain('triggerType=scheduled'));
  if (path.includes('config-1')) expect(fetchMock.mock.calls[0][0]).toContain('/monitoring-configurations/config-1/executions');
  else {
    fireEvent.change(screen.getByRole('textbox', { name: 'Configuration ID' }), { target: { value: 'fca9d0e1-0846-4f6b-80b0-cd16c6f724b7' } });
    await userEvent.click(screen.getByRole('button', { name: 'Apply filter' }));
    await waitFor(() => expect(fetchMock.mock.calls.at(-1)?.[0]).toContain('monitoringConfigurationId=fca9d0e1-0846-4f6b-80b0-cd16c6f724b7'));
  }
});

it('shows empty results and a recoverable safe error', async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce(response({ detail: 'History unavailable.' }, 500)).mockResolvedValueOnce(response({ ...page, items: [], totalItems: 0, totalPages: 0 }));
  vi.stubGlobal('fetch', fetchMock);
  renderApp('/executions');
  expect(await screen.findByText('History unavailable.')).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Retry' }));
  expect(await screen.findByText('No executions found')).toBeInTheDocument();
});

it('loads configuration choices only after the manual execution action is opened', async () => {
  const fetchMock = vi.fn().mockImplementation((input: string, init?: RequestInit) => {
    const url = String(input);
    if (init?.method === 'POST') return Promise.resolve(response(execution));
    if (url.endsWith('/monitoring-configurations')) return Promise.resolve(response({ items: [{ id: 'config-9', name: 'Build config', description: null, gitlab_url: 'https://gitlab.example', enabled: true, created_at: execution.createdAt, updated_at: execution.createdAt, version: '1', allowed_author_emails: [] }] }));
    return Promise.resolve(response(page));
  });
  vi.stubGlobal('fetch', fetchMock);
  renderApp('/executions');
  await screen.findByRole('table', { name: 'Execution history' });
  expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith('/monitoring-configurations'))).toBe(false);
  await userEvent.click(screen.getByRole('button', { name: 'Run manual execution' }));
  const dialog = await screen.findByRole('dialog', { name: 'Run a Monitoring Configuration' });
  const config = await within(dialog).findByRole('combobox', { name: 'Monitoring Configuration' });
  await userEvent.click(config);
  await userEvent.click(await screen.findByRole('option', { name: 'Build config' }));
  await userEvent.click(within(dialog).getByRole('button', { name: 'Run manual execution' }));
  await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(true));
});

it('navigates pages and opens execution detail with visible controls', async () => {
  const fetchMock = vi.fn().mockImplementation((url: string) => Promise.resolve(response(url.includes('/executions/execution-1') ? execution : { ...page, totalPages: 2, totalItems: 26 })));
  vi.stubGlobal('fetch', fetchMock);
  renderApp('/executions');
  await screen.findByRole('link', { name: execution.id });
  await userEvent.click(screen.getByRole('button', { name: 'Go to page 2' }));
  await waitFor(() => expect(fetchMock.mock.calls.at(-1)?.[0]).toContain('page=2'));
  await screen.findByRole('link', { name: execution.id });
  screen.getByRole('link', { name: execution.id }).focus();
  expect(screen.getByRole('link', { name: execution.id })).toHaveFocus();
  await userEvent.keyboard('{Enter}');
  expect(await screen.findByRole('heading', { name: 'Execution execution-1' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Execution history' })).toHaveAttribute('href', '/executions');
});

it('returns to the originating global or configuration execution history', async () => {
  const fetchMock = vi.fn().mockImplementation((url: string) => Promise.resolve(response(url.includes('/executions/execution-1') ? execution : page)));
  vi.stubGlobal('fetch', fetchMock);
  const { router } = renderApp('/monitoring-configurations/config-1/executions');
  await userEvent.click(await screen.findByRole('link', { name: execution.id }));
  expect(await screen.findByRole('heading', { name: 'Execution execution-1' })).toBeInTheDocument();
  await userEvent.click(screen.getByRole('link', { name: 'Execution history' }));
  await screen.findByRole('table', { name: 'Execution history' });
  expect(router.state.location.pathname).toBe('/monitoring-configurations/config-1/executions');
});

it('uses global execution history as a direct-entry fallback', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(execution)));
  renderApp('/executions/execution-1');
  await screen.findByRole('heading', { name: 'Execution execution-1' });
  expect(screen.getByRole('link', { name: 'Execution history' })).toHaveAttribute('href', '/executions');
});

it('displays the backend order for tied creation timestamps', async () => {
  const olderId = { ...execution, id: 'execution-0' };
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ ...page, items: [execution, olderId], totalItems: 2 })));
  renderApp('/executions');
  await screen.findByRole('link', { name: execution.id });
  const links = screen.getAllByRole('link').filter(link => link.getAttribute('href')?.startsWith('/executions/execution-'));
  expect(links.map(link => link.textContent)).toEqual(['execution-1', 'execution-0']);
});
