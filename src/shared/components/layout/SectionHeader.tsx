import { Box, Typography } from '@mui/material';
import type { ReactNode } from 'react';

export function SectionHeader({ title, action, description }: { title: string; action?: ReactNode; description?: string }) {
  return <Box sx={{ display: 'flex', gap: 2, justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}><Box><Typography variant="h3">{title}</Typography>{description && <Typography color="text.secondary" sx={{ mt: .5 }}>{description}</Typography>}</Box>{action}</Box>;
}
