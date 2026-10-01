import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { renderApp } from '../../renderApp';

const id = '00500000-0000-0000-0000-000000000003';
const savedSchedule = { recurrenceType: 'weekly', enabled: true, executionTime: '07:00', timezone: 'UTC', dayOfWeek: 1, dayOfMonth: null };
const configuration = {
  id, name: 'Dirty schedule config', description: 'Preserve me', gitlab_url: 'https://gitlab.example.test',
  enabled: true, created_at: '2026-09-01T12:00:00Z', updated_at: '2026-09-02T12:00:00Z', version: '4',
};
const connection = {
  configuration_id: id, credential_configured: false, state: 'not_configured', latest_result: null,
  last_validation_at: null, last_successful_validation_at: null,
};
const json = (body: unknown, version = 1) => new Response(JSON.stringify(body), {
  status: 200, headers: { 'Content-Type': 'application/json', ETag: `"${version}"` },
});

function mockScheduleApi() {
  let schedule = { ...savedSchedule };
  let version = 1;
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input);
    if (url.endsWith('/monitoring-configurations')) return json({ items: [], total: 0, page: 1, pageSize: 20 });
    if (url.endsWith('/monitoring-configurations/' + id)) return json(configuration);
    if (url.endsWith('/gitlab-connection')) return json(connection);
    if (url.endsWith('/schedule-timezones')) return json({ timezones: ['UTC'] });
    if (url.endsWith('/schedule') && (!init?.method || init.method === 'GET')) return json({ schedule, nextOccurrence: null }, version);
    if (url.endsWith('/schedule') && init?.method === 'PUT') {
      schedule = JSON.parse(String(init.body));
      version += 1;
      return json({ schedule, nextOccurrence: null }, version);
    }
    throw new Error('Unexpected request ' + url);
  });
  return { current: () => schedule };
}

it('allows clean navigation without a discard prompt', async () => {
  const user = userEvent.setup();
  mockScheduleApi();
  const { router } = renderApp(`/monitoring-configurations/${id}/schedule`);
  await screen.findByRole('heading', { name: 'Scheduling' });
  await screen.findByRole('combobox', { name: 'Recurrence' });
  expect(screen.queryByText('You have unsaved schedule changes.')).not.toBeInTheDocument();

  await user.click(within(screen.getByRole('navigation', { name: 'Primary navigation' }))
    .getByRole('link', { name: 'Monitoring Configurations' }));
  await screen.findByRole('heading', { level: 1, name: 'Monitoring Configurations' });
  expect(router.state.location.pathname).toBe('/monitoring-configurations');
  expect(screen.queryByRole('dialog', { name: 'Discard unsaved schedule changes?' })).not.toBeInTheDocument();
});

it('marks edits as unsaved and keeps navigation blocked until the user chooses', async () => {
  const user = userEvent.setup();
  mockScheduleApi();
  const { router } = renderApp(`/monitoring-configurations/${id}/schedule`);
  await screen.findByRole('heading', { name: 'Scheduling' });
  await screen.findByRole('combobox', { name: 'Recurrence' });
  await user.click(screen.getByRole('switch', { name: 'Automatic scheduling' }));
  expect(screen.getByText('You have unsaved schedule changes.')).toBeVisible();

  await user.click(within(screen.getByRole('navigation', { name: 'Primary navigation' }))
    .getByRole('link', { name: 'Monitoring Configurations' }));
  const dialog = await screen.findByRole('dialog', { name: 'Discard unsaved schedule changes?' });
  expect(router.state.location.pathname).toBe(`/monitoring-configurations/${id}/schedule`);
  await user.click(within(dialog).getByRole('button', { name: 'Stay' }));
  await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Discard unsaved schedule changes?' })).not.toBeInTheDocument());
  await waitFor(() => expect(router.state.location.pathname).toBe(`/monitoring-configurations/${id}/schedule`));

  await user.click(within(screen.getByRole('navigation', { name: 'Primary navigation' }))
    .getByRole('link', { name: 'Monitoring Configurations' }));
  const secondDialog = await screen.findByRole('dialog', { name: 'Discard unsaved schedule changes?' });
  await user.click(within(secondDialog).getByRole('button', { name: 'Leave page' }));
  await screen.findByRole('heading', { level: 1, name: 'Monitoring Configurations' });
  expect(router.state.location.pathname).toBe('/monitoring-configurations');
});

it('discards a draft explicitly and clears the unsaved state', async () => {
  const user = userEvent.setup();
  mockScheduleApi();
  renderApp(`/monitoring-configurations/${id}/schedule`);
  await screen.findByRole('heading', { name: 'Scheduling' });
  await screen.findByRole('combobox', { name: 'Recurrence' });
  const time = document.querySelector('input[type="time"]') as HTMLInputElement;
  expect(time).not.toBeNull();
  await user.clear(time);
  await user.type(time, '08:30');
  expect(screen.getByText('You have unsaved schedule changes.')).toBeVisible();

  await user.click(screen.getByRole('button', { name: 'Discard changes' }));
  expect(time).toHaveValue('07:00');
  expect(screen.queryByText('You have unsaved schedule changes.')).not.toBeInTheDocument();
});

it('clears the dirty state after a successful save', async () => {
  const user = userEvent.setup();
  const api = mockScheduleApi();
  renderApp(`/monitoring-configurations/${id}/schedule`);
  await screen.findByRole('heading', { name: 'Scheduling' });
  await screen.findByRole('combobox', { name: 'Recurrence' });
  await user.click(screen.getByRole('switch', { name: 'Automatic scheduling' }));
  expect(screen.getByText('You have unsaved schedule changes.')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Save schedule' }));

  expect(await screen.findByText('Schedule saved successfully.')).toBeVisible();
  expect(api.current().enabled).toBe(false);
  expect(screen.queryByText('You have unsaved schedule changes.')).not.toBeInTheDocument();
});

it('blocks browser unload while a schedule draft is dirty', async () => {
  const user = userEvent.setup();
  mockScheduleApi();
  renderApp(`/monitoring-configurations/${id}/schedule`);
  await screen.findByRole('heading', { name: 'Scheduling' });
  await screen.findByRole('combobox', { name: 'Recurrence' });
  await user.click(screen.getByRole('switch', { name: 'Automatic scheduling' }));
  const event = new Event('beforeunload', { cancelable: true }) as BeforeUnloadEvent;
  window.dispatchEvent(event);
  expect(event.defaultPrevented).toBe(true);
});

