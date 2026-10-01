import { fireEvent, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { renderApp } from '../../renderApp';
afterEach(() => vi.unstubAllGlobals());
function json(body: unknown) { return new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } }); }

it('shows the joined schedule summary in the configuration list without schedule fan-out', async () => {
  const item = { id: 'config-1', name: 'Builds', description: 'Daily builds', gitlab_url: 'https://gitlab.example', enabled: true, created_at: '2026-09-01T00:00:00Z', updated_at: '2026-09-02T00:00:00Z', version: '1', allowed_author_emails: [], scheduleSummary: { recurrenceType: 'weekly', enabled: false, executionTime: '09:30', timezone: 'UTC', dayOfWeek: 2, dayOfMonth: null } };
  const fetchMock = vi.fn().mockResolvedValue(json({ items: [item] })); vi.stubGlobal('fetch', fetchMock);
  renderApp('/monitoring-configurations');
  expect(await screen.findByText(/weekly · 09:30/i)).toBeInTheDocument();
  expect(screen.getByText(/UTC · Disabled/)).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(fetchMock.mock.calls[0][0]).toContain('/monitoring-configurations');
});

it('keeps General limited to its fields and defers configuration creation until GitLab Connection', async () => {
  const user = userEvent.setup(); const fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock); renderApp('/monitoring-configurations/new');
  for (const step of ['General', 'GitLab Connection', 'Scope', 'Policy', 'Scheduling']) expect(screen.getAllByText(step).length).toBeGreaterThan(0);
  expect(screen.queryByLabelText('Repository or group')).not.toBeInTheDocument();
  expect(screen.queryByLabelText('Branch')).not.toBeInTheDocument();
  expect(screen.queryByRole('textbox', { name: /allowed commit authors/i })).not.toBeInTheDocument();
  expect(screen.queryByRole('textbox', { name: 'GitLab instance URL' })).not.toBeInTheDocument();
  expect(screen.queryByText('Recurrence')).not.toBeInTheDocument();
  await user.type(screen.getByRole('textbox', { name: 'Name' }), 'New config');
  await user.click(screen.getByRole('button', { name: /next step: gitlab connection/i }));
  expect(await screen.findByRole('textbox', { name: 'GitLab instance URL' })).toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalled();
});

it('provides an ordered non-clickable step indicator and bottom navigation for Policy', async () => {
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    return Promise.resolve(json(url.endsWith('/gitlab-scope')
      ? { groups: [], repositories: [], stale: false }
      : url.endsWith('/author-policies')
        ? { mode: 'scope_aware', configuration_revision: 1, policies: [], legacy_fallback: { active: false, allowed_author_emails: [] } }
        : { id: 'config-1', name: 'Saved', description: null, gitlab_url: 'https://gitlab.example', enabled: true, created_at: '2026-09-30T00:00:00Z', updated_at: '2026-09-30T00:00:00Z', version: '1', allowed_author_emails: [] }));
  });
  vi.stubGlobal('fetch', fetchMock);
  renderApp('/monitoring-configurations/config-1/authors');
  expect(await screen.findByRole('button', { name: /previous step: scope/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /next step: scheduling/i })).toBeInTheDocument();
  expect(screen.getByRole('navigation', { name: 'Configuration wizard navigation' })).toBeInTheDocument();
  expect(screen.getByText('General')).toBeInTheDocument();
  expect(screen.getByText('GitLab Connection')).toBeInTheDocument();
  expect(screen.getAllByText('Scope').length).toBeGreaterThan(0);
  const activeStep = screen.getAllByRole('listitem').find(element => element.getAttribute('aria-current') === 'step');
  expect(activeStep).toHaveTextContent('Policy');
  expect(screen.getAllByText('Scheduling').length).toBeGreaterThan(0);
  expect(screen.queryByRole('tab')).not.toBeInTheDocument();
});
