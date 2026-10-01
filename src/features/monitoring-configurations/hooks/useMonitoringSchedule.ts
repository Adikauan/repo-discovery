import { useCallback, useEffect, useState } from 'react';
import { ApiError } from '../../../shared/utils/apiClient';
import { scheduleApi } from '../api/scheduleApi';
import type { NextOccurrence, Schedule, SchedulePreviewEnvelope } from '../types/schedule';

const emptySchedule: Schedule = {
  recurrenceType: 'daily', enabled: true, executionTime: '', timezone: 'UTC',
  dayOfWeek: null, dayOfMonth: null,
};

export function useMonitoringSchedule(configurationId: string) {
  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [nextOccurrence, setNextOccurrence] = useState<NextOccurrence | null>(null);
  const [etag, setEtag] = useState('"0"');
  const [timezones, setTimezones] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [preview, setPreview] = useState<SchedulePreviewEnvelope['nextOccurrence']>(null);
  const [previewReady, setPreviewReady] = useState(false);
  const [error, setError] = useState('');
  const [conflict, setConflict] = useState(false);
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [result, zones] = await Promise.all([scheduleApi.get(configurationId), scheduleApi.timezones()]);
      setSchedule(result.data.schedule ?? null);
      setNextOccurrence(result.data.nextOccurrence);
      setEtag(result.etag ?? '"0"');
      setTimezones(zones.data.timezones ?? []);
      setPreview(null);
      setPreviewReady(false);
      setConflict(false);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'Unable to load schedule configuration.');
    } finally {
      setLoading(false);
    }
  }, [configurationId]);

  useEffect(() => { void load(); }, [load]);

  const save = useCallback(async (draft: Schedule) => {
    setSaving(true);
    setError('');
    setNotice('');
    setConflict(false);
    try {
      const result = await scheduleApi.replace(configurationId, draft, etag);
      setSchedule(result.data.schedule);
      setNextOccurrence(result.data.nextOccurrence);
      setEtag(result.etag ?? etag);
      setPreview(null);
      setPreviewReady(false);
      setNotice('Schedule saved successfully.');
      return result.data.schedule;
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 412) {
        setConflict(true);
        setError('This schedule changed in another session. Your draft is unchanged; reload and review before deciding what to do.');
      } else {
        setError(cause instanceof ApiError ? cause.message : 'Unable to save the schedule. Your draft is unchanged.');
      }
      return undefined;
    } finally {
      setSaving(false);
    }
  }, [configurationId, etag]);

  const runPreview = useCallback(async (draft: Schedule) => {
    setPreviewing(true);
    setError('');
    setPreview(null);
    setPreviewReady(false);
    try {
      const result = await scheduleApi.preview(configurationId, draft);
      setPreview(result.data.nextOccurrence);
      setPreviewReady(true);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'Unable to calculate the schedule preview.');
    } finally {
      setPreviewing(false);
    }
  }, [configurationId]);

  const remove = useCallback(async () => {
    setRemoving(true);
    setError('');
    setNotice('');
    setConflict(false);
    try {
      const result = await scheduleApi.remove(configurationId, etag);
      setSchedule(null);
      setNextOccurrence(null);
      setEtag(result.etag ?? etag);
      setPreview(null);
      setPreviewReady(false);
      setNotice('Schedule removed. Monitoring Configuration settings were not changed.');
      return true;
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 412) {
        setConflict(true);
        setError('This schedule changed in another session. The saved schedule was not removed. Reload and review the latest version.');
      } else {
        setError(cause instanceof ApiError ? cause.message : 'Unable to remove the schedule.');
      }
      return false;
    } finally {
      setRemoving(false);
    }
  }, [configurationId, etag]);

  const clearFeedback = useCallback(() => { setError(''); setNotice(''); }, []);
  const clearPreview = useCallback(() => { setPreview(null); setPreviewReady(false); }, []);

  return {
    schedule, nextOccurrence, etag, timezones, loading, saving, removing,
    previewing, preview, previewReady, error, conflict, notice, emptySchedule,
    load, save, runPreview, remove, clearFeedback, clearPreview,
  };
}
