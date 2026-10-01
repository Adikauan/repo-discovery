import { expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderApp } from '../../renderApp';

it('keeps connection setup separate from configuration lifecycle and discovery', async () => {
  const id = '44444444-4444-4444-4444-444444444444';
  const configuration = { id, name: 'Disabled configuration', description: 'unchanged', gitlab_url: 'https://gitlab.example', enabled: false, created_at: '2026-09-28T12:00:00Z', updated_at: '2026-09-28T12:00:00Z', version: '1' };
  vi.spyOn(globalThis, 'fetch').mockImplementation((input) => Promise.resolve(new Response(JSON.stringify(String(input).endsWith(id) ? configuration : { configuration_id: id, credential_configured: false, state: 'not_configured', latest_result: null, last_validation_at: null, last_successful_validation_at: null }), { status: 200, headers: { 'Content-Type': 'application/json' } })));
  renderApp(`/monitoring-configurations/${id}/gitlab-connection`);
  expect(await screen.findByRole('heading', { name: 'GitLab Connection' })).toBeInTheDocument();
  expect(screen.getByRole('textbox', { name: 'GitLab instance URL' })).toBeInTheDocument();
  expect(screen.getByLabelText('GitLab access token')).toBeInTheDocument();
  expect(screen.getByText(/Discovery permissions are not checked/)).toBeVisible();
  expect(screen.queryByText(/repository results/i)).not.toBeInTheDocument();
});

