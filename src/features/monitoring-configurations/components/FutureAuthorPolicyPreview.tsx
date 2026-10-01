import { Alert, Card, CardContent, Grid, TextField, Typography } from '@mui/material';

/** Visual-only preview; these disabled fields are deliberately outside configuration form state. */
export function FutureAuthorPolicyPreview() {
  return <Card variant="outlined" aria-label="Future repository and branch author policy preview" sx={{ bgcolor: 'action.hover' }}>
    <CardContent>
      <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Repository and branch policies</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: .5, mb: 2 }}>
        Per-repository and per-branch author policies are not available yet. The allowed-author list above remains the active configuration.
      </Typography>
      <Grid container spacing={1.5}>
        <Grid size={{ xs: 12, md: 4 }}><TextField disabled fullWidth label="Repository or group" value="Selection-based policies unavailable" /></Grid>
        <Grid size={{ xs: 12, md: 4 }}><TextField disabled fullWidth label="Branch" value="Not available" /></Grid>
        <Grid size={{ xs: 12, md: 4 }}><TextField disabled fullWidth label="Allowed authors" value="Not available" /></Grid>
      </Grid>
      <Alert severity="info" sx={{ mt: 1.5 }}>These preview fields are disabled and are not saved or used by repository mining.</Alert>
    </CardContent>
  </Card>;
}
