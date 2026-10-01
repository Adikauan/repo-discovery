import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { renderApp } from '../../renderApp';
import { execution, page, response } from './fixtures';

afterEach(() => vi.unstubAllGlobals());

it.each(['/executions', '/monitoring-configurations/config-1/executions'])(
  'shows scheduled execution in ordinary history and dashboard at %s', async historyPath => {
    const scheduled = { ...execution, triggerType: 'scheduled' as const };
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/repositories')) return Promise.resolve(response({ items: [], page: 1, pageSize: 25, totalItems: 0 }));
      if (url.includes('/executions/execution-1')) return Promise.resolve(response(scheduled));
      return Promise.resolve(response({ ...page, items: [scheduled] }));
    });
    vi.stubGlobal('fetch', fetchMock);
    const { router } = renderApp(historyPath);

    await userEvent.click(await screen.findByRole('link', { name: execution.id }));
    expect(await screen.findByRole('heading', { name: 'Execution execution-1' })).toBeInTheDocument();
    expect(screen.getByText(/Trigger: Scheduled/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('tab', { name: 'Repositories' }));
    expect(await screen.findByText(/valid empty effective scope/i)).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/executions/execution-1');
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/executions/execution-1/repositories'))).toBe(true);
  },
);
