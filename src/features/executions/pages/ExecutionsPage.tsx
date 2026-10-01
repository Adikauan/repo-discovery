import { useState } from 'react';
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Stack, TextField } from '@mui/material';
import { PageContainer } from '../../../shared/components/layout/PageContainer';
import { PageHeader } from '../../../shared/components/layout/PageHeader';
import { ExecutionHistory } from '../components/ExecutionHistory';
import { ManualExecutionAction } from '../components/ManualExecutionAction';
import { monitoringConfigurationsApi } from '../../monitoring-configurations/api/monitoringConfigurationsApi';
import type { MonitoringConfiguration } from '../../monitoring-configurations/model/monitoringConfiguration';
import { ApiError } from '../../../shared/utils/apiClient';
export function ExecutionsPage() {
  const [items, setItems] = useState<MonitoringConfiguration[]>([]); const [selected, setSelected] = useState(''); const [error, setError] = useState(''); const [pickerOpen, setPickerOpen] = useState(false); const [loading, setLoading] = useState(false);
  async function openPicker() {
    setPickerOpen(true); setError(''); setLoading(true);
    try { const result = await monitoringConfigurationsApi.list(); setItems(result.data.items ?? []); }
    catch (e) { setError(e instanceof ApiError ? e.message : 'Unable to load configurations.'); }
    finally { setLoading(false); }
  }
  return <PageContainer><PageHeader title="Executions" description="Review execution history and captured configuration context." />
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} sx={{ mb: 2, alignItems: { sm: 'center' } }}>
      <Button variant="contained" onClick={() => void openPicker()}>Run manual execution</Button>
    </Stack>
    <Dialog open={pickerOpen} onClose={() => setPickerOpen(false)} fullWidth maxWidth="sm" aria-labelledby="manual-execution-picker-title">
      <DialogTitle id="manual-execution-picker-title">Run a Monitoring Configuration</DialogTitle>
      <DialogContent>
        {loading ? <p role="status">Loading configurations…</p> : error ? <Alert severity="error" action={<Button onClick={() => void openPicker()}>Retry</Button>}>{error}</Alert> : items.length === 0 ? <p>No configurations are available.</p> : <TextField select fullWidth label="Monitoring Configuration" value={selected} onChange={event => setSelected(event.target.value)} sx={{ mt: 1 }}>
          <MenuItem value="">Select a configuration</MenuItem>{items.map(item => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
        </TextField>}
        {selected && !loading && !error && <ManualExecutionAction configurationId={selected} />}
      </DialogContent>
      <DialogActions><Button onClick={() => { setPickerOpen(false); setSelected(''); }}>Close</Button></DialogActions>
    </Dialog>
    <ExecutionHistory /></PageContainer>;
}
