import { expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderApp } from '../../renderApp';

it('exposes accessible credential controls on narrow layouts', async () => {
  const id = '33333333-3333-3333-3333-333333333333';
  vi.spyOn(globalThis, 'fetch').mockImplementation((input) => Promise.resolve(new Response(JSON.stringify(String(input).endsWith(id) ? { id, name: 'A', description: null, gitlab_url: 'https://gitlab.example', enabled: false, created_at: '2026-09-28T12:00:00Z', updated_at: '2026-09-28T12:00:00Z', version: '1' } : { configuration_id: id, credential_configured: false, state: 'not_configured', latest_result: null, last_validation_at: null, last_successful_validation_at: null }), { status: 200, headers: { 'Content-Type': 'application/json' } })));
  renderApp(`/monitoring-configurations/${id}/gitlab-connection`, 375);
  expect(await screen.findByLabelText('GitLab access token')).toBeVisible();
  expect(screen.getByRole('button', { name: 'Validate without saving' })).toBeVisible();
});

