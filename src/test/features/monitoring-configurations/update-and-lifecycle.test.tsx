import { screen, waitForElementToBeRemoved } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { renderApp } from '../../renderApp';

const item = { id: 'cfg-1', name: 'Existing', description: 'Details', gitlab_url: 'https://gitlab.example.com', enabled: false,
  created_at: '2026-09-28T12:00:00Z', updated_at: '2026-09-28T12:00:00Z', version: '1' };
function response(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ETag: '"1"' } }); }
afterEach(() => vi.unstubAllGlobals());

it('keeps configuration overview read-only without wizard or delete shortcuts', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(item)));
  renderApp('/monitoring-configurations/cfg-1');
  expect(await screen.findByText(item.description)).toBeInTheDocument();
  expect(screen.getByText(item.gitlab_url)).toBeInTheDocument();
  for (const name of ['Edit General', 'Configure GitLab Scope', 'Configure Scheduling', 'Enable', 'Delete']) {
    expect(screen.queryByRole('button', { name })).not.toBeInTheDocument();
  }
});

it('preserves edit values when an optimistic concurrency conflict is returned', async () => {
  const user = userEvent.setup();
  vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(response(item)).mockResolvedValueOnce(response({ detail: 'conflict' }, 412)));
  renderApp('/monitoring-configurations/cfg-1/edit');
  const name = await screen.findByRole('textbox', { name: 'Name' });
  await user.clear(name); await user.type(name, 'My unsaved edit');
  await user.click(screen.getByRole('button', { name: /next step: gitlab connection/i }));
  expect(await screen.findByText(/changed since you opened it/i)).toBeInTheDocument();
  expect(name).toHaveValue('My unsaved edit');
});

it('moves from General to GitLab Connection after saving enabled state with the current ETag', async () => {
  const user = userEvent.setup();
  const updated = { ...item, enabled: true, version: '2', updated_at: '2026-09-29T12:00:00Z' };
  const fetchMock = vi.fn().mockResolvedValueOnce(response(item)).mockResolvedValueOnce(response(updated));
  vi.stubGlobal('fetch', fetchMock);
  renderApp('/monitoring-configurations/cfg-1/edit');
  await screen.findByRole('textbox', { name: 'Name' });
  await user.click(screen.getByRole('checkbox', { name: 'Enabled' }));
  await user.click(screen.getByRole('button', { name: /next step: gitlab connection/i }));
  expect(await screen.findByRole('heading', { name: 'GitLab Connection' })).toBeInTheDocument();
  expect(fetchMock.mock.calls[1][1]?.headers).toMatchObject({ 'If-Match': '"1"' });
});

it('keeps deletion available from the configuration list only and confirms it', async () => {
  const user = userEvent.setup();
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (init?.method === 'DELETE') return Promise.resolve(new Response(null, { status: 204 }));
    if (url.endsWith('/monitoring-configurations')) return Promise.resolve(response({ items: init?.method === 'DELETE' ? [] : [item] }));
    return Promise.resolve(response(item));
  });
  vi.stubGlobal('fetch', fetchMock);
  renderApp('/monitoring-configurations');
  await screen.findByText(item.name);
  expect(screen.queryByRole('button', { name: `Enable ${item.name}` })).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: `Delete ${item.name}` }));
  expect(await screen.findByRole('dialog')).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: /delete configuration/i }));
  expect(await screen.findByText(/deleted successfully/i)).toBeInTheDocument();
  await waitForElementToBeRemoved(() => screen.queryByRole('dialog'));
});
