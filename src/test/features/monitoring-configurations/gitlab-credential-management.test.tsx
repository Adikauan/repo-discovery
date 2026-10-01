import { afterEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderApp } from '../../renderApp';

const configuration = { id: '11111111-1111-1111-1111-111111111111', name: 'GitLab', description: null, gitlab_url: 'https://gitlab.example', enabled: false, created_at: '2026-09-28T12:00:00Z', updated_at: '2026-09-28T12:00:00Z', version: '1' };
const status = { configuration_id: configuration.id, credential_configured: false, state: 'not_configured', latest_result: null, last_validation_at: null, last_successful_validation_at: null };
const response = (body: unknown, code = 200) => Promise.resolve(new Response(code === 204 ? null : JSON.stringify(body), { status: code, headers: { 'Content-Type': 'application/json' } }));

afterEach(() => vi.restoreAllMocks());

describe('GitLab credential management', () => {
  it('masks, submits, and clears a token without storing it', async () => {
    const secret = 'sentinel-token';
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      const url = String(input);
      if (url.endsWith(`/monitoring-configurations/${configuration.id}`)) return response(configuration);
      if (url.endsWith('/gitlab-connection/credential') && init?.method === 'PUT') return response({ ...status, credential_configured: true, state: 'configured_not_validated' });
      return response(status);
    });
    renderApp(`/monitoring-configurations/${configuration.id}/gitlab-connection`);
    const input = await screen.findByLabelText('GitLab access token');
    expect(input).toHaveAttribute('type', 'password');
    await userEvent.type(input, secret);
    await userEvent.click(screen.getByRole('button', { name: 'Save credential' }));
    await waitFor(() => expect(input).toHaveValue(''));
    expect(JSON.stringify(localStorage)).not.toContain(secret); expect(JSON.stringify(sessionStorage)).not.toContain(secret);
    expect(fetchMock.mock.calls.some(([, init]) => String(init?.body).includes(secret))).toBe(true);
    expect(document.body.textContent).not.toContain(secret);
  });

  it('does not send a credential PUT for a blank field', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input) => String(input).endsWith(`/monitoring-configurations/${configuration.id}`) ? response(configuration) : response(status));
    renderApp(`/monitoring-configurations/${configuration.id}/gitlab-connection`);
    await screen.findByLabelText('GitLab access token');
    expect(screen.getByRole('button', { name: 'Save credential' })).toBeDisabled();
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PUT')).toBe(false);
  });
});

