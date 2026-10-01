import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { ScheduleForm } from '../../../features/monitoring-configurations/components/ScheduleForm';
import type { Schedule } from '../../../features/monitoring-configurations/types/schedule';

const initial: Schedule = {
  recurrenceType: 'monthly', enabled: true, executionTime: '08:15', timezone: 'UTC',
  dayOfWeek: null, dayOfMonth: 31,
};

it('switches recurrence fields, exposes validation, and submits only the active recurrence value', async () => {
  const user = userEvent.setup();
  const onSave = vi.fn(async (_schedule: Schedule) => {});
  let latest = initial;
  const preview = vi.fn(async (_schedule: Schedule) => {});
  let view: ReturnType<typeof render>;
  const onChange = (next: Schedule) => {
    latest = next;
    view.rerender(<ScheduleForm value={latest} timezones={['UTC']} saving={false} previewing={false}
      onChange={onChange} onSave={onSave} onPreview={preview} />);
  };
  view = render(<ScheduleForm value={latest} timezones={['UTC']} saving={false} previewing={false}
    onChange={onChange} onSave={onSave} onPreview={preview} />);

  await user.click(screen.getByRole('combobox', { name: 'Recurrence' }));
  await user.click(await screen.findByRole('option', { name: 'Weekly' }));
  expect(latest).toMatchObject({ recurrenceType: 'weekly', dayOfMonth: null, dayOfWeek: null });
  await user.click(screen.getByRole('combobox', { name: 'Day of week' }));
  await user.click(await screen.findByRole('option', { name: 'Friday' }));
  expect(latest).toMatchObject({ dayOfWeek: 5, dayOfMonth: null });

  const time = document.querySelector<HTMLInputElement>('input[type="time"]')!;
  fireEvent.change(time, { target: { value: '' } });
  await user.click(screen.getByRole('button', { name: 'Save schedule' }));
  expect(await screen.findByText('Enter a valid time in 24-hour HH:mm format.')).toBeVisible();
  expect(onSave).not.toHaveBeenCalled();
  expect(screen.getByRole('combobox', { name: 'Timezone' })).toHaveValue('UTC');

  fireEvent.change(time, { target: { value: '09:45' } });
  await user.click(screen.getByRole('button', { name: 'Save schedule' }));
  expect(onSave).toHaveBeenCalledWith(expect.objectContaining({
    recurrenceType: 'weekly', executionTime: '09:45', dayOfWeek: 5, dayOfMonth: null,
  }));
});
