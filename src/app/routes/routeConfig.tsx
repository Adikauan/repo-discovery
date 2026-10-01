import type { RouteObject } from 'react-router-dom';
import { AppShell } from '../layout/AppShell';
import { HomePage } from '../../features/home/pages/HomePage';
import { MonitoringConfigurationsPage } from '../../features/monitoring-configurations/pages/MonitoringConfigurationsPage';
import { NewMonitoringConfigurationPage } from '../../features/monitoring-configurations/pages/NewMonitoringConfigurationPage';
import { MonitoringConfigurationDetailsPage } from '../../features/monitoring-configurations/pages/MonitoringConfigurationDetailsPage';
import { EditMonitoringConfigurationPage } from '../../features/monitoring-configurations/pages/EditMonitoringConfigurationPage';
import { ConfigurationExecutionsPage } from '../../features/monitoring-configurations/pages/ConfigurationExecutionsPage';
import { GitLabScopePage } from '../../features/monitoring-configurations/pages/GitLabScopePage';
import { AuthorPoliciesPage } from '../../features/monitoring-configurations/pages/AuthorPoliciesPage';
import { GitLabConnectionPage } from '../../features/monitoring-configurations/pages/GitLabConnectionPage';
import { SchedulingPage } from '../../features/monitoring-configurations/pages/SchedulingPage';
import { ExecutionsPage } from '../../features/executions/pages/ExecutionsPage';
import { ExecutionDashboardPage } from '../../features/executions/pages/ExecutionDashboardPage';
import { SettingsPage } from '../../features/settings/pages/SettingsPage';

export const canonicalPaths = [
  '/', '/monitoring-configurations', '/monitoring-configurations/new',
  '/monitoring-configurations/new/gitlab-connection', '/monitoring-configurations/:id',
  '/monitoring-configurations/:id/edit', '/monitoring-configurations/:id/gitlab-connection',
  '/monitoring-configurations/:id/scope', '/monitoring-configurations/:id/authors',
  '/monitoring-configurations/:id/schedule', '/monitoring-configurations/:id/executions',
  '/executions', '/executions/:id', '/settings',
] as const;

export const routeConfig: RouteObject[] = [{
  path: '/', element: <AppShell />, children: [
    { index: true, element: <HomePage /> },
    { path: 'monitoring-configurations', element: <MonitoringConfigurationsPage /> },
    { path: 'monitoring-configurations/new', element: <NewMonitoringConfigurationPage /> },
    { path: 'monitoring-configurations/new/gitlab-connection', element: <GitLabConnectionPage /> },
    { path: 'monitoring-configurations/:id/edit', element: <EditMonitoringConfigurationPage /> },
    { path: 'monitoring-configurations/:id/gitlab-connection', element: <GitLabConnectionPage /> },
    { path: 'monitoring-configurations/:id', element: <MonitoringConfigurationDetailsPage /> },
    { path: 'monitoring-configurations/:id/scope', element: <GitLabScopePage /> },
    { path: 'monitoring-configurations/:id/authors', element: <AuthorPoliciesPage /> },
    { path: 'monitoring-configurations/:id/schedule', element: <SchedulingPage /> },
    { path: 'monitoring-configurations/:id/executions', element: <ConfigurationExecutionsPage /> },
    { path: 'executions', element: <ExecutionsPage /> },
    { path: 'executions/:id', element: <ExecutionDashboardPage /> },
    { path: 'settings', element: <SettingsPage /> },
  ],
}];
