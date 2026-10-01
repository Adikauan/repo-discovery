import { Box, Button, Stack } from '@mui/material';
import { ArrowBackRounded, ArrowForwardRounded, SaveRounded } from '@mui/icons-material';

export function WizardBottomBar({ previous, next, nextLabel = 'Next', previousLabel = 'Previous',
  nextDisabled = false, busy = false, final = false }: {
  previous?: () => void; next: () => void; nextLabel?: string; previousLabel?: string;
  nextDisabled?: boolean; busy?: boolean; final?: boolean;
}) {
  return <Box component="nav" aria-label="Configuration wizard navigation" sx={{ position: 'fixed', zIndex: 1100,
    bottom: 0, left: { xs: 0, md: 'var(--repominer-sidebar-width, 264px)' }, right: 0,
    bgcolor: 'background.paper', borderTop: 1, borderColor: 'divider', boxShadow: 3,
    px: { xs: 2, sm: 3, md: 4 }, py: 1.5 }}>
    <Stack direction="row" sx={{ maxWidth: 1440, mx: 'auto', justifyContent: 'space-between', alignItems: 'center', gap: 1 }}>
      <Box>{previous && <Button onClick={previous} startIcon={<ArrowBackRounded />} aria-label={`Previous step: ${previousLabel}`}>
        {previousLabel}</Button>}</Box>
      <Button variant="contained" onClick={next} disabled={nextDisabled || busy}
        endIcon={final ? <SaveRounded /> : <ArrowForwardRounded />} aria-label={final ? nextLabel : `Next step: ${nextLabel}`}>
        {busy ? 'Saving…' : nextLabel}
      </Button>
    </Stack>
  </Box>;
}
