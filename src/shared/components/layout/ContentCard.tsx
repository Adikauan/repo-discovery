import type { PropsWithChildren } from 'react';
import { Card, CardContent, type CardProps } from '@mui/material';

export function ContentCard({ children, sx, ...props }: PropsWithChildren<CardProps>) {
  return <Card {...props} sx={{ borderRadius: 3, ...sx }}><CardContent sx={{ p: { xs: 2, md: 3 }, '&:last-child': { pb: { xs: 2, md: 3 } } }}>{children}</CardContent></Card>;
}
