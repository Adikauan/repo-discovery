import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { renderApp } from '../../renderApp';
import { execution, response, mockOtherRequests } from './fixtures';
afterEach(() => vi.unstubAllGlobals());

it('manually executes a disabled configuration and opens final details', async () => {
  const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => Promise.resolve(init?.method === 'POST' ? response(execution, 201) : mockOtherRequests(url)));
  vi.stubGlobal('fetch', fetchMock);
  renderApp('/monitoring-configurations/config-1');
  await userEvent.click(await screen.findByRole('button', { name: 'Run manual execution' }));
  expect(await screen.findByRole('heading', { name: 'Execution execution-1' })).toBeInTheDocument();
  const post = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST');
  expect(post?.[1].body).toBeUndefined();
  expect(post?.[1].headers['Idempotency-Key']).toBeTruthy();
  expect(screen.getByText(/repository processing completed successfully/i)).toBeInTheDocument();
});

it('announces active conflict and does not retry automatically', async () => {
  let finish!: (response: Response) => void;
  const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => init?.method === 'POST' ? new Promise<Response>(resolve => { finish = resolve; }) : Promise.resolve(mockOtherRequests(url)));
  vi.stubGlobal('fetch', fetchMock);
  renderApp('/monitoring-configurations/config-1');
  await userEvent.click(await screen.findByRole('button', { name: 'Run manual execution' }));
  expect(screen.getByRole('button', { name: 'Creating execution…' })).toBeDisabled();
  finish(response({ detail: 'An execution is already active for this configuration.' }, 409));
  expect(await screen.findByText(/an execution is already active/i)).toBeInTheDocument();
  await waitFor(() => expect(screen.getByRole('button', { name: 'Run manual execution' })).toBeEnabled());
  expect(fetchMock.mock.calls.filter(([, init]) => init?.method === 'POST')).toHaveLength(1);
});
