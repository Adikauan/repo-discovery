import { afterEach, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderApp } from '../../renderApp';

const id = '22222222-2222-2222-2222-222222222222';
const configuration = { id, name: 'Connected', description: null, gitlab_url: 'https://gitlab.example', enabled: false, created_at: '2026-09-28T12:00:00Z', updated_at: '2026-09-28T12:00:00Z', version: '1' };
const configured = { configuration_id: id, credential_configured: true, state: 'configured_not_validated', latest_result: null, last_validation_at: null, last_successful_validation_at: null };
const response = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } }));
afterEach(() => vi.restoreAllMocks());

it('validates the saved credential and shows safe success metadata', async () => {
  let validated = false;
  vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
    const url = String(input);
    if (url.endsWith(`/monitoring-configurations/${id}`)) return response(configuration);
    if (url.endsWith('/validate') && init?.method === 'POST') { validated = true; return response({ configuration_id: id, credential_source: 'saved_credential', state: 'validated', result: 'success', message: 'GitLab connection validated.', checked_at: '2026-09-28T12:00:00Z', last_successful_validation_at: '2026-09-28T12:00:00Z' }); }
    return response(validated ? { ...configured, state: 'validated', latest_result: 'success', last_validation_at: '2026-09-28T12:00:00Z', last_successful_validation_at: '2026-09-28T12:00:00Z' } : configured);
  });
  renderApp(`/monitoring-configurations/${id}/gitlab-connection`);
  await userEvent.click(await screen.findByRole('button', { name: 'Validate saved credential' }));
  await waitFor(() => expect(screen.getByText(/Last successful validation:/)).toBeInTheDocument());
  expect(document.body.textContent).not.toMatch(/revision|fingerprint|ciphertext/i);
});

