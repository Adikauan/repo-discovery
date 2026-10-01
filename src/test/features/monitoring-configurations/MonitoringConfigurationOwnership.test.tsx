import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { renderApp } from '../../renderApp';

const id = 'ownership-015';
const item = { id, name: 'Ownership configuration', description: 'Scope', gitlab_url: 'https://gitlab.example.com', enabled: false,
  created_at: '2026-09-30T10:00:00Z', updated_at: '2026-09-30T10:00:00Z', version: '1', allowed_author_emails: [] };
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ETag: '"1"' } });
afterEach(() => vi.unstubAllGlobals());

it('keeps each setting in its owning wizard step through the complete edit flow', async () => {
  const user = userEvent.setup();
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith(`/monitoring-configurations/${id}`) && init?.method === 'PUT') return json({ ...item, version: '2' });
    if (url.endsWith(`/monitoring-configurations/${id}`)) return json(item);
    if (url.endsWith(`/monitoring-configurations/${id}/gitlab-connection`)) return json({ configuration_id: id, credential_configured: false, state: 'not_configured', latest_result: null, last_validation_at: null, last_successful_validation_at: null });
    if (url.endsWith(`/monitoring-configurations/${id}/gitlab-scope/root`)) return json({ nodes: [] });
    if (url.endsWith(`/monitoring-configurations/${id}/gitlab-scope`)) return json({ groups: [], repositories: [], stale: false });
    if (url.endsWith(`/monitoring-configurations/${id}/author-policies`)) return json({ mode: 'scope_aware', configuration_revision: 1, policies: [], repositories: [], legacy_fallback: { active: false, allowed_author_emails: [] } });
    if (url.endsWith('/schedule-timezones')) return json({ timezones: ['UTC'] });
    if (url.endsWith(`/monitoring-configurations/${id}/schedule`)) return json({ schedule: null, nextOccurrence: null });
    return json({});
  }));

  renderApp(`/monitoring-configurations/${id}/edit`);
  await screen.findByRole('textbox', { name: 'Name' });
  expect(screen.getByRole('checkbox', { name: 'Enabled' })).toBeInTheDocument();
  expect(screen.queryByRole('textbox', { name: 'GitLab instance URL' })).not.toBeInTheDocument();
  expect(screen.queryByText('Recurrence')).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument();

  await user.click(screen.getByRole('button', { name: /next step: gitlab connection/i }));
  await screen.findByRole('heading', { name: 'GitLab Connection' });
  expect(await screen.findByRole('textbox', { name: 'GitLab instance URL' })).toBeInTheDocument();
  expect(screen.queryByText('Recurrence')).not.toBeInTheDocument();
  expect(screen.queryByRole('checkbox', { name: 'Enabled' })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument();

  await user.click(screen.getByRole('button', { name: /next step: scope/i }));
  await screen.findByRole('heading', { name: 'GitLab Scope' });
  expect(screen.queryByRole('textbox', { name: 'Name' })).not.toBeInTheDocument();
  expect(screen.queryByRole('textbox', { name: 'GitLab instance URL' })).not.toBeInTheDocument();
  expect(screen.queryByText('Recurrence')).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: /next step: policy/i }));

  await screen.findByRole('heading', { name: 'Policy' });
  expect(screen.queryByRole('textbox', { name: 'Name' })).not.toBeInTheDocument();
  expect(screen.queryByRole('textbox', { name: 'GitLab instance URL' })).not.toBeInTheDocument();
  expect(screen.queryByText('Recurrence')).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: /next step: scheduling/i }));

  await screen.findByRole('combobox', { name: 'Recurrence' });
  expect(screen.getByRole('button', { name: 'Save schedule' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /previous step: policy/i })).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /next step/i })).not.toBeInTheDocument();
  expect(screen.queryByRole('textbox', { name: 'GitLab instance URL' })).not.toBeInTheDocument();
  expect(screen.queryByRole('checkbox', { name: 'Enabled' })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument();
});
