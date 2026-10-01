import { Alert, FormHelperText } from '@mui/material';
export function FeedbackMessage({ kind, message }: { kind: 'info' | 'success' | 'warning' | 'error' | 'helper' | 'validation'; message: string }) {
  if (kind === 'helper' || kind === 'validation') return <FormHelperText error={kind === 'validation'}>{message}</FormHelperText>;
  return <Alert severity={kind}>{message}</Alert>;
}
