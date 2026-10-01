import { fireEvent, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import { renderApp } from '../../renderApp';

const id = '00500000-0000-0000-0000-000000000001';
const originalConfig = {
  id, name: 'Mining configuration A', description: 'Preserve this description',
  gitlab_url: 'https://gitlab.example.test', enabled: true,
  created_at: '2026-09-01T12:00:00Z', updated_at: '2026-09-02T12:00:00Z', version: '3',
};
const originalConnection = {
  configuration_id: id, credential_configured: true, state: 'validated', latest_result: 'success',
  last_validation_at: '2026-09-02T11:00:00Z', last_successful_validation_at: '2026-09-02T11:00:00Z',
};
const originalScope = {
  groups: [{ selection_id: 'group-selection', gitlab_id: 10, name: 'Engineering', full_path: 'engineering', availability: 'available' }],
  repositories: [{ selection_id: 'repo-selection', gitlab_id: 20, name: 'Compiler', full_path: 'engineering/compiler', availability: 'available' }],
  stale: false,
};
const json = (body: unknown, etag?: string) => new Response(JSON.stringify(body), {
  status: 200, headers: { 'Content-Type': 'application/json', ...(etag ? { ETag: etag } : {}) },
});

type RecurrenceCase = { label: 'daily' | 'weekly' | 'monthly'; dayOfWeek: number | null; dayOfMonth: number | null };
const cases: RecurrenceCase[] = [
  { label: 'daily', dayOfWeek: null, dayOfMonth: null },
  { label: 'weekly', dayOfWeek: 4, dayOfMonth: null },
  { label: 'monthly', dayOfWeek: null, dayOfMonth: 31 },
];

beforeEach(() => vi.restoreAllMocks());

it.each(cases)('$label journey previews, saves, reloads, and preserves unrelated configuration data', async ({ label, dayOfWeek, dayOfMonth }) => {
  const user = userEvent.setup();
  let persisted: Record<string, unknown> | null = null;
  const configReads: typeof originalConfig[] = [];
  const scopeReads: typeof originalScope[] = [];
  const requests: Array<{ url: string; method: string; body?: Record<string, unknown> }> = [];

  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    const body = typeof init?.body === 'string' ? JSON.parse(init.body) as Record<string, unknown> : undefined;
    requests.push({ url, method, body });
    if (url.endsWith('/monitoring-configurations/' + id)) {
      configReads.push({ ...originalConfig });
      return json(originalConfig);
    }
    if (url.endsWith('/monitoring-configurations/' + id + '/gitlab-connection')) return json(originalConnection);
    if (url.endsWith('/monitoring-configurations/' + id + '/gitlab-scope')) {
      scopeReads.push(originalScope);
      return json(originalScope, '"scope-1"');
    }
    if (url.endsWith('/monitoring-configurations/' + id + '/schedule') && method === 'GET') {
      return json({ schedule: persisted, nextOccurrence: null }, '"schedule-1"');
    }
    if (url.endsWith('/monitoring-configurations/' + id + '/schedule/preview')) {
      return json({ nextOccurrence: { instant: '2026-10-01T13:30:00Z', timezone: 'UTC', localDateTime: '2026-10-01T13:30:00' } });
    }
    if (url.endsWith('/monitoring-configurations/' + id + '/schedule') && method === 'PUT') {
      persisted = body ?? null;
      return json({ schedule: persisted, nextOccurrence: { instant: '2026-10-01T13:30:00Z', timezone: 'UTC', localDateTime: '2026-10-01T13:30:00' } }, '"schedule-2"');
    }
    if (url.endsWith('/schedule-timezones')) return json({ timezones: ['UTC', 'America/Sao_Paulo'] });
    throw new Error('Unexpected request ' + method + ' ' + url);
  });

  const view = renderApp('/monitoring-configurations/' + id + '/schedule');
  expect((await screen.findAllByText('Mining configuration A')).length).toBe(1);
  expect(await screen.findAllByRole('heading', { name: 'Scheduling' })).not.toHaveLength(0);
  await screen.findByRole('combobox', { name: 'Recurrence' });
  await user.click(screen.getByRole('combobox', { name: 'Recurrence' }));
  await user.click(await screen.findByRole('option', { name: label[0].toUpperCase() + label.slice(1) }));

  if (label === 'weekly') {
    await user.click(screen.getByRole('combobox', { name: 'Day of week' }));
    await user.click(await screen.findByRole('option', { name: 'Thursday' }));
  } else if (label === 'monthly') {
    await user.type(screen.getByRole('spinbutton', { name: 'Day of month' }), '31');
  }
  const executionTime = document.querySelector<HTMLInputElement>('input[type="time"]');
  expect(executionTime).not.toBeNull();
  fireEvent.change(executionTime!, { target: { value: '09:30' } });
  const timezone = screen.getByRole('combobox', { name: 'Timezone' });
  await user.clear(timezone);
  await user.type(timezone, 'UTC');
  await user.click(await screen.findByRole('option', { name: 'UTC' }));

  await user.click(screen.getByRole('button', { name: 'Preview next scheduled occurrence' }));
  expect(await screen.findByText(/Next scheduled occurrence \(preview\)/)).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Save schedule' }));
  expect(await screen.findByText('Schedule saved successfully.')).toBeVisible();
  expect(persisted).toMatchObject({ recurrenceType: label, executionTime: '09:30', timezone: 'UTC', dayOfWeek, dayOfMonth, enabled: true });

  // Remount to model returning later and reading both the configuration and saved schedule.
  view.unmount();
  renderApp('/monitoring-configurations/' + id + '/schedule');
  expect(await screen.findAllByRole('heading', { name: 'Scheduling' })).not.toHaveLength(0);
  await screen.findByRole('combobox', { name: 'Recurrence' });
  expect(screen.getByRole('combobox', { name: 'Recurrence' })).toHaveTextContent(label[0].toUpperCase() + label.slice(1));
  expect(document.querySelector<HTMLInputElement>('input[type="time"]')).toHaveValue('09:30');
  expect(screen.getByRole('combobox', { name: 'Timezone' })).toHaveValue('UTC');
  if (label === 'weekly') expect(screen.getByRole('combobox', { name: 'Day of week' })).toHaveTextContent('Thursday');
  if (label === 'monthly') expect(screen.getByRole('spinbutton', { name: 'Day of month' })).toHaveValue(31);
  if (label === 'daily') {
    expect(screen.queryByLabelText('Day of week')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Day of month')).not.toBeInTheDocument();
  }
  expect(configReads.length).toBeGreaterThanOrEqual(2);
  expect(configReads.every(config => JSON.stringify(config) === JSON.stringify(originalConfig))).toBe(true);
  expect(screen.queryByText('Preserve this description')).not.toBeInTheDocument();
  expect(screen.queryByText('https://gitlab.example.test')).not.toBeInTheDocument();
  expect(screen.queryByText('Validated')).not.toBeInTheDocument();

  // Scope is an existing safe metadata contract and remains unchanged after schedule mutation.
  const scopeBefore = await (await fetch('/api/v1/monitoring-configurations/' + id + '/gitlab-scope')).json();
  const scopeAfter = await (await fetch('/api/v1/monitoring-configurations/' + id + '/gitlab-scope')).json();
  expect(scopeBefore.groups).toEqual(originalScope.groups);
  expect(scopeAfter).toEqual(scopeBefore);
  expect(scopeReads).toEqual([originalScope, originalScope]);
  expect(requests.some(request => request.method === 'PUT' && request.url.includes('/gitlab-scope'))).toBe(false);
  expect(requests.some(request => request.method === 'PUT' && request.url.includes('/schedule'))).toBe(true);
  expect(requests.every(request => !JSON.stringify(request.body ?? {}).includes('token'))).toBe(true);
}, 30_000);



