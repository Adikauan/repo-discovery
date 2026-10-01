import { Alert, Typography } from '@mui/material';

export function ExecutionErrorSummary({ error }: { error: { code: string; summary: string } | null }) {
  if (!error) return null;
  return <Alert severity="error" aria-label="Execution error">
    <Typography sx={{ fontWeight: 700 }}>{error.code}</Typography>
    <Typography component="div">{error.summary}</Typography>
  </Alert>;
}
