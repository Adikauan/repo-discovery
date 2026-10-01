import { useState, type FormEvent } from 'react';
import { Alert, Button, Checkbox, FormControlLabel, Grid, Stack, TextField } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import type { ConfigurationInput } from '../model/monitoringConfiguration';
import type { ConfigurationFieldErrors } from '../utils/formErrors';

export type FormValues = { name: string; description: string; gitlab_url: string; enabled: boolean };
export function MonitoringConfigurationForm({ initial, submitLabel, onSubmit, onCancel, error, fieldErrors = {}, onFieldChange, onDirtyChange, showEnabled = false, configurationId, showActions = true, formId = 'monitoring-configuration-general-form' }: {
  initial?: Partial<FormValues>; submitLabel: string; onSubmit: (values: ConfigurationInput) => Promise<void>;
  onCancel?: () => void; error?: string; fieldErrors?: ConfigurationFieldErrors; onFieldChange?: (field: keyof FormValues) => void; onDirtyChange?: (dirty: boolean) => void; showEnabled?: boolean; configurationId?: string; showActions?: boolean; formId?: string;
}) {
  const [values, setValues] = useState<FormValues>({ name: initial?.name ?? '', description: initial?.description ?? '', gitlab_url: initial?.gitlab_url ?? '', enabled: initial?.enabled ?? false });
  const [submitted, setSubmitted] = useState(false);
  const [saving, setSaving] = useState(false);
  const nameError = submitted && !values.name.trim() ? 'Enter a configuration name.' : '';
  async function submit(event: FormEvent) {
    event.preventDefault(); setSubmitted(true);
    if (!values.name.trim()) return;
    setSaving(true);
    try { await onSubmit({ name: values.name.trim(), description: values.description.trim() || null, gitlab_url: values.gitlab_url.trim(), enabled: values.enabled }); }
    finally { setSaving(false); }
  }
  return <form id={formId} onSubmit={submit} noValidate>
    <Grid container spacing={3}>
      <Grid size={{ xs: 12 }}><TextField label="Name" required fullWidth value={values.name} onChange={e => { setValues({ ...values, name: e.target.value }); onFieldChange?.('name'); onDirtyChange?.(true); }} error={!!(nameError || fieldErrors.name)} helperText={fieldErrors.name || nameError || 'A clear name helps you identify this configuration.'} /></Grid>
      <Grid size={{ xs: 12 }}><TextField label="Description" fullWidth multiline minRows={3} value={values.description} onChange={e => { setValues({ ...values, description: e.target.value }); onFieldChange?.('description'); onDirtyChange?.(true); }} error={!!fieldErrors.description} helperText={fieldErrors.description || 'Optional'} /></Grid>
      {showEnabled && <Grid size={{ xs: 12 }}><FormControlLabel control={<Checkbox checked={values.enabled} onChange={e => { setValues({ ...values, enabled: e.target.checked }); onDirtyChange?.(true); }} />} label="Enabled" /></Grid>}
    </Grid>
    {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
    {showActions && <Stack direction={{ xs: 'column-reverse', sm: 'row' }} spacing={2} sx={{ mt: 3, pt: 2, borderTop: 1, borderColor: 'divider', justifyContent: 'space-between' }}>
      {onCancel ? <Button onClick={onCancel}>Cancel</Button> : <Button component={RouterLink} to="/monitoring-configurations">Cancel</Button>}
      <Button type="submit" variant="contained" disabled={saving}>{saving ? 'Saving…' : submitLabel}</Button>
    </Stack>}
  </form>;
}
