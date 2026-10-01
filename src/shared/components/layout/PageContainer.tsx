import type { PropsWithChildren } from 'react';
import { Box } from '@mui/material';
import { tokens } from '../../../app/theme/tokens';

export function PageContainer({ children }: PropsWithChildren) {
  return <Box sx={{ width: '100%', maxWidth: tokens.content.maxWidth, mx: 'auto', px: tokens.spacing.pageX, py: tokens.spacing.pageY, minWidth: 0 }}>{children}</Box>;
}
