import { useEffect, useState } from 'react';
import { useMediaQuery, useTheme } from '@mui/material';
export function useResponsiveNavigation() { const theme = useTheme(); const desktop = useMediaQuery(theme.breakpoints.up('md')); const [open, setOpen] = useState(false); useEffect(() => { if (desktop) setOpen(false); }, [desktop]); return { desktop, open, openMenu: () => setOpen(true), closeMenu: () => setOpen(false) }; }
