import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CssBaseline, ThemeProvider } from '@mui/material';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { expect, it, vi } from 'vitest';
import { theme } from '../../../app/theme/theme';
import { ScheduleSection } from '../../../features/monitoring-configurations/components/ScheduleSection';

const id = '00500000-0000-0000-0000-000000000003';
const json = (body: unknown, version: number) => new Response(JSON.stringify(body), {
  status: 200, headers: { 'Content-Type': 'application/json', ETag: '"' + version + '"' },
});
const configured = { recurrenceType: 'weekly', enabled: true, executionTime: '07:00', timezone: 'UTC', dayOfWeek: 1, dayOfMonth: null };

it('disables, re-enables, and removes a schedule without changing its configuration or connection', async () => {
  const user = userEvent.setup();
  let schedule: typeof configured | null = { ...configured };
  let version = 1;
  const config = {
    id, name: 'Lifecycle config', description: 'Keep description', gitlab_url: 'https://gitlab.example.test',
    enabled: false, created_at: '2026-09-01T12:00:00Z', updated_at: '2026-09-02T12:00:00Z', version: '4',
  };
  const connection = {
    configuration_id: id, credential_configured: true, state: 'configured_not_validated', latest_result: null,
    last_validation_at: null, last_successful_validation_at: null,
  };
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input);
    if (url.endsWith('/monitoring-configurations') && (!init?.method || init.method === 'GET')) {
      return new Response(JSON.stringify({ items: [config] }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (url.endsWith('/monitoring-configurations/' + id)) return new Response(JSON.stringify(config), { status: 200, headers: { 'Content-Type': 'application/json' } });
    if (url.endsWith('/gitlab-connection')) return new Response(JSON.stringify(connection), { status: 200, headers: { 'Content-Type': 'application/json' } });
    if (url.endsWith('/schedule-timezones')) return new Response(JSON.stringify({ timezones: ['UTC'] }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    if (url.endsWith('/schedule') && (!init?.method || init.method === 'GET')) return json({ schedule, nextOccurrence: null }, version);
    if (url.endsWith('/schedule') && init?.method === 'PUT') {
      schedule = JSON.parse(String(init.body));
      version += 1;
      return json({ schedule, nextOccurrence: null }, version);
    }
    if (url.endsWith('/schedule') && init?.method === 'DELETE') {
      schedule = null;
      version += 1;
      return new Response(null, { status: 204, headers: { ETag: '"' + version + '"' } });
    }
    throw new Error('Unexpected request ' + url);
  });

  const router = createMemoryRouter([{ path: '/schedule', element: <ScheduleSection configurationId={id}
    configurationEnabled={config.enabled} /> }], { initialEntries: ['/schedule'] });
  render(<ThemeProvider theme={theme}><CssBaseline /><RouterProvider router={router} /></ThemeProvider>);
  await screen.findByRole('heading', { name: 'Scheduling' });
  await screen.findByRole('combobox', { name: 'Recurrence' });
  expect(screen.getByText('Automatic scheduling is enabled.')).toBeVisible();
  await user.click(screen.getByRole('switch', { name: 'Automatic scheduling' }));
  await user.click(screen.getByRole('button', { name: 'Save schedule' }));
  expect(await screen.findByText('Schedule saved successfully.')).toBeVisible();
  expect(schedule?.enabled).toBe(false);

  await user.click(screen.getByRole('switch', { name: 'Automatic scheduling' }));
  await user.click(screen.getByRole('button', { name: 'Save schedule' }));
  expect(await screen.findByText('Schedule saved successfully.')).toBeVisible();
  expect(schedule?.enabled).toBe(true);
  await user.click(screen.getByRole('button', { name: 'Remove schedule' }));
  const dialog = await screen.findByRole('dialog', { name: 'Remove this schedule?' });
  await user.click(within(dialog).getByRole('button', { name: 'Remove schedule' }));
  expect(await screen.findByText('Schedule removed. Monitoring Configuration settings were not changed.')).toBeVisible();
  expect(schedule).toBeNull();
  expect(screen.getByText('No schedule configured.')).toBeVisible();

  expect(screen.queryByText('https://gitlab.example.test')).not.toBeInTheDocument();
  expect(screen.queryByText('Configured · not validated')).not.toBeInTheDocument();
});

