import axe from 'axe-core';
import { screen, waitForElementToBeRemoved, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { renderApp } from '../../renderApp';

const id = '00500000-0000-0000-0000-000000000002';
const ok = (body: unknown, etag = '"1"') => new Response(JSON.stringify(body), {
  status: 200, headers: { 'Content-Type': 'application/json', ETag: etag },
});
const savedSchedule = { recurrenceType: 'daily', enabled: true, executionTime: '12:00', timezone: 'UTC', dayOfWeek: null, dayOfMonth: null };

it('exposes accessible scheduling controls, feedback, and removal dialog with keyboard operation', async () => {
  const user = userEvent.setup();
  const writes: RequestInit[] = [];
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input);
    if (url.endsWith('/monitoring-configurations/' + id)) return ok({
      id, name: 'Accessible schedule', description: null, gitlab_url: 'https://gitlab.example.test',
      enabled: true, created_at: '2026-09-01T12:00:00Z', updated_at: '2026-09-02T12:00:00Z', version: '1',
    });
    if (url.endsWith('/gitlab-connection')) return ok({
      configuration_id: id, credential_configured: false, state: 'not_configured', latest_result: null,
      last_validation_at: null, last_successful_validation_at: null,
    });
    if (url.endsWith('/schedule-timezones')) return ok({ timezones: ['UTC', 'America/Sao_Paulo'] });
    if (url.endsWith('/schedule') && (!init?.method || init.method === 'GET')) return ok({ schedule: savedSchedule, nextOccurrence: null });
    if (url.endsWith('/schedule/preview')) return ok({ nextOccurrence: { instant: '2026-10-01T12:00:00Z', timezone: 'UTC', localDateTime: '2026-10-01T12:00:00' } });
    if (url.endsWith('/schedule') && init?.method === 'PUT') {
      writes.push(init);
      return new Response(JSON.stringify({ type: 'about:blank', title: 'Precondition failed', status: 412, code: 'stale_update', detail: 'The schedule changed.' }), {
        status: 412, headers: { 'Content-Type': 'application/problem+json' },
      });
    }
    if (url.endsWith('/schedule') && init?.method === 'DELETE') return new Response(null, { status: 204, headers: { ETag: '"2"' } });
    throw new Error('Unexpected request ' + url);
  });

  renderApp('/monitoring-configurations/' + id + '/schedule');
  await screen.findByRole('heading', { name: 'Scheduling' });
  await screen.findByRole('combobox', { name: 'Recurrence' });
  const recurrence = screen.getByRole('combobox', { name: 'Recurrence' });
  const time = document.querySelector<HTMLInputElement>('input[type="time"]')!;
  const timezone = screen.getByRole('combobox', { name: 'Timezone' });
  const enabled = screen.getByRole('switch', { name: 'Automatic scheduling' });
  expect(recurrence).toHaveAttribute('aria-required', 'true');
  expect(time).toHaveAttribute('required');
  expect(document.querySelector('label[for="' + time.id + '"]')).toHaveTextContent('Execution time');
  expect(timezone).toHaveAttribute('required');
  expect(enabled).toBeChecked();

  recurrence.focus();
  await user.keyboard('{Enter}');
  expect(await screen.findByRole('listbox')).toBeVisible();
  await user.keyboard('{Escape}');
  timezone.focus();
  await user.keyboard('{ArrowDown}');
  expect(document.activeElement).toBe(timezone);
  time.focus();
  await user.keyboard('{Control>}a{/Control}09:15');
  expect(time).toHaveValue('09:15');
  enabled.focus();
  await user.keyboard(' ');
  expect(enabled).not.toBeChecked();
  await user.click(enabled);
  expect(enabled).toBeChecked();

  await user.click(screen.getByRole('button', { name: 'Preview next scheduled occurrence' }));
  expect(await screen.findByText(/Next scheduled occurrence/)).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Save schedule' }));
  const conflict = await screen.findByRole('alert');
  expect(conflict).toHaveTextContent('Your draft is unchanged');
  expect(document.querySelector<HTMLInputElement>('input[type="time"]')).toHaveValue('09:15');
  expect(writes).toHaveLength(1);
  expect(screen.getByText('Your rejected draft remains in the form and was not retried.')).toBeVisible();

  const results = await axe.run(document.body, {
    runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'] },
    rules: { 'color-contrast': { enabled: false } },
  });
  expect(results.violations.filter(item => item.impact === 'critical')).toEqual([]);

  await user.click(screen.getByRole('button', { name: 'Remove schedule' }));
  const dialog = await screen.findByRole('dialog', { name: 'Remove this schedule?' });
  expect(dialog).toContainElement(document.activeElement as HTMLElement);
  await user.tab();
  expect(within(dialog).getByRole('button', { name: 'Cancel' })).toHaveFocus();
  const dialogClosed = waitForElementToBeRemoved(() => screen.queryByRole('dialog'));
  await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
  await dialogClosed;
  expect(screen.getByRole('button', { name: 'Remove schedule' })).toBeVisible();
}, 30_000);

