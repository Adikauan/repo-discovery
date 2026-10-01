import { Box, List, ListItem, ListItemButton, ListItemIcon, ListItemText, Typography } from '@mui/material';
import { HubRounded } from '@mui/icons-material';
import { NavLink, useLocation } from 'react-router-dom';
import { navigationItems, isNavigationItemActive } from '../routes/navigation';
import { tokens } from '../theme/tokens';

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { pathname } = useLocation();
  return <Box component="nav" aria-label="Primary navigation" sx={{ width: tokens.sidebar.width, minHeight: '100%', bgcolor: tokens.colors.navy900, color: '#fff', p: 2, display: 'flex', flexDirection: 'column' }}>
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, px: 1.25, py: 2, mb: 2 }}><Box sx={{ display: 'grid', placeItems: 'center', width: 40, height: 40, borderRadius: 2, background: 'linear-gradient(135deg,#724cff,#1678ff)' }}><HubRounded /></Box><Typography variant="h6" sx={{ fontWeight: 800 }}>RepoMiner</Typography></Box>
    <List sx={{ display: 'grid', gap: .75 }}>
      {navigationItems.map((item) => { const active = isNavigationItemActive(pathname, item); return <ListItem key={item.id} disablePadding><ListItemButton component={NavLink} to={item.path} onClick={onNavigate} selected={active} aria-current={active ? 'page' : undefined} sx={{ borderRadius: 2, color: active ? '#fff' : '#d8e3f3', '&.Mui-selected': { bgcolor: '#274d96' }, '&.Mui-selected:hover': { bgcolor: '#315cae' }, '&:hover': { bgcolor: 'rgba(255,255,255,.08)' } }}><ListItemIcon sx={{ color: 'inherit', minWidth: 40 }}>{item.icon}</ListItemIcon><ListItemText primary={item.label} slotProps={{ primary: { sx: { fontWeight: active ? 700 : 500, fontSize: 14 } } }} /></ListItemButton></ListItem>; })}
    </List>
    <Box sx={{ mt: 'auto', borderTop: '1px solid rgba(255,255,255,.12)', pt: 2, px: 1 }}><Typography variant="caption" sx={{ color: '#9fb0c8' }}>Presentation workspace</Typography><Typography variant="body2" sx={{ fontWeight: 650 }}>No account connected</Typography></Box>
  </Box>;
}
