import { fireEvent, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { renderApp } from '../../renderApp';

const rows = [
  { id: 'cfg-a', name: 'Disabled configuration', description: null, gitlab_url: 'https://gitlab.example', enabled: false,
    created_at: '2026-09-30T10:00:00Z', updated_at: '2026-09-30T10:00:00Z', version: '1' },
  { id: 'cfg-b', name: 'Enabled configuration', description: null, gitlab_url: 'https://gitlab.example', enabled: true,
    created_at: '2026-09-30T10:00:00Z', updated_at: '2026-09-30T10:00:00Z', version: '1' },
];
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
afterEach(() => vi.unstubAllGlobals());

it('runs the selected row through the existing manual execution API, including disabled configurations', async () => {
  const user = userEvent.setup();
  const requests: { url: string; init?: RequestInit }[] = [];
  const execution = { id: 'exec-016', monitoringConfigurationId: 'cfg-a', configurationName: rows[0].name,
    triggerType: 'manual', status: 'pending', createdAt: '2026-09-30T10:01:00Z', startedAt: null, completedAt: null,
    durationSeconds: null, findingCount: 0,
    snapshot: { configurationId: 'cfg-a', configurationName: rows[0].name, configurationEnabled: false,
      gitlabUrl: rows[0].gitlab_url, configurationRevision: 1, scope: { groups: [], repositories: [] } },
    counters: { repositoryCount: 0, successfulRepositoryCount: 0, failedRepositoryCount: 0, findingCount: 0 },
    scopeResolutionFailureCount: 0, error: null, completionMeaning: null };
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input); requests.push({ url, init });
    if (url.endsWith('/monitoring-configurations')) return response({ items: rows });
    if (init?.method === 'POST' && url.endsWith('/monitoring-configurations/cfg-a/executions')) return response(execution);
    if (url.endsWith('/executions/exec-016')) return response(execution);
    if (url.endsWith('/executions/exec-016/repositories?page=1&pageSize=25')) return response({ items: [], totalItems: 0, page: 1, pageSize: 25, totalPages: 0 });
    return response({});
  }));
  const { router } = renderApp('/monitoring-configurations');

  await screen.findByText(rows[0].name);
  const runDisabled = screen.getByRole('button', { name: `Run manual execution for ${rows[0].name}` });
  expect(runDisabled).toBeEnabled();
  await user.hover(runDisabled);
  expect(await screen.findByRole('tooltip')).toHaveTextContent(/run manual execution/i);
  expect(screen.getByRole('button', { name: `Run manual execution for ${rows[1].name}` })).toBeInTheDocument();
  await user.click(runDisabled);
  await waitFor(() => expect(router.state.location.pathname).toBe('/executions/exec-016'));
  const request = requests.find(item => item.init?.method === 'POST');
  expect(request?.url).toContain('/monitoring-configurations/cfg-a/executions');
  expect(request?.init?.headers).toHaveProperty('Idempotency-Key');
  expect(requests.some(item => item.init?.method === 'POST' && item.url.includes('cfg-b'))).toBe(false);
});

it('disables the row action while the single request is pending', async () => {
  const user = userEvent.setup();
  let resolveRequest!: (value: Response) => void;
  let executions = 0;
  vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith('/monitoring-configurations')) return Promise.resolve(response({ items: [rows[0]] }));
    if (init?.method === 'POST') {
      executions += 1;
      return new Promise<Response>(resolve => { resolveRequest = resolve; });
    }
    return Promise.resolve(response({}));
  }));
  const { router } = renderApp('/monitoring-configurations');
  const action = await screen.findByRole('button', { name: `Run manual execution for ${rows[0].name}` });
  await user.click(action);
  expect(action).toBeDisabled();
  expect(action).toHaveAttribute('aria-busy', 'true');
  fireEvent.click(action);
  expect(executions).toBe(1);
  resolveRequest(response({ id: 'exec-pending' }));
  await waitFor(() => expect(router.state.location.pathname).toBe('/executions/exec-pending'));
});

it('shows a safe row error and enables retry after a failed manual execution request', async () => {
  const user = userEvent.setup();
  let attempts = 0;
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith('/monitoring-configurations')) return response({ items: [rows[1]] });
    if (init?.method === 'POST' && url.endsWith('/monitoring-configurations/cfg-b/executions')) {
      attempts += 1;
      return attempts === 1 ? response({ detail: 'provider stack secret' }, 503) : response({ detail: 'active conflict' }, 409);
    }
    return response({});
  }));
  renderApp('/monitoring-configurations');
  await screen.findByText(rows[1].name);
  const action = screen.getByRole('button', { name: `Run manual execution for ${rows[1].name}` });
  await user.click(action);
  expect(await screen.findByRole('alert')).toHaveTextContent(/unable to create the execution/i);
  expect(screen.queryByText(/provider stack secret/i)).not.toBeInTheDocument();
  await user.click(action);
  expect(await screen.findByRole('alert')).toHaveTextContent(/already active/i);
  expect(attempts).toBe(2);
});
