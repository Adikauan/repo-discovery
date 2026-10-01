import type { ReactNode } from 'react';
import { Box, Typography } from '@mui/material';

export function StateFrame({ icon, title, message, action, role, live }: { icon: ReactNode; title?: string; message: string; action?: ReactNode; role?: 'status' | 'alert'; live?: 'polite' | 'assertive' }) {
  return <Box role={role} aria-live={live} sx={{ minHeight: 190, display: 'grid', placeItems: 'center', textAlign: 'center', p: 3 }}><Box sx={{ maxWidth: 480 }}>{icon}{title && <Typography variant="h3" sx={{ mt: 1 }}>{title}</Typography>}<Typography color="text.secondary" sx={{ mt: 1, mb: action ? 2 : 0 }}>{message}</Typography>{action}</Box></Box>;
}
