import { useEffect, useRef, useState } from 'react';
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle,
  Stack, Typography } from '@mui/material';
import { useBlocker } from 'react-router-dom';
import { ContentCard } from '../../../shared/components/layout/ContentCard';
import { ErrorState } from '../../../shared/components/feedback/ErrorState';
import { LoadingState } from '../../../shared/components/feedback/LoadingState';
import { useMonitoringSchedule } from '../hooks/useMonitoringSchedule';
import type { Schedule } from '../types/schedule';
import { NextOccurrencePreview } from './NextOccurrencePreview';
import { ScheduleForm } from './ScheduleForm';

export function ScheduleSection({ configurationId, configurationEnabled, showSaveButton = true, onSaveSuccess }: {
  configurationId: string; configurationEnabled: boolean; showSaveButton?: boolean; onSaveSuccess?: () => void;
}) {
  const state = useMonitoringSchedule(configurationId);
  const [draft, setDraft] = useState<Schedule | null>(null);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const allowSuccessfulNavigation = useRef(false);
  const persisted = state.schedule ?? state.emptySchedule;
  const isDirty = draft !== null && !sameSchedule(draft, persisted);
  const blocker = useBlocker(() => isDirty && !allowSuccessfulNavigation.current);

  useEffect(() => {
    const beforeUnload = (event: BeforeUnloadEvent) => {
      if (!isDirty) return;
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', beforeUnload);
    return () => window.removeEventListener('beforeunload', beforeUnload);
  }, [isDirty]);

  useEffect(() => {
    if (!state.loading && draft === null) setDraft(state.schedule ?? state.emptySchedule);
  }, [state.loading, state.schedule, state.emptySchedule, draft]);

  if (state.loading) return <ContentCard><LoadingState message="Loading schedule configuration…" /></ContentCard>;
  if (state.error && !draft) return <ContentCard><ErrorState message={state.error} action={<Button onClick={() => void state.load()}>Retry</Button>} /></ContentCard>;
  const value = draft ?? state.emptySchedule;
  const matchesPersisted = !!state.schedule && JSON.stringify(state.schedule) === JSON.stringify(value);
  const preview = state.previewReady ? state.preview : matchesPersisted ? state.nextOccurrence : null;
  const latestStatus = !state.schedule ? 'No schedule configured.' : state.schedule.enabled
    ? 'Automatic scheduling is enabled.' : 'Automatic scheduling is disabled; recurrence settings are retained.';

  async function save(candidate: Schedule) {
    const saved = await state.save(candidate);
    if (saved) {
      allowSuccessfulNavigation.current = true;
      setDraft(saved);
      onSaveSuccess?.();
    }
  }
  async function previewCandidate(candidate: Schedule) {
    await state.runPreview(candidate);
  }
  async function remove() {
    const removed = await state.remove();
    setConfirmRemove(false);
    if (removed) setDraft(state.emptySchedule);
  }
  function discardDraft() {
    setDraft(state.schedule ?? state.emptySchedule);
    state.clearFeedback();
    state.clearPreview();
  }

  return <ContentCard component="section" aria-labelledby="schedule-section-heading">
    <Stack spacing={2.5}>
      <div>
        <Typography id="schedule-section-heading" component="h2" variant="h6" sx={{ fontSize: '1.25rem' }}>Scheduling</Typography>
        <Typography color="text.secondary" sx={{ mt: .5 }}>
          Schedule activation is independent from Monitoring Configuration status ({configurationEnabled ? 'enabled' : 'disabled'}).
        </Typography>
      </div>
      <Typography role="status" aria-live="polite">{latestStatus}</Typography>
      {state.error && <Alert severity={state.conflict ? 'warning' : 'error'} role="alert" aria-live="assertive">{state.error}</Alert>}
      {state.notice && <Alert severity="success" role="status" aria-live="polite">{state.notice}</Alert>}
      {state.conflict && <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
        <Typography variant="body2">Your rejected draft remains in the form and was not retried.</Typography>
        <Button onClick={() => void state.load()}>Reload saved schedule</Button>
      </Stack>}
      {isDirty && <Alert severity="info" role="status">You have unsaved schedule changes.</Alert>}
      <ScheduleForm formId="monitoring-schedule-form" showSaveButton={showSaveButton} value={value} timezones={state.timezones} saving={state.saving || state.removing}
        previewing={state.previewing} onChange={next => { state.clearFeedback(); state.clearPreview(); setDraft(next); }}
        onSave={save} onPreview={previewCandidate} />
      <Button disabled={!isDirty || state.saving || state.removing} onClick={discardDraft}>Discard changes</Button>
      <NextOccurrencePreview occurrence={state.previewing ? null : preview}
        loading={state.previewing} hasSchedule={!!state.schedule} enabled={value.enabled} />
      {state.schedule && <Button color="error" variant="outlined" disabled={state.saving || state.removing}
        onClick={() => setConfirmRemove(true)}>{state.removing ? 'Removing…' : 'Remove schedule'}</Button>}
    </Stack>
    <Dialog open={confirmRemove} onClose={() => setConfirmRemove(false)} aria-labelledby="remove-schedule-title"
      aria-describedby="remove-schedule-description">
      <DialogTitle id="remove-schedule-title">Remove this schedule?</DialogTitle>
      <DialogContent><DialogContentText id="remove-schedule-description">
        This removes only the schedule. The Monitoring Configuration, its enabled status, GitLab connection, and scope remain unchanged.
      </DialogContentText></DialogContent>
      <DialogActions>
        <Button onClick={() => setConfirmRemove(false)}>Cancel</Button>
        <Button color="error" onClick={() => void remove()} disabled={state.removing}>Remove schedule</Button>
      </DialogActions>
    </Dialog>
    <Dialog open={blocker.state === 'blocked'} onClose={() => blocker.reset?.()} aria-labelledby="discard-schedule-title"
      aria-describedby="discard-schedule-description">
      <DialogTitle id="discard-schedule-title">Discard unsaved schedule changes?</DialogTitle>
      <DialogContent><DialogContentText id="discard-schedule-description">
        Your schedule changes have not been saved. Leave this page and discard the draft?
      </DialogContentText></DialogContent>
      <DialogActions>
        <Button onClick={() => blocker.reset?.()}>Stay</Button>
        <Button color="error" onClick={() => blocker.proceed?.()}>Leave page</Button>
      </DialogActions>
    </Dialog>
  </ContentCard>;
}

function sameSchedule(left: Schedule, right: Schedule): boolean {
  return left.recurrenceType === right.recurrenceType && left.enabled === right.enabled &&
    left.executionTime === right.executionTime && left.timezone === right.timezone &&
    left.dayOfWeek === right.dayOfWeek && left.dayOfMonth === right.dayOfMonth;
}
