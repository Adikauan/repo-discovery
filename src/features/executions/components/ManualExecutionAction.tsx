import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Alert, Button, IconButton, Stack, Tooltip, Typography } from '@mui/material';
import { PlayArrowRounded } from '@mui/icons-material';
import { executionsApi } from '../api/executionsApi';
import { ApiError } from '../../../shared/utils/apiClient';

export function ManualExecutionAction({ configurationId, configurationName, compact = false }: {
  configurationId: string; configurationName?: string; compact?: boolean;
}) {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const key = useRef<string | null>(null);
  const inFlight = useRef(false);
  const live = useRef(true);
  useEffect(() => { live.current = true; return () => { live.current = false; }; }, []);
  async function execute() {
    if (inFlight.current) return;
    inFlight.current = true; setBusy(true); setError('');
    key.current ??= crypto.randomUUID();
    try {
      const result = await executionsApi.create(configurationId, key.current);
      key.current = null;
      if (live.current) navigate(`/executions/${result.data.id}`, { state: { notice: 'Execution created.' } });
    } catch (e) {
      if (live.current) setError(e instanceof ApiError && e.status === 409 ? 'An execution is already active or another execution request is in progress. Review the history before trying again.' : 'Unable to create the execution. You can retry this request.');
    } finally { inFlight.current = false; if (live.current) setBusy(false); }
  }
  return <Stack spacing={1} sx={compact ? undefined : { mb: 3 }}>
    {!compact && <Typography color="text.secondary">Run the current configuration through repository mining and record its results.</Typography>}
    {compact ? <Tooltip title={busy ? 'Creating execution…' : 'Run manual execution'}>
      <span><IconButton color="primary" onClick={execute} disabled={busy} aria-busy={busy}
        aria-label={`Run manual execution${configurationName ? ` for ${configurationName}` : ''}`}>
        <PlayArrowRounded /></IconButton></span>
    </Tooltip> : <Button variant="contained" onClick={execute} disabled={busy} aria-busy={busy} sx={{ alignSelf: 'flex-start' }}>{busy ? 'Creating execution…' : 'Run manual execution'}</Button>}
    {busy && <Typography role="status">Creating execution…</Typography>}
    {error && <Alert severity="error">{error}</Alert>}
  </Stack>;
}
