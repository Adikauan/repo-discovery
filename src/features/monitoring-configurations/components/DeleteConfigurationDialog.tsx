import { useState } from 'react';
import { Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle } from '@mui/material';

export function DeleteConfigurationDialog({ open, name, onClose, onConfirm }: { open: boolean; name: string; onClose: () => void; onConfirm: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  async function confirm() { setBusy(true); try { await onConfirm(); } finally { setBusy(false); } }
  return <Dialog open={open} onClose={busy ? undefined : onClose} aria-labelledby="delete-configuration-title">
    <DialogTitle id="delete-configuration-title">Delete Monitoring Configuration?</DialogTitle>
    <DialogContent><DialogContentText>This will remove “{name}” from active management. Its retained record will not be physically deleted.</DialogContentText></DialogContent>
    <DialogActions><Button onClick={onClose} disabled={busy}>Cancel</Button><Button onClick={confirm} color="error" variant="contained" disabled={busy}>{busy ? 'Deleting…' : 'Delete configuration'}</Button></DialogActions>
  </Dialog>;
}
