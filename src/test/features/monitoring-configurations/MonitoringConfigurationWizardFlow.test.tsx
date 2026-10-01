import { fireEvent, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { renderApp } from '../../renderApp';

afterEach(() => vi.unstubAllGlobals());
const created = { id: 'config-015', name: 'Platform', description: 'Repositories', gitlab_url: 'https://gitlab.example.com', enabled: false,
  created_at: '2026-09-30T10:00:00Z', updated_at: '2026-09-30T10:00:00Z', version: '1', allowed_author_emails: [] };
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ETag: '"1"' } });

describe('Monitoring Configuration wizard consolidation', () => {
  it('keeps General in memory, validates the transient connection, then creates and stores the credential', async () => {
    const user = userEvent.setup();
    const requests: { url: string; init?: RequestInit }[] = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); requests.push({ url, init });
      if (url.endsWith('/gitlab-connections/validate-candidate')) return json({ state: 'validated', result: 'success', message: 'GitLab connection validated.', checked_at: '2026-09-30T10:00:00Z' });
      if (url.endsWith('/monitoring-configurations') && init?.method === 'POST') return json(created, 201);
      if (url.endsWith(`/monitoring-configurations/${created.id}`)) return json(created);
      if (url.endsWith('/gitlab-connection/credential') && init?.method === 'PUT') return json({ configuration_id: created.id, credential_configured: true, state: 'configured_not_validated', latest_result: null, last_validation_at: null, last_successful_validation_at: null });
      if (url.endsWith('/gitlab-connection/validate')) return json({ configuration_id: created.id, credential_source: 'saved_credential', state: 'validated', result: 'success', message: 'GitLab connection validated.', checked_at: '2026-09-30T10:00:00Z', last_successful_validation_at: '2026-09-30T10:00:00Z' });
      if (url.endsWith('/gitlab-scope')) return json({ groups: [], repositories: [], stale: false });
      if (url.endsWith('/gitlab-scope/root')) return json({ nodes: [] });
      return json({});
    });
    vi.stubGlobal('fetch', fetchMock);
    const { router } = renderApp('/monitoring-configurations/new');

    expect(screen.getByRole('heading', { name: 'New Monitoring Configuration' })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Name' })).toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: 'GitLab instance URL' })).not.toBeInTheDocument();
    expect(screen.queryByText('Recurrence')).not.toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Configuration wizard navigation' })).toHaveAttribute('class');
    expect(screen.getByRole('button', { name: /next step: gitlab connection/i })).toBeEnabled();
    expect(screen.queryByRole('button', { name: /previous step/i })).not.toBeInTheDocument();

    await user.type(screen.getByRole('textbox', { name: 'Name' }), created.name);
    await user.type(screen.getByRole('textbox', { name: 'Description' }), created.description);
    const unloadGeneral = new Event('beforeunload', { cancelable: true }) as BeforeUnloadEvent;
    window.dispatchEvent(unloadGeneral);
    expect(unloadGeneral.defaultPrevented).toBe(true);
    await user.click(screen.getByRole('button', { name: /next step: gitlab connection/i }));

    expect(await screen.findByRole('heading', { name: 'GitLab Connection' })).toBeInTheDocument();
    expect(requests.some(request => request.url.endsWith('/monitoring-configurations') && request.init?.method === 'POST')).toBe(false);
    await user.type(screen.getByRole('textbox', { name: 'GitLab instance URL' }), created.gitlab_url);
    await user.type(screen.getByLabelText(/GitLab access token/), 'transient-secret');
    await user.click(screen.getByRole('button', { name: 'Validate connection' }));
    await screen.findByText('GitLab connection validated.');
    expect(requests.some(request => request.url.endsWith('/monitoring-configurations') && request.init?.method === 'POST')).toBe(false);
    const candidate = requests.find(request => request.url.endsWith('/validate-candidate'))!;
    expect(JSON.parse(String(candidate.init?.body))).toEqual({ gitlab_url: created.gitlab_url, token: 'transient-secret' });

    await user.click(screen.getByRole('button', { name: /next step: create and continue/i }));
    expect(await screen.findByRole('heading', { name: 'GitLab Scope' })).toBeInTheDocument();
    const createRequest = requests.find(request => request.url.endsWith('/monitoring-configurations') && request.init?.method === 'POST')!;
    expect(JSON.parse(String(createRequest.init?.body))).toEqual({ name: created.name, description: created.description, gitlab_url: created.gitlab_url, allowed_author_emails: [] });
    expect(createRequest.init?.headers).toMatchObject({ 'Idempotency-Key': expect.any(String) });
    expect(requests.some(request => request.url.includes(`/monitoring-configurations/${created.id}/gitlab-connection/credential`) && request.init?.method === 'PUT')).toBe(true);
    expect(document.body.textContent).not.toContain('transient-secret');
    await waitFor(() => expect(requests.some(request => request.url.endsWith('/gitlab-connection/validate'))).toBe(true));
    await user.click(screen.getByRole('button', { name: /previous step: gitlab connection/i }));
    expect(await screen.findByRole('heading', { name: 'GitLab Connection' })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe(`/monitoring-configurations/${created.id}/gitlab-connection`);
    await user.click(screen.getByRole('button', { name: /previous step: general/i }));
    expect(await screen.findByRole('heading', { name: 'General' })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe(`/monitoring-configurations/${created.id}/edit`);
  });

  it('keeps a configuration uncreated when transient candidate validation fails', async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockResolvedValue(json({ state: 'failed', result: 'invalid_credentials', message: 'GitLab rejected the credential.', checked_at: '2026-09-30T10:00:00Z' }));
    vi.stubGlobal('fetch', fetchMock);
    renderApp('/monitoring-configurations/new');
    await user.type(screen.getByRole('textbox', { name: 'Name' }), 'No create');
    await user.click(screen.getByRole('button', { name: /next step: gitlab connection/i }));
    await user.type(await screen.findByRole('textbox', { name: 'GitLab instance URL' }), 'https://gitlab.example.com');
    await user.type(screen.getByLabelText(/GitLab access token/), 'bad-token');
    await user.click(screen.getByRole('button', { name: 'Validate connection' }));
    expect(await screen.findByText('GitLab rejected the credential.')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0][0])).toContain('validate-candidate');
    expect(fetchMock.mock.calls.some(call => String(call[0]).endsWith('/monitoring-configurations'))).toBe(false);
  });

  it('retries credential persistence with the retained ID and never creates a duplicate', async () => {
    const user = userEvent.setup();
    let credentialAttempts = 0;
    const requests: { url: string; init?: RequestInit }[] = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); requests.push({ url, init });
      if (url.endsWith('/validate-candidate')) return json({ state: 'validated', result: 'success', message: 'GitLab connection validated.', checked_at: '2026-09-30T10:00:00Z' });
      if (url.endsWith('/monitoring-configurations') && init?.method === 'POST') return json(created, 201);
      if (url.endsWith(`/monitoring-configurations/${created.id}/gitlab-connection/credential`) && init?.method === 'PUT') {
        credentialAttempts += 1;
        return credentialAttempts === 1 ? json({ detail: 'Temporary save failure.' }, 503) : json({ configuration_id: created.id, credential_configured: true, state: 'configured_not_validated', latest_result: null, last_validation_at: null, last_successful_validation_at: null });
      }
      if (url.endsWith(`/monitoring-configurations/${created.id}/gitlab-connection/validate`)) return json({ configuration_id: created.id, credential_source: 'saved_credential', state: 'validated', result: 'success', message: 'GitLab connection validated.', checked_at: '2026-09-30T10:00:00Z', last_successful_validation_at: '2026-09-30T10:00:00Z' });
      if (url.endsWith(`/monitoring-configurations/${created.id}/gitlab-scope`)) return json({ groups: [], repositories: [], stale: false });
      if (url.endsWith(`/monitoring-configurations/${created.id}/gitlab-scope/root`)) return json({ nodes: [] });
      return json({});
    });
    vi.stubGlobal('fetch', fetchMock);
    renderApp('/monitoring-configurations/new');
    await user.type(screen.getByRole('textbox', { name: 'Name' }), created.name);
    await user.click(screen.getByRole('button', { name: /next step: gitlab connection/i }));
    await user.type(await screen.findByRole('textbox', { name: 'GitLab instance URL' }), created.gitlab_url);
    await user.type(screen.getByLabelText(/GitLab access token/), 'retry-secret');
    await user.click(screen.getByRole('button', { name: /create and continue/i }));
    expect(await screen.findByText(/temporary save failure/i)).toBeInTheDocument();
    expect(requests.filter(request => request.url.endsWith('/monitoring-configurations') && request.init?.method === 'POST')).toHaveLength(1);
    await user.click(screen.getByRole('button', { name: /retry and continue/i }));
    expect(await screen.findByRole('heading', { name: 'GitLab Scope' })).toBeInTheDocument();
    expect(requests.filter(request => request.url.endsWith('/monitoring-configurations') && request.init?.method === 'POST')).toHaveLength(1);
    expect(requests.filter(request => request.url.endsWith('/validate-candidate'))).toHaveLength(1);
    expect(document.body.textContent).not.toContain('retry-secret');
  });

  it('warns before discarding a new GitLab credential and preserves it when the user stays', async () => {
    const user = userEvent.setup();
    vi.stubGlobal('fetch', vi.fn());
    renderApp('/monitoring-configurations/new');
    await user.type(screen.getByRole('textbox', { name: 'Name' }), 'Draft config');
    await user.click(screen.getByRole('button', { name: /next step: gitlab connection/i }));
    await user.type(await screen.findByRole('textbox', { name: 'GitLab instance URL' }), 'https://gitlab.example.com');
    const token = screen.getByLabelText(/GitLab access token/);
    await user.type(token, 'unsaved-token');
    await user.click(screen.getByRole('button', { name: /previous step: general/i }));
    const dialog = await screen.findByRole('dialog', { name: 'Leave GitLab Connection?' });
    await user.click(screen.getByRole('button', { name: 'Stay' }));
    await waitFor(() => expect(dialog).not.toBeInTheDocument());
    expect(screen.getByRole('heading', { name: 'GitLab Connection' })).toBeInTheDocument();
    expect(token).toHaveValue('unsaved-token');
    await user.click(screen.getByRole('button', { name: /previous step: general/i }));
    await screen.findByRole('dialog', { name: 'Leave GitLab Connection?' });
    await user.click(screen.getByRole('button', { name: 'Leave step' }));
    await waitFor(() => expect(dialog).not.toBeInTheDocument());
    expect(await screen.findByRole('heading', { name: 'New Monitoring Configuration' })).toBeInTheDocument();
  });

  it('keeps the existing ID through forward and backward edit wizard navigation', async () => {
    const user = userEvent.setup();
    const id = 'edit-config-015';
    const item = { ...created, id, version: '4' };
    const requests: { url: string; init?: RequestInit }[] = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); requests.push({ url, init });
      if (init?.method === 'PUT' && url.endsWith(`/monitoring-configurations/${id}`)) return json({ ...item, version: '5' });
      if (url.endsWith(`/monitoring-configurations/${id}`)) return json(item);
      if (url.endsWith(`/monitoring-configurations/${id}/gitlab-connection`)) return json({ configuration_id: id, credential_configured: false, state: 'not_configured', latest_result: null, last_validation_at: null, last_successful_validation_at: null });
      if (url.endsWith(`/monitoring-configurations/${id}/gitlab-scope`)) return json({ groups: [], repositories: [], stale: false });
      if (url.endsWith(`/monitoring-configurations/${id}/gitlab-scope/root`)) return json({ nodes: [] });
      if (url.endsWith(`/monitoring-configurations/${id}/author-policies`)) return json({ mode: 'scope_aware', configuration_revision: 1, policies: [], legacy_fallback: { active: false, allowed_author_emails: [] } });
      if (url.endsWith('/schedule-timezones')) return json({ timezones: ['UTC'] });
      if (url.endsWith(`/monitoring-configurations/${id}/schedule`)) return json({ schedule: null, nextOccurrence: null });
      return json({});
    });
    vi.stubGlobal('fetch', fetchMock);
    const { router } = renderApp(`/monitoring-configurations/${id}/edit`);
    await screen.findByRole('textbox', { name: 'Name' });
    await user.click(screen.getByRole('button', { name: /next step: gitlab connection/i }));
    expect(await screen.findByRole('heading', { name: 'GitLab Connection' })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole('textbox', { name: 'GitLab instance URL' })).toHaveValue(item.gitlab_url));
    await user.click(screen.getByRole('button', { name: /next step: scope/i }));
    expect(await screen.findByRole('heading', { name: 'GitLab Scope' })).toBeInTheDocument();
    expect(requests.some(request => request.url.includes(`/monitoring-configurations/${id}/gitlab-scope`))).toBe(true);
    await user.click(screen.getByRole('button', { name: /next step: policy/i }));
    expect(await screen.findByRole('heading', { name: 'Policy' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /next step: scheduling/i }));
    expect(await screen.findByRole('combobox', { name: 'Recurrence' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /previous step: policy/i }));
    expect(await screen.findByRole('heading', { name: 'Policy' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /previous step: scope/i }));
    expect(await screen.findByRole('heading', { name: 'GitLab Scope' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /previous step: gitlab connection/i }));
    expect(await screen.findByRole('heading', { name: 'GitLab Connection' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /previous step: general/i }));
    expect(await screen.findByRole('textbox', { name: 'Name' })).toBeInTheDocument();
    expect(router.state.location.pathname).toContain(id);
    expect(requests.every(request => !request.url.includes('undefined'))).toBe(true);
  });

  it('uses the existing safe error state for a deep link to a missing configuration', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ detail: 'Configuration not found.' }, 404)));
    renderApp('/monitoring-configurations/missing-015/edit');
    expect(await screen.findByText(/configuration not found/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
  });
});
