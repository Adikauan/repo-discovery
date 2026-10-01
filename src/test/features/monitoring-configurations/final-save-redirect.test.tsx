import { fireEvent, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { renderApp } from '../../renderApp';

const id = 'cfg-feature-016';
const configuration = { id, name: 'Configuration 016', description: null, gitlab_url: 'https://gitlab.example.test',
  enabled: true, created_at: '2026-09-30T10:00:00Z', updated_at: '2026-09-30T10:00:00Z', version: '1' };
const response = (body: unknown, status = 200, etag?: string) => new Response(JSON.stringify(body), { status,
  headers: { 'Content-Type': 'application/json', ...(etag ? { ETag: etag } : {}) } });
afterEach(() => vi.unstubAllGlobals());

function mockSuccessfulSave() {
  const requests: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input); const method = init?.method ?? 'GET'; requests.push(`${method} ${url}`);
    if (url.endsWith('/monitoring-configurations') && method === 'GET') return response({ items: [configuration] });
    if (url.endsWith(`/monitoring-configurations/${id}`)) return response(configuration);
    if (url.endsWith(`/monitoring-configurations/${id}/schedule`) && method === 'GET') return response({ schedule: null, nextOccurrence: null }, 200, '"schedule-1"');
    if (url.endsWith('/schedule-timezones')) return response({ timezones: ['UTC'] });
    if (url.endsWith(`/monitoring-configurations/${id}/schedule`) && method === 'PUT') {
      return response({ schedule: JSON.parse(String(init?.body)), nextOccurrence: null }, 200, '"schedule-2"');
    }
    if (url.endsWith(`/monitoring-configurations/${id}/gitlab-scope`)) return response({ groups: [], repositories: [], stale: false });
    if (url.endsWith(`/monitoring-configurations/${id}/author-policies`)) return response({ mode: 'scope_aware',
      configuration_revision: 1, policies: [], legacy_fallback: { active: false, allowed_author_emails: [] } });
    throw new Error(`Unexpected request ${method} ${url}`);
  }));
  return requests;
}

async function fillTime() {
  await screen.findByRole('combobox', { name: 'Recurrence' });
  fireEvent.change(document.querySelector<HTMLInputElement>('input[type="time"]')!, { target: { value: '01:00' } });
}

it('returns a newly created configuration flow to the list only after final schedule save succeeds', async () => {
  const user = userEvent.setup(); const requests = mockSuccessfulSave();
  const { router } = renderApp(`/monitoring-configurations/${id}/authors`);
  await screen.findByRole('heading', { name: 'Policy' });
  await user.click(screen.getByRole('button', { name: 'Next step: Scheduling' }));
  await fillTime();
  await user.click(screen.getByRole('button', { name: 'Save schedule' }));
  await waitFor(() => expect(router.state.location.pathname).toBe('/monitoring-configurations'));
  expect(await screen.findByText('Monitoring Configuration saved successfully.')).toBeVisible();
  expect(requests.some(request => request.startsWith('GET ') && request.endsWith('/monitoring-configurations'))).toBe(true);
});

it('returns an existing configuration edit flow to the list after a successful final save', async () => {
  const user = userEvent.setup(); mockSuccessfulSave();
  const { router } = renderApp(`/monitoring-configurations/${id}/schedule`);
  await fillTime();
  await user.click(screen.getByRole('button', { name: 'Save schedule' }));
  await waitFor(() => expect(router.state.location.pathname).toBe('/monitoring-configurations'));
  expect(await screen.findByText('Monitoring Configuration saved successfully.')).toBeVisible();
});

it('stays on Scheduling and retains the draft when the final save fails', async () => {
  const user = userEvent.setup();
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input); const method = init?.method ?? 'GET';
    if (url.endsWith(`/monitoring-configurations/${id}`)) return response(configuration);
    if (url.endsWith(`/monitoring-configurations/${id}/schedule`) && method === 'GET') return response({ schedule: null, nextOccurrence: null }, 200, '"schedule-1"');
    if (url.endsWith('/schedule-timezones')) return response({ timezones: ['UTC'] });
    if (url.endsWith(`/monitoring-configurations/${id}/schedule`) && method === 'PUT') return response({ detail: 'Unable to save the schedule. Your draft is unchanged.' }, 503);
    throw new Error(`Unexpected request ${method} ${url}`);
  }));
  const { router } = renderApp(`/monitoring-configurations/${id}/schedule`);
  await fillTime();
  await user.click(screen.getByRole('button', { name: 'Save schedule' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/unable to save the schedule/i);
  expect(router.state.location.pathname).toBe(`/monitoring-configurations/${id}/schedule`);
  expect(document.querySelector<HTMLInputElement>('input[type="time"]')).toHaveValue('01:00');
});

it('does not leave Scheduling when final schedule validation fails', async () => {
  const user = userEvent.setup(); mockSuccessfulSave();
  const { router } = renderApp(`/monitoring-configurations/${id}/schedule`);
  await screen.findByRole('combobox', { name: 'Recurrence' });
  await user.click(screen.getByRole('button', { name: 'Save schedule' }));
  expect(await screen.findByText('Enter a valid time in 24-hour HH:mm format.')).toBeVisible();
  expect(router.state.location.pathname).toBe(`/monitoring-configurations/${id}/schedule`);
});
