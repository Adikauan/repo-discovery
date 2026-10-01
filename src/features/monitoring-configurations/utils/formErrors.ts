import { ApiError } from '../../../shared/utils/apiClient';

export type ConfigurationFieldErrors = Partial<Record<'name' | 'description' | 'gitlab_url' | 'enabled' | 'allowed_author_emails', string>>;

export function configurationFieldErrors(error: unknown): ConfigurationFieldErrors {
  if (!(error instanceof ApiError)) return {};
  return Object.fromEntries((error.problem?.errors ?? [])
    .filter(({ field }) => ['name', 'description', 'gitlab_url', 'enabled', 'allowed_author_emails'].includes(field))
    .map(({ field, message }) => [field, message])) as ConfigurationFieldErrors;
}
