import type { ReactNode } from 'react';
import { Box, TextField } from '@mui/material';
import { SearchRounded } from '@mui/icons-material';
import { SectionHeader } from '../layout/SectionHeader';

export function TreePanel({ children, searchQuery = '', onSearchChange, title = 'Groups and repositories' }:
  { children: ReactNode; searchQuery?: string; onSearchChange?: (value: string) => void; title?: string }) {
  return <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 2, p: 2, minHeight: 390 }}>
    <SectionHeader title={title} />
    <TextField fullWidth size="small" slotProps={{ htmlInput: { 'aria-label': 'Search hierarchy' } }} placeholder="Search loaded groups or repositories"
      value={searchQuery} onChange={event => onSearchChange?.(event.target.value)} />
    <Box sx={{ mt: 1.5 }}>{children}</Box>
  </Box>;
}
