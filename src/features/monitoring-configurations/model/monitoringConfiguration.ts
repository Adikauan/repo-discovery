export interface MonitoringConfiguration {
  id: string;
  name: string;
  description: string | null;
  gitlab_url: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  version: string;
  allowed_author_emails: string[];
  scheduleSummary?: {
    recurrenceType: 'daily' | 'weekly' | 'monthly'; enabled: boolean; executionTime: string; timezone: string;
    dayOfWeek: number | null; dayOfMonth: number | null;
  } | null;
}
export interface MonitoringConfigurationList { items: MonitoringConfiguration[] }

export type ConfigurationInput = Pick<MonitoringConfiguration, 'name' | 'description' | 'gitlab_url' | 'enabled'> & Partial<Pick<MonitoringConfiguration, 'allowed_author_emails'>>;
export type CreateConfigurationInput = Pick<MonitoringConfiguration, 'name' | 'description' | 'gitlab_url' | 'allowed_author_emails'>;
