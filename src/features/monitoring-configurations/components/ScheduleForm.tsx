import { useState, type FormEvent } from 'react';
import { Button, FormControlLabel, MenuItem, Stack, Switch, TextField } from '@mui/material';
import type { Schedule } from '../types/schedule';
import { TimezoneSelector } from './TimezoneSelector';

const weekdays = [
  ['1', 'Monday'], ['2', 'Tuesday'], ['3', 'Wednesday'], ['4', 'Thursday'],
  ['5', 'Friday'], ['6', 'Saturday'], ['7', 'Sunday'],
];

export function ScheduleForm({ value, timezones, saving, previewing, onChange, onSave, onPreview, showSaveButton = true, formId = 'monitoring-schedule-form' }: {
  value: Schedule; timezones: string[]; saving: boolean; previewing: boolean;
  onChange: (next: Schedule) => void; onSave: (schedule: Schedule) => Promise<void>;
  onPreview: (schedule: Schedule) => Promise<void>;
  showSaveButton?: boolean; formId?: string;
}) {
  const [submitted, setSubmitted] = useState(false);
  const timeError = submitted && !/^([01]\d|2[0-3]):[0-5]\d$/.test(value.executionTime)
    ? 'Enter a valid time in 24-hour HH:mm format.' : '';
  const timezoneError = submitted && !value.timezone ? 'Choose a timezone.' : '';
  const weekdayError = submitted && value.recurrenceType === 'weekly' && !value.dayOfWeek
    ? 'Choose a day of the week.' : '';
  const monthdayError = submitted && value.recurrenceType === 'monthly' &&
    (!value.dayOfMonth || value.dayOfMonth < 1 || value.dayOfMonth > 31)
    ? 'Enter a day from 1 to 31.' : '';
  const valid = !timeError && !timezoneError && !weekdayError && !monthdayError &&
    /^([01]\d|2[0-3]):[0-5]\d$/.test(value.executionTime) && !!value.timezone &&
    (value.recurrenceType !== 'weekly' || (value.dayOfWeek !== null && value.dayOfWeek >= 1 && value.dayOfWeek <= 7)) &&
    (value.recurrenceType !== 'monthly' || (value.dayOfMonth !== null && value.dayOfMonth >= 1 && value.dayOfMonth <= 31));

  function update(patch: Partial<Schedule>) { onChange({ ...value, ...patch }); }
  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitted(true);
    if (valid) await onSave(value);
  }
  async function preview() {
    setSubmitted(true);
    if (valid) await onPreview(value);
  }

  return <form id={formId} onSubmit={submit} noValidate>
    <Stack spacing={2.5}>
      <TextField select label="Recurrence" required value={value.recurrenceType}
        onChange={event => {
          const recurrenceType = event.target.value as Schedule['recurrenceType'];
          update({ recurrenceType, dayOfWeek: recurrenceType === 'weekly' ? value.dayOfWeek : null,
            dayOfMonth: recurrenceType === 'monthly' ? value.dayOfMonth : null });
        }}>
        <MenuItem value="daily">Daily</MenuItem>
        <MenuItem value="weekly">Weekly</MenuItem>
        <MenuItem value="monthly">Monthly</MenuItem>
      </TextField>

      {value.recurrenceType === 'weekly' && <TextField select required label="Day of week"
        value={value.dayOfWeek ?? ''} error={!!weekdayError} helperText={weekdayError || 'One occurrence each week.'}
        onChange={event => update({ dayOfWeek: Number(event.target.value) })}>
        {weekdays.map(([number, label]) => <MenuItem key={number} value={number}>{label}</MenuItem>)}
      </TextField>}

      {value.recurrenceType === 'monthly' && <TextField required type="number" label="Day of month"
        value={value.dayOfMonth ?? ''} error={!!monthdayError} helperText={monthdayError || 'Choose 1–31; shorter months use their final day.'}
        slotProps={{ htmlInput: { min: 1, max: 31, step: 1 } }}
        onChange={event => update({ dayOfMonth: event.target.value ? Number(event.target.value) : null })} />}

      <TextField required type="time" label="Execution time" value={value.executionTime}
        error={!!timeError} helperText={timeError || 'Local wall-clock time, minute precision.'}
        slotProps={{ inputLabel: { shrink: true } }} onChange={event => update({ executionTime: event.target.value })} />

      <TimezoneSelector value={value.timezone} options={timezones} error={!!timezoneError}
        helperText={timezoneError || undefined} onChange={timezone => update({ timezone })} />

      <FormControlLabel control={<Switch checked={value.enabled} onChange={event => update({ enabled: event.target.checked })} />}
        label="Automatic scheduling" />
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
        <Button type="button" onClick={preview} disabled={saving || previewing}>
          {previewing ? 'Calculating preview…' : 'Preview next scheduled occurrence'}
        </Button>
        {showSaveButton && <Button type="submit" variant="contained" disabled={saving || previewing}>
          {saving ? 'Saving…' : 'Save schedule'}
        </Button>}
      </Stack>
    </Stack>
  </form>;
}
