import { createTheme } from '@mui/material/styles';
import { tokens } from './tokens';

export const theme = createTheme({
  palette: {
    mode: 'light', primary: { main: tokens.colors.blue600 },
    success: { main: tokens.colors.success },
    warning: { main: tokens.colors.warning },
    error: { main: tokens.colors.danger },
    info: { main: tokens.colors.info },
    background: { default: tokens.colors.canvas, paper: tokens.colors.surface },
    text: { primary: tokens.colors.text, secondary: tokens.colors.muted },
    divider: tokens.colors.border,
  },
  typography: {
    fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h1: { fontSize: 'clamp(1.85rem, 3vw, 2.35rem)', fontWeight: 750, letterSpacing: '-0.035em', lineHeight: 1.15 },
    h2: { fontSize: '1.4rem', fontWeight: 700, letterSpacing: '-0.02em' },
    h3: { fontSize: '1.05rem', fontWeight: 700 },
    body2: { lineHeight: 1.55 },
    button: { fontWeight: 650, textTransform: 'none' },
  },
  shape: { borderRadius: tokens.radii.md },
  components: {
    MuiCssBaseline: { styleOverrides: { body: { minWidth: 320 }, '*:focus-visible': { outline: `3px solid ${tokens.colors.blue500}`, outlineOffset: 2 } } },
    MuiButton: { styleOverrides: { root: { minHeight: 42, borderRadius: tokens.radii.sm, boxShadow: 'none' } } },
    MuiCard: { styleOverrides: { root: { border: `1px solid ${tokens.colors.border}`, boxShadow: tokens.shadows.card, backgroundImage: 'none' } } },
    MuiOutlinedInput: { styleOverrides: { root: { borderRadius: tokens.radii.sm, backgroundColor: '#fff' } } },
    MuiTableCell: { styleOverrides: { root: { borderColor: tokens.colors.border, paddingTop: 14, paddingBottom: 14 }, head: { fontWeight: 700, color: tokens.colors.text, whiteSpace: 'nowrap', backgroundColor: '#f8faff' } } },
    MuiTableRow: { styleOverrides: { root: { '&:last-child td, &:last-child th': { borderBottom: 0 } } } },
    MuiDialog: { styleOverrides: { paper: { maxHeight: 'calc(100% - 32px)' } } },
    MuiTab: { styleOverrides: { root: { textTransform: 'none', fontWeight: 650 } } },
  },
});
