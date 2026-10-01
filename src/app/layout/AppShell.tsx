import { Box, IconButton, Toolbar, Typography } from '@mui/material';
import { MenuRounded } from '@mui/icons-material';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { MobileNavigation } from './MobileNavigation';
import { useResponsiveNavigation } from '../../shared/hooks/useResponsiveNavigation';
import { tokens } from '../theme/tokens';
import { MonitoringConfigurationWizardProvider } from '../../features/monitoring-configurations/context/MonitoringConfigurationWizardContext';

export function AppShell() { const nav = useResponsiveNavigation(); return <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
  {nav.desktop ? <Box sx={{ width: tokens.sidebar.width, flexShrink: 0 }}><Box sx={{ position: 'fixed', inset: '0 auto 0 0', width: tokens.sidebar.width }}><Sidebar /></Box></Box> : <><Toolbar component="header" sx={{ position: 'fixed', zIndex: 1100, inset: '0 0 auto 0', bgcolor: '#fff', borderBottom: 1, borderColor: 'divider' }}><IconButton aria-label="Open navigation" onClick={nav.openMenu}><MenuRounded /></IconButton><Typography sx={{ fontWeight: 800 }}>RepoMiner</Typography></Toolbar><MobileNavigation open={nav.open} onClose={nav.closeMenu} /></>}
  <Box component="main" sx={{ flex: 1, minWidth: 0, pt: nav.desktop ? 0 : 8, '--repominer-sidebar-width': `${tokens.sidebar.width}px` }}><MonitoringConfigurationWizardProvider><Outlet /></MonitoringConfigurationWizardProvider></Box>
  </Box>; }
