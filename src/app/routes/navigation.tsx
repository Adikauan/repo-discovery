import { HomeRounded, PlayCircleOutlineRounded, SettingsRounded, TuneRounded } from '@mui/icons-material';
import type { NavigationItem } from '../../shared/types/presentation';

export const navigationItems: NavigationItem[] = [
  { id: 'home', label: 'Home', path: '/', icon: <HomeRounded />, matchPaths: ['/'] },
  { id: 'monitoring-configurations', label: 'Monitoring Configurations', path: '/monitoring-configurations', icon: <TuneRounded />, matchPaths: ['/monitoring-configurations'] },
  { id: 'executions', label: 'Executions', path: '/executions', icon: <PlayCircleOutlineRounded />, matchPaths: ['/executions'] },
  { id: 'settings', label: 'Settings', path: '/settings', icon: <SettingsRounded />, matchPaths: ['/settings'] },
];

export function isNavigationItemActive(pathname: string, item: NavigationItem) {
  if (item.path === '/') return pathname === '/';
  return pathname === item.path || pathname.startsWith(`${item.path}/`);
}
